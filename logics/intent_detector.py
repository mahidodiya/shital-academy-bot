from rapidfuzz import fuzz
from knowledge_loader import get_knowledge
import re

KNOWLEDGE = get_knowledge()
INTENTS = KNOWLEDGE["common"]["intents"]["intents"]

MIN_CONFIDENCE = 80

# Keywords shorter than this are only ever matched with an exact
# word-boundary check (score=100 or nothing). rapidfuzz's
# partial_ratio/token_set_ratio/WRatio are unreliable for very
# short keywords (e.g. "bye", "job", "exit") compared against a
# much longer, unrelated sentence - small coincidental character
# overlap can push the score above MIN_CONFIDENCE and cause a
# completely wrong intent to "win". Longer, more distinctive
# keywords (e.g. "eligibility", "certificate") still get typo
# tolerance via fuzzy matching.
MIN_KEYWORD_LEN_FOR_FUZZY = 6


def detect_intent(user_text):
    """
    Detect the user's intent using intents.json.
    Returns:
        (intent_name, score)
    """

    text = user_text.lower().strip()

    best_intent = None
    best_score = 0
    best_priority = -1

    for intent in INTENTS:

        intent_name = intent["id"]
        priority = intent.get("priority", 0)

        for phrase in intent.get("keywords", []):

            phrase = phrase.lower()

            # Ignore tiny keywords during fuzzy matching
            if len(phrase) < 3:
                continue

            # -------------------------
            # Exact Match
            # -------------------------
            if re.search(r"\b" + re.escape(phrase) + r"\b", text):

                score = 100

            # -------------------------
            # Fuzzy Match
            # -------------------------
            # Only attempted for keywords long/distinctive enough
            # that a high fuzzy score is meaningful. Short keywords
            # that don't appear verbatim simply don't match - see
            # MIN_KEYWORD_LEN_FOR_FUZZY above.
            # -------------------------
            elif len(phrase) >= MIN_KEYWORD_LEN_FOR_FUZZY:

                score = max(
                    fuzz.partial_ratio(text, phrase),
                    fuzz.token_sort_ratio(text, phrase),
                    fuzz.token_set_ratio(text, phrase),
                    fuzz.WRatio(text, phrase),
                )

            else:

                score = 0

            # -------------------------
            # Save Best Match
            # -------------------------
            if (
                score > best_score
                or (score == best_score and priority > best_priority)
            ):
                best_score = score
                best_priority = priority
                best_intent = intent_name

    if best_score < MIN_CONFIDENCE:
        return None, best_score

    return best_intent, best_score