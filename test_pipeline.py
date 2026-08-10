from logics.intent_detector import detect_intent
from logics.course_detector import detect_course
from logics.faq_matcher import search_faq
from logics.response_builder import build_response


# =========================================================
# End-to-End Pipeline Test
# =========================================================

TEST_MESSAGES = [

    "Tell me about Python",
    "What are the fees for Python?",
    "What is the duration of Python?",
    "Who can join Python?",
    "Does Python course provide a certificate?",
    "What will I learn in Python?",

    "Tell me about Advanced Excel",
    "What are the fees for Advanced Excel?",

    "What will I learn in IELTS?",
    "Who can join IELTS?",

    "I want to learn web development",
    "Is web development suitable for beginners?"
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

    faq = None
    faq_score = 0

    # Only search FAQ when the intent is actually
    # something that should be answered by an FAQ.

    FAQ_INTENTS = {
            "admission",
            "placement",
            "recommendation",
            "course_info",
            "academy_info",
            "contact",
            "help",
            "demo_class",
    }
    
    # -----------------------------------------------------
    # Search academy FAQ only when course data should NOT
    # be the primary source.
    # -----------------------------------------------------

    if intent in FAQ_INTENTS:

        faq, faq_score = search_faq(
            message,
            course_id,
            intent
        )

    # -----------------------------------------------------
    # 5. Build response
    # -----------------------------------------------------

    response = build_response(
        intent=intent,
        course=course,
        faq=faq,
        knowledge=knowledge
    )

    return {
        "intent": intent,
        "intent_score": intent_score,
        "course": course_id,
        "course_score": course_score,
        "faq": faq.get("id") if faq else None,
        "faq_score": faq_score,
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
    print(f"FAQ    : {result['faq']} ({result['faq_score']:.2f})")

    print("\nBOT:")
    print(result["response"])