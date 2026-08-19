"""
chatbot.py

Production chatbot orchestration layer for Shital Academy.

This file does NOT implement NLP, validation, or email logic itself.
Every piece of actual logic lives in the logics/ package and is only
called from here, in a defined order:

    logics.course_listing    - detect_course_listing, format_course_listing
    logics.intent_detector   - detect_intent
    logics.course_detector   - detect_course
    logics.response_builder  - build_response, can_answer_from_course
    logics.faq_matcher       - search_course_faq, search_academy_faq
    logics.greeting_detector - greetings, goodbye
    logics.lead_capture      - validate_email, validate_mobile,
                                save_lead, send_transcript_to_academy

chatbot.py's own job is orchestration only:
- deciding WHICH logic runs, in WHAT order, for a given message
- holding per-session conversation state
- passing data between the individual logic modules
- shaping the final dictionary returned to the frontend/API
"""

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
    search_academy_faq,
)

from logics.greeting_detector import (
    greetings,
    goodbye,
)

from logics.lead_capture import (
    validate_email,
    validate_mobile,
    save_lead,
    send_transcript_to_academy,
)

from conversation import ConversationContext
from knowledge_loader import get_knowledge

from session_manager import (
    create_session,
    get_lead,
    get_conversation,
    update_activity,
)


# =========================================================
# CONFIGURATION
# =========================================================

# Academy requirement:
# Ask for lead details after this many REAL questions.
LEAD_CAPTURE_AFTER = 1


# =========================================================
# INTENT GROUPS
# =========================================================

COURSE_CONTEXT_INTENTS = {
    "course_info",
    "computer_course",
    "english_course",
    "course_fees",
    "course_duration",
    "course_eligibility",
    "course_certificate",
    "course_modules",
    "learning_outcomes",
    "beginner_friendly",
}


ACADEMY_INTENTS = {
    "admission",
    "placement",
    "demo_class",
    "academy_info",
    "contact",
    "branches",
    "academy_timings",
    "help",
}


# =========================================================
# CONVERSATION CONTEXT
# =========================================================

# One ConversationContext per session.
#
# This prevents course context from leaking between users.
_contexts = {}


def get_context(session_id):
    """
    Get or create conversation context for a session.
    """

    if session_id not in _contexts:
        _contexts[session_id] = ConversationContext()

    return _contexts[session_id]


def clear_context(session_id):
    """
    Remove conversation context when a session ends.
    """

    _contexts.pop(session_id, None)


# =========================================================
# SESSION HELPERS
# =========================================================

def save_message(session_id, sender, message):
    """
    Save a conversation message to the session transcript.
    """

    conversation = get_conversation(session_id)

    conversation.append(f"{sender}: {message}")


# =========================================================
# COURSE AVAILABILITY
# =========================================================

def is_course_offered(course_id, knowledge):
    """
    Check whether a course is officially offered by the academy
    even if detailed course JSON does not exist.
    """

    if not course_id:
        return False

    academy_data = knowledge.get("academy", {})

    if not isinstance(academy_data, dict):
        return False

    for data in academy_data.values():

        if not isinstance(data, dict):
            continue

        courses_offered = data.get("courses_offered", {})

        if not isinstance(courses_offered, dict):
            continue

        for course_list in courses_offered.values():

            if not isinstance(course_list, list):
                continue

            for offered_course in course_list:

                if not isinstance(offered_course, str):
                    continue

                offered_id = offered_course.lower().replace(" ", "_")

                if offered_id == course_id:
                    return True

    return False


# =========================================================
# COURSE CONTEXT
# =========================================================

def resolve_course_context(
    session_id,
    course_id,
    course_score,
    intent,
):
    """
    Resolve explicit course detection or previous course context.
    """

    context = get_context(session_id)

    course_from_context = False

    # -----------------------------------------------------
    # Explicit course mentioned
    # -----------------------------------------------------

    if course_id:

        context.set_course(course_id)

        return (
            course_id,
            course_score,
            course_from_context,
        )

    # -----------------------------------------------------
    # No explicit course.
    #
    # Fall back to previous course only when the intent is
    # course-specific.
    # -----------------------------------------------------

    if intent in COURSE_CONTEXT_INTENTS:

        previous_course = context.get_course()

        if previous_course:

            course_from_context = True
            course_id = previous_course
            course_score = 100.0

            return (
                course_id,
                course_score,
                course_from_context,
            )

    return (
        None,
        0.0,
        False,
    )


