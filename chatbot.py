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

import re

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
from logics.query_analyzer import analyze_topics, comparison_courses

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
LEAD_CAPTURE_AFTER = 3


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
    "prerequisites",
    "course_certificate",
    "certificate_recognition",
    "course_modules",
    "learning_outcomes",
    "beginner_friendly",
    "study_material",
    "practice_tests",
}


ACADEMY_INTENTS = {
    "admission",
    "placement",
    "demo_class",
    "academy_info",
    "contact",
    "online_classes",
    "batch",
    "refund_policy",
    "installment_payment",
    "discounts",
    "documents_required",
    "missed_class",
    "language_of_instruction",
    "parking",
    "equipment",
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

                offered_normalized = offered_course.strip().lower()

                # Map the public academy catalog name to the internal
                # course id. This keeps courses such as C++/Customized
                # English consistent with course_detector.py.
                catalog_ids = {
                    "c": "c",
                    "c++": "cpp",
                    "java": "java",
                    "html": "html",
                    "bootstrap": "bootstrap",
                    "customized english courses": "customized_english",
                    "basic to advanced english course": "basic_to_advanced_english",
                    "special speaking course for english medium students": "special_speaking_english",
                    "foundation course": "foundation_english",
                    "foundation english course": "foundation_english",
                    "rapido english course": "rapido_english",
                    "spoken english": "spoken_english",
                    "ielts preparation": "ielts",
                    "web designing": "web_designing",
                    "web development": "web_development",
                    "python programming": "python",
                    "tally prime with gst": "tally",
                    "data analytics": "data_analytics",
                    "advanced excel": "excel",
                    "advanced ccc": "ccc",
                    "office executive": "office_executive",
                }

                offered_id = catalog_ids.get(
                    offered_normalized,
                    offered_normalized.replace(" ", "_")
                )

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
    # 6. THANKS / GRATITUDE
    # =====================================================

    if normalized_message in {
        "thanks",
        "thank you",
        "thankyou",
        "thx",
        "ty",
        "thanks a lot",
        "thank you so much",
    }:

        response = "You're welcome! 😊 Let me know if you need anything else."

        save_message(session_id, "Bot", response)

        return {
            "response": response,
            "session_id": session_id,
            "intent": "thanks",
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
            "end_session": False,
        }

    # =====================================================
    # 7. DETECT INTENT
    # =====================================================

    intent, intent_score = detect_intent(message)

    # =====================================================
    # 8. DETECT COURSE
    # =====================================================

    course_id, course_score = detect_course(message)


    # =====================================================
    # 9. QUERY ANALYSIS: MULTI-TOPIC + COMPARISON
    # =====================================================
    topics = analyze_topics(message)

    # A course-specific eligibility question such as
    # "Can a senior citizen join CCC?" also contains the word "join".
    # Do not let the generic admission FAQ contaminate the answer.
    if "course_eligibility" in topics and "admission" in topics:
        topics.remove("admission")
    if "certificate_recognition" in topics and "course_certificate" in topics:
        topics.remove("course_certificate")
    if "course_modules" in topics and "language_of_instruction" in topics:
        topics.remove("language_of_instruction")

    comparison_ids = comparison_courses(message, detect_course)

    # A comparison must name at least two recognizable courses.
    comparison_language = bool(re.search(r"\b(vs|versus|or|between)\b", normalized_message))
    if len(comparison_ids) >= 2 and (
        intent in {"comparison", "recommendation"}
        or "confused" in normalized_message
        or comparison_language
    ):
        knowledge = get_knowledge()
        names = []
        for cid in comparison_ids:
            course_data = knowledge.get("courses", {}).get(cid, {})
            names.append(course_data.get("name", cid.replace("_", " ").title()))
        details = []
        for cid in comparison_ids:
            course_data = knowledge.get("courses", {}).get(cid, {})
            desc = course_data.get("description")
            if desc:
                details.append(
                    f"{course_data.get('name', cid.replace('_',' ').title())}: {desc}"
                )
        response = (
            f"You are comparing {' and '.join(names)}.\n\n"
            + "\n\n".join(details)
            + "\n\nIf you tell me your main goal, I can help you choose between them."
        )
        save_message(session_id, "Bot", response)
        lead = get_lead(session_id)
        lead["question_count"] = lead.get("question_count", 0) + 1
        return {
            "response": response, "session_id": session_id,
            "intent": "comparison", "intent_score": 100.0,
            "course": comparison_ids[0], "course_score": 100.0,
            "course_from_context": False, "course_can_answer": False,
            "course_faq": None, "course_faq_score": 0.0,
            "academy_faq": None, "academy_faq_score": 0.0,
            "course_offered": True,
            "trigger_lead_form": should_trigger_lead_form(session_id),
            "end_session": False,
        }

    # A single explicit course plus a career goal is a recommendation/career-fit
    # question, not a placement request. Use the course's verified career data.
    if course_id and intent == "recommendation" and len(comparison_ids) < 2:
        knowledge = get_knowledge()
        course_data = knowledge.get("courses", {}).get(course_id)
        if course_data:
            name = course_data.get("name", course_id.replace("_", " ").title())
            desc = course_data.get("description", "")
            careers = course_data.get("career_opportunities", [])
            response = f"{name}\n\n{desc}" if desc else name
            if careers:
                response += "\n\nCareer opportunities listed for this course:\n" + "\n".join(f"• {x}" for x in careers)
            response += "\n\nIf you tell me your exact job goal, I can help you compare this with another suitable course."
            save_message(session_id, "Bot", response)
            lead = get_lead(session_id)
            lead["question_count"] = lead.get("question_count", 0) + 1
            return {
                "response": response, "session_id": session_id,
                "intent": "recommendation", "intent_score": 100.0,
                "course": course_id, "course_score": course_score,
                "course_from_context": False, "course_can_answer": False,
                "course_faq": None, "course_faq_score": 0.0,
                "academy_faq": None, "academy_faq_score": 0.0,
                "course_offered": True,
                "trigger_lead_form": should_trigger_lead_form(session_id),
                "end_session": False,
            }

    # Multiple specific topics in one message are answered separately.
    if len(topics) >= 2:
        knowledge = get_knowledge()
        resolved_course_id = course_id or get_context(session_id).get_course()
        resolved_course = knowledge.get("courses", {}).get(resolved_course_id) if resolved_course_id else None
        responses = []

        for topic in topics:
            if topic == "course_start_date":
                answer = (
                    "I don't have a confirmed starting date for this course yet. "
                    "Please contact Shital Academy for the next available batch date."
                )
            elif topic in {
                "academy_timings", "batch", "branches", "online_classes",
                "installment_payment", "discounts", "documents_required",
                "missed_class", "language_of_instruction", "parking",
                "equipment", "refund_policy", "demo_class", "placement",
                "admission",
            }:
                if topic == "online_classes" and "offline" in normalized_message:
                    if "online" in normalized_message:
                        answer = (
                            "Shital Academy offers offline classroom training. "
                            "Online batch availability should be confirmed for your preferred course and schedule. "
                            "Please contact the academy for the current online-batch availability."
                        )
                    else:
                        answer = (
                            "Yes. Shital Academy offers offline classroom training. "
                            "For the specific course and batch schedule, please contact the academy."
                        )
                elif topic == "demo_class" and any(x in normalized_message for x in ("free", "without paying", "before paying")):
                    answer = (
                        "Yes, demo classes are available for selected courses so students can understand the teaching method, "
                        "course content, and learning environment before taking admission. The current information does not "
                        "confirm that every demo class is free, so please contact the academy for the selected course."
                    )
                else:
                    faq, _ = search_academy_faq(message, topic)
                    answer = build_response(
                        intent=topic,
                        course=resolved_course,
                        course_id=resolved_course_id,
                        academy_faq=faq,
                        knowledge=knowledge,
                    )
            else:
                faq, _ = (
                    search_course_faq(resolved_course_id, message, topic)
                    if resolved_course_id else (None, 0.0)
                )
                answer = build_response(
                    intent=topic,
                    course=resolved_course,
                    course_id=resolved_course_id,
                    course_faq=faq,
                    knowledge=knowledge,
                )

            if answer and answer not in responses:
                responses.append(answer)

        if responses:
            response = "\n\n".join(responses)
            save_message(session_id, "Bot", response)
            lead = get_lead(session_id)
            lead["question_count"] = lead.get("question_count", 0) + 1
            return {
                "response": response, "session_id": session_id,
                "intent": topics[0], "intent_score": 100.0,
                "course": resolved_course_id,
                "course_score": 100.0 if resolved_course_id else 0.0,
                "course_from_context": bool(resolved_course_id and not course_id),
                "course_can_answer": False,
                "course_faq": None, "course_faq_score": 0.0,
                "academy_faq": None, "academy_faq_score": 0.0,
                "course_offered": bool(resolved_course_id),
                "trigger_lead_form": should_trigger_lead_form(session_id),
                "end_session": False,
            }

    # Use a specific topic when the generic intent detector chose a broad
    # course category such as "computer_course" or "english_course".
    if topics:
        priority = [
            "course_fees", "course_duration", "course_start_date", "certificate_recognition", "course_modules",
            "study_material", "course_certificate", "practice_tests",
            "prerequisites", "course_eligibility", "placement",
            "demo_class", "installment_payment", "documents_required",
            "refund_policy", "online_classes", "batch", "academy_timings",
            "branches", "language_of_instruction", "parking", "equipment",
            "missed_class", "discounts", "recommendation", "admission",
        ]
        for topic in priority:
            if topic in topics:
                intent = topic
                intent_score = 100.0
                break

    # =====================================================
    # 9. OUT-OF-SCOPE / UNKNOWN
    # =====================================================
    # Never search the academy FAQ when we do not have a reliable
    # intent. This is the key production guard against unrelated
    # questions receiving random academy answers.

    if intent is None:

        response = (
            "I can help with Shital Academy's courses, fees, "
            "admissions, timings, batches, branches, and other "
            "academy-related questions. What would you like to know?"
        )

        save_message(session_id, "Bot", response)

        return {
            "response": response,
            "session_id": session_id,
            "intent": None,
            "intent_score": intent_score,
            "course": course_id,
            "course_score": course_score,
            "course_from_context": False,
            "course_can_answer": False,
            "course_faq": None,
            "course_faq_score": 0.0,
            "academy_faq": None,
            "academy_faq_score": 0.0,
            "course_offered": bool(course_id),
            "trigger_lead_form": False,
            "end_session": False,
        }

    # =====================================================
    # 10. COUNT REAL QUESTION
    # =====================================================

    lead = get_lead(session_id)

    lead["question_count"] = (
        lead.get("question_count", 0) + 1
    )

    # =====================================================
    # 11. RESOLVE COURSE CONTEXT
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
    # 12. LOAD KNOWLEDGE
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
            and intent in COURSE_CONTEXT_INTENTS
        ):

            (
                academy_faq,
                academy_faq_score,
            ) = search_academy_faq(
                message,
                intent,
            )

    # Offline questions are distinct from online-batch availability.
    if intent == "online_classes" and "offline" in normalized_message:
        if "online" in normalized_message:
            response = (
                "Shital Academy offers offline classroom training. "
                "Online batch availability should be confirmed for your preferred course and schedule. "
                "Please contact the academy for the current online-batch availability."
            )
        else:
            response = (
                "Yes. Shital Academy offers offline classroom training. "
                "For the specific course and batch schedule, please contact the academy."
            )
    elif intent == "demo_class" and any(x in normalized_message for x in ("free", "without paying", "before paying")):
        response = (
            "Yes, demo classes are available for selected courses so students can understand the teaching method, "
            "course content, and learning environment before taking admission. The current information does not "
            "confirm that every demo class is free, so please contact the academy for the selected course."
        )
    else:
        response = None

    # =====================================================
    # 16. BUILD FINAL RESPONSE
    # =====================================================

    if response is None:
        response = build_response(
            intent=intent,
            course=course,
            course_id=course_id,
            course_faq=course_faq,
            academy_faq=academy_faq,
            knowledge=knowledge,
        )

    # Never imply guaranteed placement when the academy only confirms
    # placement support and says assistance may vary by course.
    if intent == "placement" and any(
        word in normalized_message
        for word in ("guaranteed", "guarantee", "100% job", "sure job")
    ):
        response = (
            "Placement support is available for the Diploma in Office Executive "
            "course and IT courses. The academy does not state that placement is "
            "guaranteed; the level of assistance may vary depending on the course."
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