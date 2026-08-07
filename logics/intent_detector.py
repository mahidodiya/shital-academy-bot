from rapidfuzz import fuzz
from knowledge_loader import get_knowledge
import re

KNOWLEDGE = get_knowledge()
INTENTS = KNOWLEDGE["common"]["intents"]["intents"]

MIN_CONFIDENCE = 80


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
            else:

                score = max(
                    fuzz.partial_ratio(text, phrase),
                    fuzz.token_sort_ratio(text, phrase),
                    fuzz.token_set_ratio(text, phrase),
                    fuzz.WRatio(text, phrase),
                )

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