# =========================================================
# LEAD MANAGEMENT
# =========================================================

def should_trigger_lead_form(session_id):
    """
    Determine whether the frontend should display the lead form.
    """

    lead = get_lead(session_id)

    return (
        lead.get("question_count", 0) >= LEAD_CAPTURE_AFTER
        and not lead.get("captured", False)
    )


def submit_lead(session_id, name, email, mobile):
    """
    Save lead details and notify the academy.
    """

    result = save_lead(
        session_id,
        name,
        email,
        mobile,
    )

    if not result["success"]:
        return result

    send_transcript_to_academy(session_id)

    return {
        "success": True,
        "message": (
            f"Thank you, {name.strip()}. Let's continue."
        ),
    }

# =========================================================
# SESSION CLEANUP
# =========================================================

def cleanup_expired_sessions(exclude_session_id=None):
    """
    Find inactive sessions and send captured leads
    to the academy before removing the sessions.

    `exclude_session_id` should be the session about to handle
    the current request, so it never gets deleted out from
    under the message that's about to use it.
    """

    from session_manager import (
        get_expired_sessions,
        clear_session,
    )

    expired_sessions = get_expired_sessions(
        exclude_session_id=exclude_session_id
    )

    for session_id in expired_sessions:

        lead = get_lead(session_id)

        # -------------------------------------------------
        # Send captured lead if it has not been sent
        # -------------------------------------------------

        if (
            lead.get("captured")
            and not lead.get("email_sent")
        ):

            print(
                f"[session] Sending abandoned lead: "
                f"{session_id}"
            )

            send_transcript_to_academy(
                session_id
            )

        # -------------------------------------------------
        # Remove session
        # -------------------------------------------------

        clear_session(session_id)

        clear_context(session_id)

        print(
            f"[session] Expired: {session_id}"
        )
# =========================================================
# MAIN CHAT PROCESSOR
# =========================================================

