from rapidfuzz import fuzz
import re
from knowledge_loader import get_knowledge

KNOWLEDGE = get_knowledge()

ACADEMY_FAQS = KNOWLEDGE["academy"]["faq"]["faqs"]
COURSES = KNOWLEDGE["courses"]

MIN_CONFIDENCE = 80


def _normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _find_best_match(query, faqs):
    """
    Search a FAQ list and return the best matching FAQ.
    """

    query = _normalize(query)
    query_words = set(query.split())

    best_faq = None
    best_score = 0
    best_priority = -1

    for faq in faqs:

        priority = faq.get("priority", 0)

        # =====================================================
        # 1. Exact Keyword Match (Highest Priority)
        # =====================================================
        for keyword in faq.get("keywords", []):

            keyword = _normalize(keyword)

            if " " in keyword:
                matched = keyword in query
            else:
                matched = keyword in query_words

            if matched:
                return faq, 100

        # =====================================================
        # 2. Exact Question Match
        # =====================================================
        question = _normalize(faq["question"])

        if question in query:
            return faq, 99

        # =====================================================
        # 3. Fuzzy Keyword Match
        # =====================================================
        for keyword in faq.get("keywords", []):

            keyword = _normalize(keyword)

            if len(keyword) <= 2:
                continue

            score = max(
                fuzz.token_set_ratio(query, keyword),
                fuzz.partial_ratio(query, keyword),
            )

            score -= 5

            if (
                score > best_score
                or (score == best_score and priority > best_priority)
            ):
                best_score = score
                best_priority = priority
                best_faq = faq

        # =====================================================
        # 4. Fuzzy Question Match
        # =====================================================
        score = max(
            fuzz.token_set_ratio(query, question),
            fuzz.partial_ratio(query, question),
        )

        score -= 10

        if (
            score > best_score
            or (score == best_score and priority > best_priority)
        ):
            best_score = score
            best_priority = priority
            best_faq = faq

    if best_score < MIN_CONFIDENCE:
        return None, best_score

    return best_faq, best_score


def search_academy_faq(query):
    return _find_best_match(query, ACADEMY_FAQS)


def search_course_faq(course_id, query):

    course = COURSES.get(course_id)

    if not course:
        return None, 0

    return _find_best_match(query, course.get("faqs", []))


def search_faq(query, course_id=None):
    """
    Search course FAQ first (if course detected),
    then academy FAQ.
    """

    if course_id:
        faq, score = search_course_faq(course_id, query)

        if faq:
            return faq, score

    return search_academy_faq(query)