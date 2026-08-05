import re
import difflib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

import spacy as sa

from knowledge_base import shital_academy_knowledge
from llm_helper import ask_llm

from session_manager import (
    create_session,
    get_lead,
    get_conversation,
)
# ==========================================================
# NLP
# ==========================================================

nlp = sa.load("en_core_web_sm")


# ==========================================================
# CONFIGURATION
# ==========================================================

MIN_SCORE_THRESHOLD = 5
FUZZY_CUTOFF = 0.8
MIN_WORD_LEN_FOR_FUZZY = 4

# Topics that ask about an ATTRIBUTE of a course (fees, timing, location,
# eligibility, etc.) rather than about a specific subject/course itself.
# A message like "fees of spoken english" or "duration of python course"
# mentions both an attribute (fees/duration) and a course name (spoken
# english/python). Because course names are often multi-word phrases, they
# tend to out-score a single generic attribute word like "fees" - which
# means, without this override, "fees of spoken english" would incorrectly
# return the Spoken English course description instead of the fees answer.
# When any of these topics gets a real match, it takes priority over any
# competing subject/course topic.
ATTRIBUTE_INTENT_TOPICS = {
    "fees",
    "installment",
    "duration",
    "batch_timings",
    "office_hours",
    "branches",
    "admission",
    "eligibility",
    "certificate",
    "age_limit",
    "demo_class",
}

# Specific course/subject topics. These are the ones whose own name (e.g.
# "python", "ielts coaching") can rack up a strong multi-word phrase match
# and wrongly out-score a real attribute question mentioned alongside it
# (see ATTRIBUTE_INTENT_TOPICS above). The override below is scoped to just
# these, so it doesn't affect unrelated topics like "why_choose" or
# "career_guidance" that might coincidentally share a word with an
# attribute topic (e.g. "join").
SUBJECT_COURSE_TOPICS = {
    "spoken_english",
    "rapido_english",
    "ielts",
    "ccc",
    "tally_gst",
    "advanced_excel",
    "python",
    "c_programming",
    "cpp",
    "web_designing",
    "web_development",
    "html",
    "css",
    "javascript",
    "php",
    "language",
}

# Ask lead details after this many REAL questions
LEAD_CAPTURE_AFTER = 3

# ------------------------------
# Academy Email Configuration
# ------------------------------
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

ACADEMY_EMAIL = os.getenv("ACADEMY_EMAIL")

# ==========================================================
# SESSION DATA
# ==========================================================

def save_message(session_id, sender, message):

    conversation = get_conversation(session_id)

    timestamp = datetime.now().strftime("%H:%M:%S")

    conversation.append(
        f"[{timestamp}] {sender}: {message}"
    )

def validate_email(email):

    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    return re.match(pattern, email)


def validate_mobile(number):

    number = number.replace(" ", "")

    if number.startswith("+91"):
        number = number[3:]

    return number.isdigit() and len(number) == 10

def capture_lead(session_id):

    print("\nBot: Before we continue, I'd like to know a few details.")

    while True:

        name = input("Your Name : ").strip()

        if name:
            break

        print("Bot: Name cannot be empty.")

    while True:

        email = input("Your Email : ").strip()

        if validate_email(email):
            break

        print("Bot: Please enter a valid email address.")

    while True:

        mobile = input("Your Mobile : ").strip()

        if validate_mobile(mobile):
            break

        print("Bot: Please enter a valid mobile number.")
    lead = get_lead(session_id)
    lead["name"] = name
    lead["email"] = email
    lead["mobile"] = mobile
    lead["captured"] = True

    print(f"\nBot: Thank you, {name}. Let's continue.\n")
    
def send_transcript_to_academy(session_id):

    lead = get_lead(session_id)

    conversation = get_conversation(session_id)

    if not lead["captured"]:
        return

    body = f"""
NEW WEBSITE LEAD

--------------------------------------

Name   : {lead['name']}
Email  : {lead['email']}
Mobile : {lead['mobile']}

--------------------------------------

Conversation

{chr(10).join(conversation)}
"""

    msg = MIMEText(body)

    msg["Subject"] = f"New Chatbot Lead - {lead['name']}"
    msg["From"] = SMTP_EMAIL
    msg["To"] = ACADEMY_EMAIL

    try:

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

    except Exception as e:

        print("Email Error:", e)
        
def _build_kb_vocab():
    """
    Build the vocabulary of meaningful words used across all KB keywords.

    Important: common glue words ("is", "of", "what", "are", "by", ...) are
    excluded even if they appear inside a multi-word keyword phrase (e.g.
    "medium of teaching", "who is shital academy"). Otherwise those glue
    words would leak into KB_VOCAB, which in turn defeats the stopword
    filter in preprocess() for every single message and pollutes topic
    scoring with noise tokens.
    """

    vocab = set()

    topics = shital_academy_knowledge.get("topics", {})

    for topic_data in topics.values():

        if isinstance(topic_data, dict):

            for phrase in topic_data.get("keywords", []):

                for word in phrase.lower().split():

                    if word in STOP_GLUE_WORDS:
                        continue

                    vocab.add(word)

    return vocab


