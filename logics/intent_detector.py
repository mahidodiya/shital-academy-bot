from rapidfuzz import fuzz
from knowledge_loader import get_knowledge
import re

KNOWLEDGE = get_knowledge()
INTENTS = KNOWLEDGE["common"]["intents"]["intents"]

# Production rule: intent matching must be conservative.
# A false positive is worse than asking the user to clarify.
EXACT_CONFIDENCE = 100
FUZZY_CONFIDENCE = 90
MIN_FUZZY_KEYWORD_LEN = 4
MAX_FUZZY_WINDOW = 5

# These intents only identify a course/category. When they tie with a
# question-specific intent such as fees, syllabus, or study material,
# the question-specific intent must win.
BROAD_COURSE_INTENTS = {
    "computer_course",
    "english_course",
}


def _normalize(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s+#.]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _windows(words, size):
    for i in range(len(words) - size + 1):
        yield " ".join(words[i:i + size])


def _fuzzy_keyword_score(text, phrase):
    """Typo tolerance without comparing the whole sentence to a keyword."""
    words = text.split()
    phrase_words = phrase.split()

    if not words or not phrase_words:
        return 0

    target_size = len(phrase_words)
    sizes = {target_size}

    # For single words, compare against individual words only.
    # For phrases, compare against local word windows.
    if target_size > 1:
        sizes.update({max(1, target_size - 1), target_size + 1})

    best = 0
    for size in sizes:
        if size < 1 or size > MAX_FUZZY_WINDOW or size > len(words):
            continue
        for window in _windows(words, size):
            score = fuzz.ratio(window, phrase)
            best = max(best, score)

    return best


def _augment_intents(intents):
    """Add high-value production phrases without mutating the loaded JSON."""
    additions = {
        "certificate": ["government recognized", "govt recognized", "recognized certificate", "recognised certificate", "certificate standard"],
        "course_modules": [
            "django", "flask", "power bi", "powerbi", "sql", "mysql",
            "payroll", "export sales", "gujarati typing", "english typing",
            "ai tools", "shortcut keys", "shortcuts", "tally and excel",
        ],
        "course_eligibility": ["senior citizen", "senior citizens", "can senior citizen join", "can anyone join"],
    }
    merged = []
    for item in intents:
        item = dict(item)
        extra = additions.get(item.get("id"), [])
        if extra:
            item["keywords"] = list(dict.fromkeys(list(item.get("keywords", [])) + extra))
        merged.append(item)
    return merged


def detect_intent(user_text):
    """
    Detect intent conservatively.

    Returns:
        (intent_name | None, confidence)

    Important production behavior:
    - Exact phrase matches are preferred.
    - Fuzzy matching is performed against local words/windows, not the
      entire user sentence. This prevents unrelated questions such as
      "what is the weather today" from matching "contact" or "timings".
    - Low-confidence matches return (None, score).
    """
    text = _normalize(user_text)

    if not text:
        return None, 0.0

    best_intent = None
    best_score = 0.0
    best_priority = -1
    best_phrase_length = 0

    for intent in _augment_intents(INTENTS):
        intent_name = intent["id"]
        priority = intent.get("priority", 0)

        # fallback is never a fuzzy candidate.
        if intent_name == "fallback":
            continue

        for raw_phrase in intent.get("keywords", []):
            phrase = _normalize(raw_phrase)
            if not phrase or len(phrase) < 2:
                continue

            # Exact phrase/word-boundary match.
            pattern = r"(?<![\w])" + re.escape(phrase) + r"(?![\w])"
            if re.search(pattern, text):
                score = EXACT_CONFIDENCE
            else:
                # Fuzzy typo correction only for sufficiently distinctive
                # phrases. Never fuzzy-match a one/two-letter token.
                if len(phrase.replace(" ", "")) < MIN_FUZZY_KEYWORD_LEN:
                    continue
                score = _fuzzy_keyword_score(text, phrase)
                if score < FUZZY_CONFIDENCE:
                    continue

            phrase_length = len(phrase.split())

            candidate_is_specific = intent_name not in BROAD_COURSE_INTENTS
            best_is_specific = (
                best_intent is not None
                and best_intent not in BROAD_COURSE_INTENTS
            )

            should_replace = (
                score > best_score
                or (
                    score == best_score
                    and (
                        # A specific question intent beats a broad course
                        # category match at the same confidence.
                        (candidate_is_specific and not best_is_specific)
                        or (
                            candidate_is_specific == best_is_specific
                            and (
                                phrase_length > best_phrase_length
                                or (
                                    phrase_length == best_phrase_length
                                    and priority > best_priority
                                )
                            )
                        )
                    )
                )
            )

            if should_replace:
                best_score = score
                best_priority = priority
                best_phrase_length = phrase_length
                best_intent = intent_name

    if best_intent is None:
        return None, best_score

    return best_intent, best_score
