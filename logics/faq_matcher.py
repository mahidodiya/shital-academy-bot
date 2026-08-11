from rapidfuzz import fuzz
import re

from knowledge_loader import get_knowledge

KNOWLEDGE = get_knowledge()

ACADEMY_FAQS = KNOWLEDGE["academy"]["faq"]["faqs"]
COURSES = KNOWLEDGE["courses"]

MIN_CONFIDENCE = 80


# =========================================================
# FAQ → INTENT MAPPING
# =========================================================

FAQ_INTENTS = {

    "admission_process": "admission",
    "course_guidance": "recommendation",
    "documents_required": "admission",
    "eligibility": "course_eligibility",
    "age_limit": "course_eligibility",
    "admission_open": "admission",
    "join_anytime": "admission",
    "demo_class": "demo_class",
    "registration_process": "admission",

    "fees_information": "course_fees",
    "installment_payment": "course_fees",
    "payment_methods": "course_fees",
    "discounts": "course_fees",
    "refund_policy": "course_fees",
    "fee_receipt": "course_fees",

    "batch_timings": "course_info",
    "weekend_batches": "course_info",
    "online_classes": "course_info",
    "offline_classes": "course_info",
    "batch_change": "course_info",
    "missed_class": "course_info",

    "faculty_experience": "academy_info",
    "individual_attention": "academy_info",

    "study_material": "course_modules",
    "practical_training": "course_modules",

    "certificate": "course_certificate",

    "placement_support": "placement",
    "internship": "placement",

    "about_academy": "academy_info",
    "why_choose_academy": "academy_info",

    "contact_information": "contact",
    "branch_locations": "contact",

    "parking_facility": "academy_info",
    "computer_lab": "academy_info",

    "attendance": "academy_info",
    "holiday_classes": "academy_info",
    "leave_policy": "academy_info",

    "language_of_instruction": "academy_info",
    "beginner_friendly": "beginner_friendly",
    "working_professionals": "course_eligibility",

    "course_duration": "course_duration",
    "course_mode": "course_info",

    "student_support": "help",
    "doubt_solving": "help",

    "academy_services": "academy_info",
}


# =========================================================
# Helpers
# =========================================================