def process_message(message, session_id=None):
    """
    Main production chatbot entry point.

    Returns a dictionary that can directly be used by a
    web frontend / FastAPI API layer.
    """

    # =====================================================
    # 0. VALIDATE MESSAGE
    # =====================================================

    if not isinstance(message, str):

        return {
            "response": "Please enter a valid message.",
            "session_id": session_id,
            "trigger_lead_form": False,
            "end_session": False,
        }

    message = message.strip()

    if not message:

        return {
            "response": "Please enter a message.",
            "session_id": session_id,
            "trigger_lead_form": False,
            "end_session": False,
        }

    # =====================================================
    # 1. CREATE SESSION IF NECESSARY
    # =====================================================

    if session_id is None:
        session_id = create_session()
    update_activity(session_id)
    # =====================================================
    # 2. SAVE USER MESSAGE
    # =====================================================

    save_message(
        session_id,
        "User",
        message,
    )

    normalized_message = message.lower()

    # =====================================================
    # 3. COURSE LISTING
    # =====================================================
    #
    # IMPORTANT:
    #
    # This MUST happen before goodbye/greeting/normal intent
    # detection.
    #
    # The general intent detector uses fuzzy matching and may
    # incorrectly classify:
    #
    #     "What course do you provide?"
    #
    # as "goodbye".
    #
    # Course listing is a higher-priority deterministic route.
    #
    # Therefore:
    #
    #     detect_course_listing()
    #
    # gets the first opportunity to handle the message.
    # =====================================================

    course_listing = detect_course_listing(message)

    if course_listing:

        response = format_course_listing(
            course_listing
        )

        save_message(
            session_id,
            "Bot",
            response,
        )

        return {
            "response": response,
            "session_id": session_id,

            "intent": "course_listing",
            "intent_score": 100.0,

            "course": None,
            "course_score": 0.0,

            "course_from_context": False,
            "course_can_answer": False,

            "course_faq": None,
            "course_faq_score": 0.0,

            "academy_faq": None,
            "academy_faq_score": 0.0,

            "course_offered": False,

            "trigger_lead_form": (
                should_trigger_lead_form(session_id)
            ),

            "end_session": False,
        }

    # =====================================================
    # 4. GOODBYE
    # =====================================================
    #
    # Goodbye is checked before greeting so "bye" cannot be
    # swallowed by a greeting fuzzy match.
    #
    # Course listing was intentionally checked first.
    # =====================================================

    if goodbye(normalized_message):

        response = (
            "Goodbye! Thank you for contacting "
            "Shital Academy."
        )

        save_message(
            session_id,
            "Bot",
            response,
        )

        # Send transcript if a lead was already captured.
        lead = get_lead(session_id)

        if lead.get("captured"):
            send_transcript_to_academy(session_id)

        clear_context(session_id)

        return {
            "response": response,
            "session_id": session_id,

            "intent": "goodbye",
            "intent_score": 100.0,

            "course": None,
            "course_score": 0.0,

            "course_from_context": False,
            "course_can_answer": False,

            "course_faq": None,
            "course_faq_score": 0.0,

            "academy_faq": None,
            "academy_faq_score": 0.0,

            "course_offered": False,

            "trigger_lead_form": False,

            "end_session": True,
        }

    # =====================================================
    # 5. GREETING
    # =====================================================

    if greetings(normalized_message):

        response = (
            "Hello! How can I help you today?"
        )

        save_message(
            session_id,
            "Bot",
            response,
        )

        return {
            "response": response,
            "session_id": session_id,

            "intent": "greeting",
            "intent_score": 100.0,

            "course": None,
            "course_score": 0.0,

            "course_from_context": False,
            "course_can_answer": False,

            "course_faq": None,
            "course_faq_score": 0.0,

            "academy_faq": None,
            "academy_faq_score": 0.0,

            "course_offered": False,

            # Greeting does NOT increase question_count.
            "trigger_lead_form": (
                should_trigger_lead_form(session_id)
            ),

            "end_session": False,
        }

    # =====================================================
    # 6. COUNT REAL QUESTION
    # =====================================================

    lead = get_lead(session_id)

    lead["question_count"] = (
        lead.get("question_count", 0) + 1
    )

    # =====================================================
    # 7. DETECT INTENT
    # =====================================================

    intent, intent_score = detect_intent(
        message
    )

    # =====================================================
    # 8. DETECT COURSE
    # =====================================================

    course_id, course_score = detect_course(
        message
    )

    # =====================================================
    # 9. RESOLVE COURSE CONTEXT
    # =====================================================

    (
        course_id,
        course_score,
        course_from_context,
    ) = resolve_course_context(
        session_id=session_id,
        course_id=course_id,
        course_score=course_score,
        intent=intent,
    )

    # =====================================================
    # 10. LOAD KNOWLEDGE
    # =====================================================

    knowledge = get_knowledge()

    course = None
    course_offered = False

    if course_id:

        course = (
            knowledge
            .get("courses", {})
            .get(course_id)
        )

        # Course may be officially offered even when detailed
        # course knowledge is unavailable.
        if not course:

            course_offered = is_course_offered(
                course_id,
                knowledge,
            )

    # =====================================================
    # 11. DETERMINE COURSE CONTEXT
    # =====================================================

    use_course_context = (
        bool(course_id)
        and intent in COURSE_CONTEXT_INTENTS
    )

    # =====================================================
    # 12. INITIALIZE FAQ RESULTS
    # =====================================================

    course_faq = None
    course_faq_score = 0.0

    academy_faq = None
    academy_faq_score = 0.0

    course_can_answer = False

    # =====================================================
    # 13. STRUCTURED COURSE DATA
    # =====================================================

    if use_course_context and course:

        course_can_answer = can_answer_from_course(
            course,
            intent,
        )

    # =====================================================
    # 14. COURSE FAQ
    # =====================================================

    if (
        use_course_context
        and course
        and not course_can_answer
    ):

        (
            course_faq,
            course_faq_score,
        ) = search_course_faq(
            course_id,
            message,
            intent,
        )

    # =====================================================
    # 15. ACADEMY FAQ
    # =====================================================

    if (
        not course_can_answer
        and not course_faq
    ):

        # Do not let an academy-level FAQ override a
        # course-specific academy question.
        if not (
            course_id
            and intent in ACADEMY_INTENTS
        ):

            (
                academy_faq,
                academy_faq_score,
            ) = search_academy_faq(
                message,
                intent,
            )

    # =====================================================
    # 16. BUILD FINAL RESPONSE
    # =====================================================

    response = build_response(
        intent=intent,
        course=course,
        course_id=course_id,
        course_faq=course_faq,
        academy_faq=academy_faq,
        knowledge=knowledge,
    )

    # =====================================================
    # 17. SAVE BOT RESPONSE
    # =====================================================

    save_message(
        session_id,
        "Bot",
        response,
    )

    # =====================================================
    # 18. RETURN API-FRIENDLY RESULT
    # =====================================================

    return {
        "response": response,
        "session_id": session_id,

        "intent": intent,
        "intent_score": intent_score,

        "course": course_id,
        "course_score": course_score,

        "course_from_context": course_from_context,
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

        "course_offered": course_offered,

        "trigger_lead_form": (
            should_trigger_lead_form(session_id)
        ),

        "end_session": False,
    }


