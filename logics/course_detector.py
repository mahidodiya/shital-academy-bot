"""Course detection for Shital Academy.

The course JSON files are the single source of truth.  We deliberately avoid
fuzzy matching arbitrary KB keywords because generic words such as
"english", "course", "accounting", etc. can cause false positives.
"""

import re
from functools import lru_cache
from rapidfuzz import fuzz

from knowledge_loader import get_knowledge

KNOWLEDGE = get_knowledge()
COURSES = KNOWLEDGE.get("courses", {})

# Conservative aliases for ambiguous/common user wording.  Course names and
# aliases from the JSON files are still the primary source of truth.
EXTRA_ALIASES = {
    "ccc": ["ccc", "advanced ccc", "basic computer course", "computer basics course"],
    "data_analytics": [
        "data analytics", "data analyst", "data analyst course",
        "data analysis", "data analysis course", "business analytics",
        "analytics course", "python for data analysis",
    ],
    "excel": ["excel", "ms excel", "microsoft excel", "advanced excel", "advanced ms excel"],
    "foundation_english": [
        "foundation english", "foundation english course", "basic english course",
        "foundation course", "english foundation course",
    ],
    "ielts": ["ielts", "ielts course", "ielts coaching", "ielts training", "ielts preparation"],
    "office_executive": [
        "office executive", "office executive course", "office administration course",
        "office management course", "back office course",
    ],
    "python": ["python", "python programming", "python programming course", "python course"],
    "rapido_english": ["rapido english", "rapido english course", "rapid english", "rapid english course"],
    "spoken_english": [
        "spoken english", "spoken english course", "english speaking course",
        "english speaking", "speaking english",
    ],
    "tally": [
        "tally", "tally prime", "tally prime with gst", "tally erp", "tally course",
    ],
    "web_designing": [
        "web designing", "web design", "website designing", "web designing course",
    ],
    "web_development": [
        "web development", "website development", "web developer course",
        "web programming", "website programming",
    ],

    # Courses officially offered by the academy but without a detailed
    # course JSON yet. They are still detectable so the bot can give a
    # safe "details not available" response instead of pretending they
    # do not exist.
    "c": ["c", "c programming", "c language", "c course"],
    "cpp": ["c++", "cpp", "c plus plus", "c++ course"],
    "java": ["java", "java programming", "java course"],
    "html": ["html", "html course", "html web course"],
    "bootstrap": ["bootstrap", "bootstrap course"],
    "customized_english": [
        "customized english", "customised english",
        "customized english course", "customised english course",
    ],
    "basic_to_advanced_english": [
        "basic to advanced english", "basic to advanced english course",
    ],
    "special_speaking_english": [
        "special speaking", "special speaking course",
        "special speaking course for english medium students",
    ],
}

# Words that are too generic to identify a course by themselves.
GENERIC_WORDS = {
    "course", "courses", "class", "classes", "training", "learn", "learning",
    "teach", "teaching", "academy", "skill", "skills", "program", "programming",
    "english", "office", "computer", "data", "analysis", "analytics", "website",
    "web", "design", "development", "basic", "advanced",
}


def _normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = text.replace("’", "'")
    # Keep +/# because they can be meaningful in course names in future.
    text = re.sub(r"[^a-z0-9+#.\s'-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _word_tokens(text: str):
    return re.findall(r"[a-z0-9+#.]+", text)


def _build_candidates():
    """Build (phrase, course_id, source_type) candidates from the KB."""
    candidates = []

    # Include both detailed course JSON files and officially offered
    # courses that do not yet have a detailed JSON file.
    all_course_ids = set(COURSES.keys()) | set(EXTRA_ALIASES.keys())

    for course_id in all_course_ids:
        course = COURSES.get(course_id, {})
        phrases = []
        name = course.get("name", "")
        if name:
            phrases.append(name)
        phrases.extend(course.get("aliases", []) or [])
        phrases.extend(EXTRA_ALIASES.get(course_id, []))

        seen = set()
        for phrase in phrases:
            phrase = _normalize(phrase)
            if not phrase or phrase in seen:
                continue
            seen.add(phrase)
            candidates.append((phrase, course_id, "alias"))

    # Longest first makes "tally prime with gst" win before "tally".
    candidates.sort(key=lambda x: (-len(x[0].split()), -len(x[0])))
    return tuple(candidates)


COURSE_CANDIDATES = _build_candidates()


@lru_cache(maxsize=2048)
def detect_course(user_text: str):
    """Return ``(course_id, confidence)`` or ``(None, confidence)``.

    Matching order:
      1. Exact course name/alias as a phrase.
      2. Exact single-word alias only when it is distinctive.
      3. High-confidence fuzzy typo correction against names/aliases.

    KB keywords are intentionally *not* used as unrestricted course aliases;
    they often contain generic terms and cause false positives.
    """
    text = _normalize(user_text)
    if not text:
        return None, 0.0

    words = set(_word_tokens(text))

    # 1) Exact phrase/name/alias match.
    for phrase, course_id, _ in COURSE_CANDIDATES:
        if len(phrase.split()) >= 2:
            if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text):
                return course_id, 100.0

    # 2) Exact distinctive single-word aliases.
    single_word_map = {}
    for phrase, course_id, _ in COURSE_CANDIDATES:
        if len(phrase.split()) != 1:
            continue
        if phrase in GENERIC_WORDS:
            continue
        single_word_map.setdefault(phrase, set()).add(course_id)

    for word in words:
        course_ids = single_word_map.get(word)
        if course_ids and len(course_ids) == 1:
            return next(iter(course_ids)), 100.0

    # 3) Fuzzy typo matching against official names/aliases only.
    best_course = None
    best_score = 0.0

    for phrase, course_id, _ in COURSE_CANDIDATES:
        phrase_words = phrase.split()

        # Single-word aliases: compare individual user tokens.
        if len(phrase_words) == 1:
            target = phrase_words[0]
            if target in GENERIC_WORDS or len(target) < 3:
                continue

            for word in words:
                if len(word) < 3:
                    continue
                score = fuzz.ratio(word, target)
                # Short words need stricter matching to avoid false positives.
                threshold = 92 if len(target) <= 4 else 88
                if score >= threshold and score > best_score:
                    best_course = course_id
                    best_score = float(score)
            continue

        # Multi-word aliases: every non-generic word must have a strong match.
        meaningful = [w for w in phrase_words if w not in GENERIC_WORDS and len(w) >= 3]
        if not meaningful:
            continue

        token_scores = []
        for target in meaningful:
            token_scores.append(max(fuzz.ratio(target, word) for word in words if len(word) >= 3))

        if token_scores:
            score = min(token_scores)
            # Require strong agreement for all meaningful words.
            if score >= 88 and score > best_score:
                best_course = course_id
                best_score = float(score)

    if best_course is None:
        return None, best_score

    return best_course, best_score


def get_course_data(course_id):
    """Return course data from the loaded knowledge base."""
    return COURSES.get(course_id)