from logics.course_listing import (
    detect_course_listing,
    format_course_listing,
)
from logics.intent_detector import detect_intent
from logics.course_detector import detect_course
from logics.response_builder import (
    build_response,
    can_answer_from_course,
)
from logics.faq_matcher import (
    search_course_faq,
    search_academy_faq
)
from conversation import ConversationContext
context = ConversationContext()
# =========================================================
# End-to-End Pipeline Test
# =========================================================

TEST_MESSAGES = [
    "What are the batch timings?",
    "What are your timings?",
    ]
# =========================================================
# Conversation Routing Rules
# =========================================================

COURSE_CONTEXT_INTENTS = {
    "course_info",
    "course_fees",
    "course_duration",
    "course_eligibility",
    "course_certificate",
    "course_modules",
    "learning_outcomes",
    "beginner_friendly"
}

ACADEMY_INTENTS = {
    "admission",
    "placement",
    "demo_class",
    "academy_info",
    "contact",
    "timings",
    "help",
    "academy_timings",
}
# =========================================================
# Pipeline
# =========================================================
def process_message(message):

    # -----------------------------------------------------
    # 1. Detect intent
    # -----------------------------------------------------

    intent, intent_score = detect_intent(message)

    # -----------------------------------------------------
    # 2. Detect course
    # -----------------------------------------------------

    course_id, course_score = detect_course(message)
    
    # -----------------------------------------------------
    # 2A. Check if user is asking for course listing
    # -----------------------------------------------------

    course_listing = detect_course_listing(message)

    if course_listing:

        response = format_course_listing(course_listing)

        return {
            "intent": "course_listing",
            "intent_score": 100.0,

            "course": None,
            "course_score": 0.0,

            "course_can_answer": False,

            "course_faq": None,
            "course_faq_score": 0.0,

            "academy_faq": None,
            "academy_faq_score": 0.0,

            "course_from_context": False,

            "response": response
        }
    #------------------------------------------------------
    # Use conversation context when no course is detected
    #------------------------------------------------------
    course_from_context = False
    
    if course_id:
        # Course explicitly mentioned in current message
        context.set_course(course_id)

    else:

        # Use previous course context ONLY for course-specific intents
        if intent in COURSE_CONTEXT_INTENTS:
            course_id = context.get_course()

            if course_id:
                course_from_context = True
                course_score = 100.0
        else:
            course_id = None
    # -----------------------------------------------------
    # Determine course context
    # -----------------------------------------------------

    use_course_context = False

    if course_id and intent in COURSE_CONTEXT_INTENTS:
        use_course_context = True
    # -----------------------------------------------------
    # 3. Load knowledge
    # -----------------------------------------------------

    from knowledge_loader import get_knowledge

    knowledge = get_knowledge()

    course = None
    course_offered = False

    if course_id:

        # Detailed course data exists
        course = knowledge["courses"].get(course_id)

        # Course may be officially offered even without
        # detailed knowledge-base data
        if not course:
            for data in knowledge.get("academy", {}).values():

                if not isinstance(data, dict):
                    continue

                courses_offered = data.get(
                    "courses_offered",
                    {}
                )

                if not isinstance(courses_offered, dict):
                    continue

                for course_list in courses_offered.values():

                    if not isinstance(course_list, list):
                        continue

                    for offered_course in course_list:

                        offered_id = offered_course.lower().replace(
                            " ",
                            "_"
                        )

                        if offered_id == course_id:
                            course_offered = True
                            break

                    if course_offered:
                        break

                if course_offered:
                    break
    # -----------------------------------------------------
    # 4.FAQ SEARCH
    # -----------------------------------------------------

    course_faq = None
    course_faq_score = 0

    academy_faq = None
    academy_faq_score = 0

    # -----------------------------------------------------
    # Check structured course data first
    # -----------------------------------------------------

    course_can_answer = False

    if use_course_context and course:
        course_can_answer = can_answer_from_course(
            course,
            intent
        )

    # -----------------------------------------------------
    # Course FAQ fallback
    # -----------------------------------------------------

    if use_course_context and course and not course_can_answer:

        course_faq, course_faq_score = search_course_faq(
            course_id,
            message,
            intent
        )
    # -----------------------------------------------------
    # Academy FAQ fallback
    # -----------------------------------------------------

    if not course_can_answer and not course_faq:

        # Do not use Academy FAQ when a specific course
        # is mentioned with an academy-level question.
        if not (
            course_id
            and intent in ACADEMY_INTENTS
        ):

            academy_faq, academy_faq_score = search_academy_faq(
                message,
                intent
            )
            
    # -----------------------------------------------------
    # 5. Build response
    # -----------------------------------------------------

    response = build_response(
    intent=intent,
    course=course,
    course_id=course_id,
    course_faq=course_faq,
    academy_faq=academy_faq,
    knowledge=knowledge
)
        
    return {
        "intent": intent,
        "intent_score": intent_score,

        "course": course_id,
        "course_score": course_score,

        "course_can_answer": course_can_answer,

        "course_faq": (
            course_faq.get("id")
            if course_faq
            else None
        ),

        "course_faq_score": course_faq_score,

        "academy_faq": (
            academy_faq.get("id")
            if academy_faq
            else None
        ),

        "academy_faq_score": academy_faq_score,
        
        "course_from_context": course_from_context,

        "response": response
    }
# =========================================================
# Run Tests
# =========================================================

print("\n" + "=" * 80)
print("END-TO-END PIPELINE TEST")
print("=" * 80)


for message in TEST_MESSAGES:

    result = process_message(message)

    print("\n" + "-" * 80)
    print(f"USER: {message}")

    print(f"INTENT : {result['intent']} ({result['intent_score']:.2f})")
    print(f"COURSE : {result['course']} ({result['course_score']:.2f})")
    print(
    f"STRUCTURED : "
    f"{result['course_can_answer']}"
    )
    print(
        f"COURSE FAQ : "
        f"{result['course_faq']} "
        f"({result['course_faq_score']:.2f})"
    )
    
    print(
        f"FROM CONTEXT : "
        f"{result['course_from_context']}"
    )

    print(
        f"ACADEMY FAQ: "
        f"{result['academy_faq']} "
        f"({result['academy_faq_score']:.2f})"
    )
    print("\nBOT:")
    print(result["response"])