# =========================================================
# CONSOLE LEAD CAPTURE
# =========================================================

def _console_capture_lead(session_id):
    """
    Blocking console prompt used only by run().

    A real frontend should call submit_lead() directly.
    """

    print(
        "\nBot: Before we continue, "
        "I'd like to know a few details."
    )

    # -----------------------------------------------------
    # Name
    # -----------------------------------------------------

    while True:

        name = input("Your Name : ").strip()

        if name:
            break

        print(
            "Bot: Name cannot be empty."
        )

    # -----------------------------------------------------
    # Email
    # -----------------------------------------------------

    while True:

        email = input("Your Email : ").strip()

        if validate_email(email):
            break

        print(
            "Bot: Please enter a valid email address."
        )

    # -----------------------------------------------------
    # Mobile
    # -----------------------------------------------------

    while True:

        mobile = input("Your Mobile : ").strip()

        if validate_mobile(mobile):
            break

        print(
            "Bot: Please enter a valid mobile number."
        )

    # -----------------------------------------------------
    # Submit
    # -----------------------------------------------------

    result = submit_lead(
        session_id,
        name,
        email,
        mobile,
    )

    print(
        f"\nBot: {result['message']}\n"
    )


# =========================================================
# CONSOLE MODE
# =========================================================

def run():
    """
    Simple console interface for local testing.

    A real deployment calls process_message() and
    submit_lead() directly.
    """

    session_id = create_session()

    print("=" * 60)
    print(
        "Bot: Namaste! Welcome to Shital Academy."
    )
    print(
        "Bot: I'm here to answer your questions."
    )
    print(
        "Bot: Type 'bye' anytime to exit."
    )
    print("=" * 60)

    try:

        while True:

            message = input(
                "\nYou : "
            ).strip()

            if not message:
                continue

            result = process_message(
                message,
                session_id,
            )

            print(
                f"\nBot: {result['response']}"
            )

            if result["trigger_lead_form"]:

                _console_capture_lead(
                    session_id
                )

            if result["end_session"]:
                break

    except KeyboardInterrupt:

        print(
            "\n\nBot: Chat ended."
        )

    finally:

        lead = get_lead(session_id)

        if lead.get("captured"):
            send_transcript_to_academy(
                session_id
            )

        clear_context(session_id)


# =========================================================
# PROGRAM START
# =========================================================

if __name__ == "__main__":
    run()