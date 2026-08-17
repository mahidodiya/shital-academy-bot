"""
logics/greeting_detector.py

Fuzzy, typo-tolerant greeting / goodbye detection.

Tolerates minor typos ("helo", "byee") and phrase-level greetings
("good morning"), while staying conservative on longer messages so a
stray word doesn't misfire mid-sentence (see _fuzzy_contains below).

chatbot.py only calls greetings()/goodbye() - it does not know or
care how the matching is implemented.
"""

import re
import difflib


FUZZY_CUTOFF = 0.8
MIN_WORD_LEN_FOR_FUZZY = 4

GREETING_PHRASES = [
    "hello", "hi", "hey", "howdy", "greetings",
    "good morning", "good afternoon", "good evening", "good day",
    "what's up", "whats up", "how are you", "how's it going",
    "how do you do", "nice to meet you", "welcome",
    "hy", "hiya", "yo", "sup",
]

GOODBYE_PHRASES = [
    "goodbye", "bye", "bye bye", "see you", "see you later",
    "see you soon", "take care", "farewell", "good night",
    "later", "cheers",
]


def _contains_phrase(message, phrase):
    """
    Word-boundary match that also works for phrases starting/ending in
    punctuation, where \\b doesn't fire because there's no transition
    between two non-word characters.
    """

    pattern = r'(?<![A-Za-z0-9])' + re.escape(phrase) + r'(?![A-Za-z0-9])'
    return re.search(pattern, message) is not None


def _fuzzy_contains(message, phrase_list, cutoff=FUZZY_CUTOFF, max_words_for_single_word=4):
    """
    True if message matches one of phrase_list, either verbatim or
    (for short messages only) via a typo-tolerant single-word match.
    """

    multi_word_phrases = [p for p in phrase_list if " " in p]

    if any(_contains_phrase(message, phrase) for phrase in multi_word_phrases):
        return True

    # Single-word matching (exact or fuzzy) is only attempted on short
    # messages - a genuine greeting/goodbye is almost always sent as its
    # own short message, not embedded inside a longer question.
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
            cutoff=cutoff,
        ):
            return True

    return False


def greetings(message):
    """
    Detect greetings, tolerant of minor typos.
    """

    return _fuzzy_contains(
        message.strip().lower(),
        GREETING_PHRASES,
    )


def goodbye(message):
    """
    Detect goodbye messages, tolerant of minor typos.

    Held to a stricter length limit than greetings, since ending the
    conversation is a much higher-stakes false positive than a stray
    "Hello!" reply.
    """

    return _fuzzy_contains(
        message.strip().lower(),
        GOODBYE_PHRASES,
        max_words_for_single_word=3,
    )