from rapidfuzz import fuzz
from knowledge_loader import get_knowledge
import re

KNOWLEDGE = get_knowledge()
COURSES = KNOWLEDGE["courses"]


def detect_course(user_text: str):
    """
    Detect the best matching course.

    Priority:
    1. Exact course name
    2. Exact alias
    3. Exact keyword
    4. Fuzzy course name
    """

    text = re.sub(r"[^\w\s]", "", user_text.lower()).strip()
    words = set(text.split())
    
    corrected_words = []

    for word in words:
        best = word
        best_score = 0

        for course in COURSES.values():
            for keyword in course.get("keywords", []):
                keyword = keyword.lower()

                if " " not in keyword:
                    score = fuzz.ratio(word, keyword)

                    if score > best_score:
                        best_score = score
                        best = keyword

        if best_score >= 85:
            corrected_words.append(best)
        else:
            corrected_words.append(word)

    words = set(corrected_words)

    best_course = None
    best_score = 0

    for course_id, course in COURSES.items():

        # -------------------------
        # 1. Exact Course Name
        # -------------------------
        course_name = course.get("name", "").lower()

        if course_name in text:
            score = 100

            if score > best_score:
                best_score = score
                best_course = course_id

        # -------------------------
        # 2. Exact Alias
        # -------------------------
        for alias in course.get("aliases", []):
            alias = alias.lower()

            if alias in text:
                score = 98

                if score > best_score:
                    best_score = score
                    best_course = course_id
        # -------------------------
        # 3. Exact Keyword
        # -------------------------
        for keyword in course.get("keywords", []):
            keyword = keyword.lower()

            # Multi-word keyword
            if " " in keyword:
                if keyword in text:
                    score = 95

                    if score > best_score:
                        best_score = score
                        best_course = course_id

            # Single-word keyword
            else:
                # Exact word match
                if keyword in words:
                    score = 95

                    if score > best_score:
                        best_score = score
                        best_course = course_id

                # Fuzzy typo match
                else:
                    for word in words:
                        fuzzy_score = fuzz.ratio(word, keyword)

                        if fuzzy_score >= 85:
                            score = 92

                            if score > best_score:
                                best_score = score
                                best_course = course_id 
        # -------------------------
        # 4. Fuzzy Course Name Only
        # -------------------------
        score = max(
            fuzz.partial_ratio(text, course_name),
            fuzz.token_sort_ratio(text, course_name),
            fuzz.token_set_ratio(text, course_name),
            fuzz.WRatio(text, course_name),
        )
        if score > best_score:
            best_score = score
            best_course = course_id

    MIN_CONFIDENCE = 88

    if best_score < MIN_CONFIDENCE:
        return None, best_score

    return best_course, best_score
    

def get_course_data(course_id):
    return COURSES.get(course_id)