# Glue words that should never count as meaningful KB vocabulary, even when
# they appear inside a multi-word keyword phrase.
STOP_GLUE_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "and", "or", "but", "if", "then", "so",
    "as", "at", "by", "with", "from", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his",
    "her", "its", "our", "their", "am", "do", "does", "did", "can",
    "could", "will", "would", "should", "shall", "may", "might", "must",
    "not", "no", "nor", "what", "who", "which", "your",
}

KB_VOCAB = _build_kb_vocab()

# ==========================================================
# NLP HELPER FUNCTIONS
# ==========================================================

def _contains_phrase(message, phrase):
    # \b requires a transition between a word char and a non-word char.
    # That breaks for phrases starting/ending in punctuation (e.g. "c++"),
    # since there's no such transition between two non-word characters.
    # Checking for "not alphanumeric" on either side instead handles both
    # ordinary words and symbol-containing keywords correctly.
    pattern = r'(?<![A-Za-z0-9])' + re.escape(phrase) + r'(?![A-Za-z0-9])'
    return re.search(pattern, message) is not None

def _correct_typo(word):

    if word in KB_VOCAB or len(word) < MIN_WORD_LEN_FOR_FUZZY:
        return word

    matches = difflib.get_close_matches(
        word,
        KB_VOCAB,
        n=1,
        cutoff=FUZZY_CUTOFF
    )

    return matches[0] if matches else word


def _fuzzy_contains(message, phrase_list, cutoff=FUZZY_CUTOFF, max_words_for_single_word=4):

    # Multi-word phrases are specific enough ("see you later", "take care")
    # that matching them anywhere in the message is safe regardless of
    # length.
    multi_word_phrases = [p for p in phrase_list if " " in p]

    if any(_contains_phrase(message, phrase) for phrase in multi_word_phrases):
        return True

    # Bare single-word keywords ("bye", "later", "hi") are a different
    # story: they're ordinary English words that can show up anywhere in a
    # completely unrelated sentence ("I'll pay the fees later"), and typo
    # variants of them ("byee", "helo") are only meaningful as a match when
    # the person is clearly just saying that one thing. So single-word
    # matching (exact or fuzzy) is only attempted on short messages - a
    # genuine goodbye/greeting is almost always sent as its own short
    # message, not embedded inside a longer question.
    words = message.split()

    if len(words) > max_words_for_single_word:
        return False

    single_word_phrases = [p for p in phrase_list if " " not in p]

    if any(_contains_phrase(message, phrase) for phrase in single_word_phrases):
        return True

    for word in words:

        if len(word) < MIN_WORD_LEN_FOR_FUZZY:
            continue

        if difflib.get_close_matches(
                word,
                single_word_phrases,
                n=1,
                cutoff=cutoff):

            return True

    return False

def greetings(message):

    greet_list = ["hello","hi","hey","howdy","greetings","good morning","good afternoon","good evening",
        "good day","what's up","whats up","how are you","how's it going",
        "how do you do","nice to meet you","welcome",
        "hy","hiya","yo","sup"]

    return _fuzzy_contains(
        message.strip().lower(),
        greet_list
    )
    
def goodbye(message):

    bye_list = ["goodbye","bye","bye bye","see you","see you later","see you soon",
        "take care","farewell","good night","later","cheers"]

    return _fuzzy_contains(
        message.strip().lower(),
        bye_list,
        # Ending the conversation is a much higher-stakes false positive
        # than a stray "Hello!" reply, so goodbye detection is held to an
        # even stricter length limit than the default.
        max_words_for_single_word=3
    )
    
