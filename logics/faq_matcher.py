from rapidfuzz import fuzz
import re

from knowledge_loader import get_knowledge

KNOWLEDGE = get_knowledge()

ACADEMY_FAQS = KNOWLEDGE["academy"]["faq"]["faqs"]
COURSES = KNOWLEDGE["courses"]

MIN_CONFIDENCE = 80


# A course FAQ is allowed to answer only the user-facing topic it belongs
# to. This prevents a vague fuzzy match such as "python syllabus" from
# selecting an unrelated FAQ like "who can join Python?".
COURSE_FAQ_TOPIC_TERMS = {
    "course_modules": (
        "syllabus", "module", "modules", "topic", "topics",
        "curriculum", "course content", "what will i learn",
    ),
    "learning_outcomes": (
        "learn", "learning", "outcome", "outcomes", "skills",
    ),
    "course_fees": (
        "fee", "fees", "price", "cost", "charge", "payment",
    ),
    "course_duration": (
        "duration", "how long", "months", "weeks",
    ),
    "course_certificate": (
        "certificate", "certification",
    ),
    "course_eligibility": (
        "eligibility", "eligible", "qualification", "prerequisite",
        "requirements", "who can join",
    ),
    "beginner_friendly": (
        "beginner", "beginners", "no experience", "suitable",
    ),
    "practice_tests": (
        "mock test", "mock tests", "practice test", "practice tests", "test practice",
    ),
    "prerequisites": (
        "prerequisite", "prior programming", "prior knowledge", "coding knowledge",
        "programming knowledge", "experience required", "no experience",
    ),
    "equipment": (
        "laptop", "computer required", "own laptop",
    ),
    "study_material": (
        "study material", "notes", "books", "learning material",
        "course material",
    ),
}


def _faq_matches_topic(faq, intent):
    """Return True when a course FAQ belongs to the requested topic."""
    terms = COURSE_FAQ_TOPIC_TERMS.get(intent)

    if not terms:
        return True

    haystack = " ".join([
        str(faq.get("question", "")),
        " ".join(str(k) for k in faq.get("keywords", []) or []),
        str(faq.get("category", "")),
    ]).lower()

    return any(term in haystack for term in terms)


# =========================================================
# FAQ → INTENT MAPPING
# =========================================================

FAQ_INTENTS = {

    "admission_process": "admission",
    "course_guidance": "recommendation",
    "documents_required": "documents_required",
    "eligibility": "course_eligibility",
    "age_limit": "course_eligibility",
    "admission_open": "admission",
    "join_anytime": "admission",
    "demo_class": "demo_class",
    "registration_process": "admission",

    "fees_information": "course_fees",
    "installment_payment": "installment_payment",
    "payment_methods": "course_fees",
    "discounts": "discounts",
    "refund_policy": "refund_policy",
    "fee_receipt": "course_fees",

    "batch_timings": "batch",
    "weekend_batches": "batch",
    "online_classes": "online_classes",
    "offline_classes": "course_info",
    "batch_change": "batch",
    "missed_class": "missed_class",

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
    "branch_locations": "branches",

    "parking_facility": "parking",
    "computer_lab": "academy_info",

    "attendance": "academy_info",
    "holiday_classes": "academy_info",
    "leave_policy": "academy_info",

    "language_of_instruction": "language_of_instruction",
    "beginner_friendly": "beginner_friendly",
    "working_professionals": "course_eligibility",
    "laptop_requirement": "equipment",
    "python_prior_programming_knowledge": "prerequisites",

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

        "prerequisites": {
            "python_prior_programming_knowledge": ["prior programming", "programming knowledge", "coding experience", "prior knowledge", "without programming", "without coding"],
        },
        "equipment": {
            "laptop_requirement": ["laptop", "own laptop", "bring laptop", "laptop required"],
        },
        "batch": {
            "batch_timings": ["batch", "batch timings", "flexible timings", "after 6 pm", "after 6", "class schedule"],
            "weekend_batches": ["weekend", "sunday", "saturday"],
        },
        "online_classes": {
            "online_classes": ["online", "online classes", "online batch", "virtual", "remote"],
        },
        "missed_class": {
            "missed_class": ["miss class", "missed class", "backup class", "backup classes", "makeup", "absence"],
        },
        "language_of_instruction": {
            "language_of_instruction": ["language", "gujarati", "hindi", "english", "teaching language"],
        },
        "parking": {
            "parking_facility": ["parking", "two wheeler", "bike parking", "parking space"],
        },
        "branches": {
            "branch_near_sanskar_mandal": ["sanskar mandal", "near sanskar mandal", "closest to sanskar mandal"],
        },

        "documents_required": {
            "documents_required": ["documents", "id proof", "photo", "bring for admission"],
        },
        "refund_policy": {
            "refund_policy": ["refund", "refundable", "money back", "cancel admission"],
        },
        "installment_payment": {
            "installment_payment": ["installment", "installments", "emi", "monthly installment", "pay monthly"],
        },
        "discounts": {
            "discounts": ["discount", "discounts", "two friends", "group discount", "offer"],
        },
        "practice_tests": {
            "ielts_mock_tests": ["mock test", "mock tests", "practice test", "practice tests"],
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

    query = _normalize(query)

    best_faq = None
    best_score = 0

    for faq in faqs:

        # Do not allow a fuzzy match from another topic to answer
        # a course-specific question.
        if not _faq_matches_topic(faq, intent):
            continue

        question = _normalize(
            faq.get("question", "")
        )

        answer = faq.get("answer", "")

        if not question:
            continue

        # ---------------------------------------------
        # Question similarity + FAQ keyword evidence
        # ---------------------------------------------

        score = _calculate_score(
            query,
            question
        )

        keyword_bonus = 0
        for keyword in faq.get("keywords", []) or []:
            keyword = _normalize(keyword)
            if not keyword:
                continue
            if re.search(r"\b" + re.escape(keyword) + r"\b", query):
                keyword_bonus = max(keyword_bonus, 35)
            else:
                # Allow high-confidence typo/wording variants without
                # letting a generic keyword dominate the whole question.
                candidate_score = _calculate_score(query, keyword)
                if candidate_score >= 92:
                    keyword_bonus = max(keyword_bonus, 22)

        # ---------------------------------------------
        # Intent-based bonus
        # ---------------------------------------------

        intent_bonus = 0

        question_lower = question

        if intent == "beginner_friendly":
            if "beginner" in question_lower:
                intent_bonus = 30

        elif intent == "course_certificate":
            if "certificate" in question_lower:
                intent_bonus = 30

        elif intent == "course_duration":
            if (
                "duration" in question_lower
                or "long" in question_lower
            ):
                intent_bonus = 30

        elif intent == "course_fees":
            if (
                "fee" in question_lower
                or "cost" in question_lower
                or "price" in question_lower
            ):
                intent_bonus = 30

        elif intent == "course_eligibility":
            if (
                "join" in question_lower
                or "eligible" in question_lower
                or "prerequisite" in question_lower
                or "beginner" in question_lower
            ):
                intent_bonus = 30

        # ---------------------------------------------
        # Final score
        # ---------------------------------------------

        final_score = score + intent_bonus + keyword_bonus

        if final_score > best_score:

            best_score = final_score
            best_faq = faq

    # ---------------------------------------------
    # Confidence
    # ---------------------------------------------

    if best_score < MIN_CONFIDENCE:
        return None, min(100, best_score)

    return best_faq, min(100, best_score)

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
