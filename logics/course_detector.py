from rapidfuzz import fuzz
from knowledge_loader import get_knowledge
import re

KNOWLEDGE = get_knowledge()
COURSES = KNOWLEDGE["courses"]

# Courses officially offered by the academy
OFFERED_COURSES = {
    # IT Courses
    "java": "java",
    "python": "python",
    "c": "c",
    "c++": "cpp",
    "html": "html",
    "bootstrap": "bootstrap",
    "web development": "web_development",
    "web designing": "web_designing",

    # English Courses
    "foundation course": "foundation_english",
    "rapido english course": "rapido_english",
    "basic to advanced english course": "spoken_english",
    "special speaking course for english medium students": "spoken_english",
    "ielts preparation": "ielts",
    "customized english courses": "customized_english",
}

def detect_course(user_text: str):
    """
    Detect the best matching course.

    Priority:
    1. Exact official course name / alias
    2. Exact keyword
    3. Fuzzy match against individual course names/aliases
    4. Fuzzy typo correction for short course names

    Important:
    - Avoids matching unrelated courses such as React -> Web Designing
    - Allows typos such as Pythn -> Python
    - Allows typos such as Web Developement -> Web Development
    """

    text = user_text.lower().strip()

    # Remove common punctuation, but keep characters such as . and #
    # because names like ".NET", "C++" can contain them.
    cleaned_text = re.sub(r"[!?;,():]", " ", text)
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    words = set(cleaned_text.split())

    # =========================================================
    # 1. EXACT OFFICIALLY OFFERED COURSE MATCH
    # =========================================================

    for offered_name, course_id in OFFERED_COURSES.items():

        if " " in offered_name:
            if offered_name in cleaned_text:
                return course_id, 100.0

        else:
            if offered_name in words:
                return course_id, 100.0

    # =========================================================
    # 3. FUZZY MATCH ONLY AGAINST COURSE NAMES / ALIASES
    # =========================================================
    #
    # We intentionally DO NOT fuzzy-match the entire sentence
    # against course names.
    #
    # Example:
    # "Tell me about React"
    #
    # should NOT become Web Designing just because
    # "Tell me about React" has a partial similarity to it.
    # =========================================================

    candidates = []

    for course_id, course in COURSES.items():

        course_name = course.get("name", "").lower().strip()

        if course_name:
            candidates.append((course_name, course_id))

        for alias in course.get("aliases", []):
            alias = alias.lower().strip()

            if alias:
                candidates.append((alias, course_id))

    # =========================================================
    # 4. FUZZY MATCH COURSE NAMES / ALIASES
    # =========================================================

    best_course = None
    best_score = 0.0

    for candidate, course_id in candidates:

        candidate_words = candidate.split()

        # -----------------------------------------------------
        # Single-word course names
        # Example:
        # Pythn     -> Python
        # Pythoon   -> Python
        # Jvaa      -> Java
        # Bootstrp  -> Bootstrap
        # -----------------------------------------------------
        if len(candidate_words) == 1:

            candidate_word = candidate_words[0]

            for word in words:

                if len(word) < 3:
                    continue

                score = fuzz.ratio(word, candidate_word)

                if score > best_score:
                    best_score = score
                    best_course = course_id

        # -----------------------------------------------------
        # Multi-word course names
        # Example:
        # Web Developement -> Web Development
        # Web Desiging     -> Web Designing
        # -----------------------------------------------------
        else:

            # Extract meaningful words from the user's message.
            # This prevents unrelated words such as "Tell me about"
            # from dominating the comparison.
            text_words = [
                word for word in words
                if len(word) >= 3
            ]

            if not text_words:
                continue

            candidate_word_scores = []

            for candidate_word in candidate_words:

                # Find the closest word in the user's message.
                word_score = max(
                    fuzz.ratio(candidate_word, word)
                    for word in text_words
                )

                candidate_word_scores.append(word_score)

            # Every important word in the course name must have
            # a reasonably good match.
            if candidate_word_scores:

                score = min(candidate_word_scores)

                if score > best_score:
                    best_score = score
                    best_course = course_id


    # =========================================================
    # 5. FUZZY MATCH CONFIDENCE
    # =========================================================

    MIN_CONFIDENCE = 88

    if best_course is None or best_score < MIN_CONFIDENCE:
        return None, best_score

    return best_course, best_score
def get_course_data(course_id):
    return COURSES.get(course_id)