def _score_topics(doc):
    """
    Score every KB topic against the given spaCy doc. Returns a dict of
    {topic_name: score}. Split out from preprocess() so the scoring logic
    can be inspected/tested directly instead of re-implemented ad hoc.
    """

    topics_dict = shital_academy_knowledge.get("topics", {})

    candidate_tokens = []

    for token in doc:

        if (
            token.is_punct
            or token.is_digit
            or token.like_num
            or token.is_space
        ):
            continue

        token_text = token.text.lower()
        token_lemma = token.lemma_.lower()

        if (
            token.is_stop
            and token_text not in KB_VOCAB
            and token_lemma not in KB_VOCAB
        ):
            continue

        candidate_tokens.append(
            (
                _correct_typo(token_text),
                _correct_typo(token_lemma)
            )
        )

    # Original message text (used for real phrase-level matching below).
    message_text = getattr(doc, "text", None)
    if message_text is None:
        message_text = " ".join(t.text for t in doc)
    message_text = message_text.lower()

    scores = {}

    for topic_name, topic_data in topics_dict.items():

        if not isinstance(topic_data, dict):
            continue

        keywords = [
            k.lower()
            for k in topic_data.get(
                "keywords",
                []
            )
        ]

        current_score = 0

        # Strong signal: a *multi-word* keyword phrase appears verbatim in
        # the message (word-boundary matched). Single-word keywords are
        # intentionally NOT scored here - they're already scored by the
        # token loop below, and double-counting them here let generic
        # shared words (e.g. "academy", "institute") outscore genuinely
        # specific multi-word phrase matches (e.g. "why shital academy").
        #
        # The bonus scales with the number of words in the phrase, so a
        # longer, more specific phrase (e.g. "rapid spoken english") beats
        # a shorter phrase it happens to contain (e.g. "spoken english")
        # when both belong to different topics.
        for kw in keywords:

            word_count = len(kw.split())

            if word_count > 1 and _contains_phrase(message_text, kw):

                current_score += 5 * word_count

        for token_text, token_lemma in candidate_tokens:

            if (
                token_text in keywords
                or token_lemma in keywords
            ):

                current_score += 5

            else:

                for kw in keywords:

                    # Only fall back to substring matching against
                    # single-word keywords, and only when both sides are
                    # long enough to be meaningful. Comparing against
                    # multi-word phrases here (or very short words) is what
                    # caused generic words like "course" or "tell" to
                    # falsely light up unrelated topics.
                    if " " in kw or len(kw) < MIN_WORD_LEN_FOR_FUZZY:
                        continue

                    if (
                        len(token_text) >= MIN_WORD_LEN_FOR_FUZZY
                        and (token_text in kw or kw in token_text)
                    ) or (
                        len(token_lemma) >= MIN_WORD_LEN_FOR_FUZZY
                        and (token_lemma in kw or kw in token_lemma)
                    ):

                        current_score += 3
                        break

        scores[topic_name] = current_score

    return scores


def preprocess(doc):

    topics_dict = shital_academy_knowledge.get("topics", {})
    scores = _score_topics(doc)

    best_answer = None
    best_topic = None
    best_score = 0

    for topic_name, current_score in scores.items():

        if current_score > best_score:

            best_score = current_score
            best_topic = topic_name
            best_answer = topics_dict[topic_name]["answer"]

    # If the message contains a genuine match for an attribute question
    # (fees, duration, timing, eligibility, branches, ...) AND the natural
    # winner above is just a specific course/subject name, the person is
    # actually asking about that attribute, not asking generically about
    # the course - e.g. "fees of spoken english" should answer the fees
    # question, not describe the Spoken English course. This override is
    # scoped to that specific conflict so it doesn't affect any other
    # topic (e.g. "why should I join" should still win as "why_choose",
    # not get hijacked by "admission" just because both mention "join").
    if best_topic in SUBJECT_COURSE_TOPICS:

        attribute_scores = {
            name: score
            for name, score in scores.items()
            if name in ATTRIBUTE_INTENT_TOPICS and score >= MIN_SCORE_THRESHOLD
        }

        if attribute_scores:
            best_topic = max(attribute_scores, key=attribute_scores.get)
            best_answer = topics_dict[best_topic]["answer"]
            best_score = attribute_scores[best_topic]

    if (
        best_answer
        and best_score >= MIN_SCORE_THRESHOLD
    ):

        return best_answer

    return (
        "Sorry, I didn't understand that. "
        "Can you please rephrase?"
    )
    
# ==========================================================
# MAIN CHAT LOOP
# ==========================================================

def run():

    session_id = create_session()

    try:

        print("=" * 60)
        print("Bot: Namaste! Welcome to Shital Academy.")
        print("Bot: I'm here to answer your questions.")
        print("Bot: Type 'bye' anytime to exit.")
        print("=" * 60)

        while True:

            question = input("\nYou : ").strip()

            if not question:
                continue

            # Save user message
            save_message(session_id, "User", question)

            message = question.lower()

            # Goodbye
            if goodbye(message):
                reply = "Goodbye! Thank you for contacting Shital Academy."
                print(f"\nBot: {reply}")
                save_message(session_id, "Bot", reply)
                break

            # Greeting
            if greetings(message):
                reply = "Hello! How can I help you today?"
                print(f"\nBot: {reply}")
                save_message(session_id, "Bot", reply)
                continue

            lead = get_lead(session_id)
            lead["question_count"] += 1

            if (
                lead["question_count"] >= LEAD_CAPTURE_AFTER
                and not lead["captured"]
            ):
                # capture_lead(session_id)
                pass

            doc = nlp(question)

            reply = preprocess(doc)
            
            # if kb not answer then ask llm
            if reply == (
                "Sorry, I didn't understand that. "
                "Can you please rephrase?"
            ):
                reply = ask_llm(question)

            print(f"\nBot: {reply}")
            save_message(session_id, "Bot", reply)

    except KeyboardInterrupt:
        print("\n\nBot: Chat ended.")
        
    except Exception as e:
        print("\nUnexpected Error:", e)
        
    finally:
        send_transcript_to_academy(session_id)
# ==========================================================
# PROGRAM START
# ==========================================================

if __name__ == "__main__":
    run()

    