def _normalize(text):
    """
    Normalize text for matching.
    """

    text = text.lower().strip()

    text = re.sub(r"[^\w\s]", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text


def _calculate_score(query, candidate):
    """
    Calculate fuzzy similarity score.
    """

    return max(
        fuzz.partial_ratio(query, candidate),
        fuzz.token_sort_ratio(query, candidate),
        fuzz.token_set_ratio(query, candidate),
        fuzz.WRatio(query, candidate),
    )


# =========================================================
# Find Best FAQ
# =========================================================

def _find_best_match(query, faqs, intent=None):
    """
    Search FAQ list and return the best matching FAQ.

    Uses:
    1. Detected intent
    2. FAQ-specific keywords
    3. FAQ question similarity
    4. FAQ priority
    """

    query = _normalize(query)

    # -----------------------------------------------------
    # Intent → FAQ → keywords
    # -----------------------------------------------------

    intent_keywords = {

        "course_fees": {
            "fees_information": [
                "fee", "fees", "price", "cost", "charges"
            ],
            "installment_payment": [
                "installment", "installments", "emi",
                "monthly payment", "partial payment"
            ],
            "payment_methods": [
                "payment", "cash", "upi", "card",
                "bank transfer"
            ],
            "discounts": [
                "discount", "offer", "scholarship",
                "concession"
            ],
            "refund_policy": [
                "refund", "cancel", "money back"
            ],
            "fee_receipt": [
                "receipt", "invoice", "payment proof"
            ],
        },

        "course_duration": {
            "course_duration": [
                "duration", "how long", "months",
                "weeks", "time"
            ],
        },

        "course_certificate": {
            "certificate": [
                "certificate", "certification"
            ],
        },

        "course_eligibility": {
            "eligibility": [
                "eligibility", "qualification",
                "who can join"
            ],
            "beginner_friendly": [
                "beginner", "beginners",
                "no experience"
            ],
            "working_professionals": [
                "working professional",
                "employee"
            ],
        },

        "admission": {
            "admission_process": [
                "admission", "join", "enroll",
                "registration", "apply"
            ],
            "documents_required": [
                "documents", "id proof", "photo"
            ],
            "admission_open": [
                "admission open", "enrollment"
            ],
            "join_anytime": [
                "join anytime", "late admission"
            ],
            "registration_process": [
                "register", "registration",
                "enrollment"
            ],
        },

        "demo_class": {
            "demo_class": [
                "demo", "trial", "sample class"
            ],
        },

        "placement": {
            "placement_support": [
                "placement", "job", "career"
            ],
            "internship": [
                "internship",
                "industrial training"
            ],
        },
    }

    # -----------------------------------------------------
    # Find best FAQ
    # -----------------------------------------------------

    best_faq = None
    best_score = 0
    best_priority = -1

    for faq in faqs:

        faq_id = faq.get("id")
        priority = faq.get("priority", 0)

        faq_intent = FAQ_INTENTS.get(faq_id)

        # -------------------------------------------------
        # Intent compatibility
        # -------------------------------------------------

        intent_bonus = 0

        if intent:

            # If FAQ has a mapped intent,
            # only allow matching intent.
            if faq_intent:

                if faq_intent != intent:
                    continue

                intent_bonus = 20

        # -------------------------------------------------
        # FAQ-specific keyword bonus
        # -------------------------------------------------

        faq_keyword_bonus = 0

        if intent in intent_keywords:

            faq_keywords = intent_keywords[intent].get(
                faq_id,
                []
            )

            for keyword in faq_keywords:

                keyword = _normalize(keyword)

                if not keyword:
                    continue

                if re.search(
                    r"\b" + re.escape(keyword) + r"\b",
                    query
                ):
                    faq_keyword_bonus = 40
                    break

        # -------------------------------------------------
        # Question
        # -------------------------------------------------

        question = _normalize(
            faq.get("question", "")
        )

        if not question:
            continue

        # Exact question
        if query == question:

            score = 120

        # Complete FAQ question inside query
        elif re.search(
            r"\b" + re.escape(question) + r"\b",
            query
        ):

            score = 115

        else:

            score = _calculate_score(
                query,
                question
            )

            score -= 5

        final_score = (
            score
            + intent_bonus
            + faq_keyword_bonus
        )

        # -------------------------------------------------
        # Question score
        # -------------------------------------------------

        if (
            final_score > best_score
            or (
                final_score == best_score
                and priority > best_priority
            )
        ):

            best_score = final_score
            best_priority = priority
            best_faq = faq

        # -------------------------------------------------
        # FAQ keywords
        # -------------------------------------------------

        for keyword in faq.get("keywords", []):

            keyword = _normalize(keyword)

            if not keyword:
                continue

            # Exact keyword
            if re.search(
                r"\b" + re.escape(keyword) + r"\b",
                query
            ):

                score = 98

            else:

                score = _calculate_score(
                    query,
                    keyword
                )

                score -= 2

            final_score = (
                score
                + intent_bonus
                + faq_keyword_bonus
            )

            if (
                final_score > best_score
                or (
                    final_score == best_score
                    and priority > best_priority
                )
            ):

                best_score = final_score
                best_priority = priority
                best_faq = faq

    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    if best_score < MIN_CONFIDENCE:
        return None, min(100, best_score)

    return best_faq, min(100, best_score)
# =========================================================
# Academy FAQ
# =========================================================

def search_academy_faq(query, intent=None):

    return _find_best_match(
        query,
        ACADEMY_FAQS,
        intent
    )


# =========================================================
# Course FAQ
# =========================================================

def search_course_faq(course_id, query, intent=None):

    course = COURSES.get(course_id)

    if not course:
        return None, 0

    faqs = course.get("faqs", [])

    if not faqs:
        return None, 0

    return _find_best_match(
        query,
        faqs,
        intent
    )


# =========================================================
# Main FAQ Search
# =========================================================

def search_faq(query, course_id=None, intent=None):
    """
    Search course FAQ first when a course is detected,
    then academy FAQ.

    Course-specific FAQs have priority over academy FAQs.
    """

    # -----------------------------------------------------
    # Course FAQ
    # -----------------------------------------------------

    if course_id:

        faq, score = search_course_faq(
            course_id,
            query,
            intent
        )

        if faq:
            return faq, score

    # -----------------------------------------------------
    # Academy FAQ
    # -----------------------------------------------------

    return search_academy_faq(
        query,
        intent
    )