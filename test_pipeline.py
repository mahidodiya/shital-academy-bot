from logics.intent_detector import detect_intent
from logics.course_detector import detect_course
from logics.response_builder import build_response
from logics.faq_matcher import (
    search_course_faq,
    search_academy_faq
)
# =========================================================
# End-to-End Pipeline Test
# =========================================================

TEST_MESSAGES = [

    "Who can join?",
    "How can I take admission?",
    "What are the fees?",
    "Can I pay fees in installments?",
    "Do you provide demo classes?",
    "Is placement available?",
    "What is the duration?",
    "Do you provide certificate?",
    "What are the fees for Python?",
    "What is the duration of Python?",
    "Does Python provide a certificate?",
    "Is Python suitable for beginners?"
]


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
    # 3. Load knowledge
    # -----------------------------------------------------

    from knowledge_loader import get_knowledge

    knowledge = get_knowledge()

    course = None

    if course_id:
        course = knowledge["courses"].get(course_id)

    # -----------------------------------------------------
    # 4. FAQ search
    # -----------------------------------------------------
    course_faq = None
    course_faq_score = 0

    academy_faq = None
    academy_faq_score = 0 
    # -----------------------------------------------------
    # Course FAQ
    # -----------------------------------------------------

    if course_id:

        course_faq, course_faq_score = search_course_faq(
            course_id,
            message,
            intent
        )

    # -----------------------------------------------------
    # Academy FAQ
    # -----------------------------------------------------

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
        course_faq=course_faq,
        academy_faq=academy_faq,
        knowledge=knowledge
    )

    return {
        "intent": intent,
        "intent_score": intent_score,

        "course": course_id,
        "course_score": course_score,

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
        f"COURSE FAQ : "
        f"{result['course_faq']} "
        f"({result['course_faq_score']:.2f})"
    )

    print(
        f"ACADEMY FAQ: "
        f"{result['academy_faq']} "
        f"({result['academy_faq_score']:.2f})"
    )
    print("\nBOT:")
    print(result["response"])