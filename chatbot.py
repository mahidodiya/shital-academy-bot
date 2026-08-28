import re
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
# Ask for lead details after the first REAL question.
# Greetings / thanks / goodbye do not count as questions.
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
    "prerequisites",
    "course_certificate",
    "course_modules",
    "learning_outcomes",
    "beginner_friendly",
    "study_material",
    "practice_tests",
    "certificate_recognition",
    "placement_guarantee",
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
    "certificate_recognition",
    "placement_guarantee",
    "payment_methods",
    "fee_receipt",
    "internship",
    "leave_policy",
    "teaching_methodology",
    "why_choose",
    "admission_open",
    "join_anytime",
    "batch_change",
    "practical_training",
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
# CONVERSATIONAL HELPERS
# =========================================================

def _set_pending(session_id, kind, **data):
    """Store a small, explicit follow-up state for the next user turn."""
    get_context(session_id).set_pending({"kind": kind, **data})


def _clear_pending(session_id):
    get_context(session_id).clear_pending()


def _scenario_for_comparison(message):
    """Extract the student's decision scenario from a comparison query."""
    text = (message or "").lower()
    scenarios = [
        ("data_analyst", ("data analyst", "data analysis", "data analytics")),
        ("mis", ("mis job", "mis role", "mis executive", "reporting job", "reporting", "data manage", "data management")),
        ("accounting", ("accounting", "accountant", "accounts job", "accounts")),
        ("back_office", ("back office", "office job", "office work", "administrative")),
        ("programming", ("programming", "developer", "software development", "coding")),
        ("speaking", ("speaking", "speak", "conversation", "confidence")),
        ("grammar", ("grammar", "grammatical")),
        ("weak_english", ("weak in english", "weak english", "basic english", "english foundation", "beginner in english")),
        ("basic_computer", ("basic computer", "computer basics", "learn computers")),
        ("job", ("job", "career", "employment")),
    ]
    for scenario, phrases in scenarios:
        if any(phrase in text for phrase in phrases):
            return scenario
    return None


def _scenario_from_goal(text):
    """Map a student's plain-language goal to a verified course scenario."""
    t = (text or "").lower()
    if any(x in t for x in ("mis", "reporting", "data manage", "data management")):
        return "mis"
    if any(x in t for x in ("data analyst", "data analysis", "analytics")):
        return "data_analyst"
    if any(x in t for x in ("back office", "office job", "office work")):
        return "back_office"
    if any(x in t for x in ("programming", "programing", "program", "coding", "coder", "developer")):
        return "programming"
    if any(x in t for x in ("accounting", "accountant", "accounts job")):
        return "accounting"
    if any(x in t for x in ("grammar", "grammatical")):
        return "grammar"
    if any(x in t for x in ("speaking", "speaking confidence", "conversation", "speking")):
        return "speaking"
    if any(x in t for x in ("weak in english", "basic english", "beginner in english")):
        return "weak_english"
    return None


def _single_course_recommendation(course_id, message, knowledge):
    """Give a useful answer when a recommendation names one course."""
    course = knowledge.get("courses", {}).get(course_id, {})
    name = course.get("name", course_id.replace("_", " ").title())
    scenario = _scenario_from_goal(message)
    if scenario == "mis" and course_id in {"excel", "data_analytics"}:
        return f"Yes. {name} is a suitable choice for an MIS/data-management goal because it covers data handling, reporting, analysis and visualization relevant to MIS work."
    if scenario == "back_office" and course_id in {"office_executive", "ccc", "excel"}:
        return f"Yes. {name} is suitable for back-office work based on its office, computer and productivity skills."
    if scenario == "programming" and course_id == "python":
        return "Yes. Python Programming is a suitable choice if your goal is to learn programming and move toward software development."
    if scenario == "data_analyst" and course_id == "data_analytics":
        return "Yes. Data Analytics is the more directly aligned course for a data analyst goal."
    if scenario == "grammar" and course_id == "foundation_english":
        return "Yes. Foundation English is a suitable choice for improving grammar and core English skills."
    if scenario == "speaking" and course_id in {"rapido_english", "spoken_english"}:
        return f"Yes. {name} is suitable for improving speaking confidence through practical English communication."
    return None


def _comparison_guidance(comparison_ids, message, knowledge):
    """Return a concise, scenario-specific comparison instead of dumping both courses."""
    scenario = _scenario_for_comparison(message)
    names = {
        cid: knowledge.get("courses", {}).get(cid, {}).get("name", cid.replace("_", " ").title())
        for cid in comparison_ids
    }

    # Explicit, verified course-to-scenario recommendations based only on
    # the career/module information already present in the project KB.
    preferred = None
    reason = None
    if scenario == "mis" and "excel" in comparison_ids:
        preferred = "excel"
        reason = "Advanced Excel directly covers formulas, data analysis, Pivot Tables, charts, and dashboard basics used in MIS/reporting work."
    elif scenario == "accounting" and "tally" in comparison_ids:
        preferred = "tally"
        reason = "Tally Prime with GST is focused on accounting, ledgers, vouchers, GST, TDS, payroll, billing, and related accounts work."
    elif scenario == "back_office" and "office_executive" in comparison_ids:
        preferred = "office_executive"
        reason = "Office Executive is designed for office-based careers and covers Advanced CCC, Microsoft Office, Advanced Excel, Tally Prime, communication, and office administration."
    elif scenario == "programming" and "python" in comparison_ids:
        preferred = "python"
        reason = "Python is focused on programming, logical thinking, problem-solving, and software development."
    elif scenario == "data_analyst" and "data_analytics" in comparison_ids:
        preferred = "data_analytics"
        reason = "Data Analytics is specifically focused on data handling, reporting, visualization, and data-driven decision making."
    elif scenario == "weak_english" and "foundation_english" in comparison_ids:
        preferred = "foundation_english"
        reason = "Foundation English is the better starting point for building grammar, vocabulary, pronunciation, reading, writing, listening, and basic speaking confidence."
    elif scenario == "grammar" and "foundation_english" in comparison_ids:
        preferred = "foundation_english"
        reason = "Foundation English places stronger emphasis on grammar and core language skills."
    elif scenario == "speaking":
        if "rapido_english" in comparison_ids and "foundation_english" in comparison_ids:
            preferred = "rapido_english"
            reason = "Rapido English focuses more directly on speaking ability, conversation practice, pronunciation, vocabulary, and confidence."
        elif "spoken_english" in comparison_ids and "rapido_english" in comparison_ids:
            reason = "Both focus on speaking. Rapido emphasizes interactive speaking, conversation, pronunciation, vocabulary, and confidence; Spoken English also includes grammar, group discussions, presentations, and real-life communication."
    elif scenario == "basic_computer" and "ccc" in comparison_ids:
        preferred = "ccc"
        reason = "Advanced CCC is the more direct choice for computer fundamentals, Microsoft Office, typing, internet skills, and basic productivity tools."

    if preferred and preferred in names:
        others = [names[cid] for cid in comparison_ids if cid != preferred]
        other_text = ", ".join(others)
        scenario_labels = {
            "mis": "an MIS job", "accounting": "an accounting job",
            "back_office": "a back office job", "programming": "programming",
            "data_analyst": "a data analyst job", "weak_english": "building a strong English foundation",
            "grammar": "improving grammar", "speaking": "improving speaking",
            "basic_computer": "basic computer skills",
        }
        goal_text = scenario_labels.get(scenario, "this goal")
        return (
            f"You are comparing {' and '.join(names[cid] for cid in comparison_ids)} for {goal_text}.\n\n"
            f"For this goal, **{names[preferred]}** would be the more suitable choice.\n\n"
            f"{reason}\n\n"
            f"For this specific scenario, {names[preferred]} is the better fit than {other_text}."
        )

    # If there is no scenario, give a useful short comparison rather than
    # reproducing the entire course descriptions and career lists.
    lines = [f"You are comparing {' and '.join(names[cid] for cid in comparison_ids)}."]
    for cid in comparison_ids:
        course = knowledge.get("courses", {}).get(cid, {})
        desc = course.get("description") or ""
        first_sentence = desc.split(". ")[0].strip()
        if first_sentence:
            lines.append(f"• {names[cid]}: {first_sentence}.")
    lines.append("\nTell me your goal (for example MIS, accounting, back office, programming, or speaking), and I can recommend the better option.")
    return "\n\n".join(lines)


def _handle_pending_followup(message, session_id):
    """Handle short answers to the bot's previous clarification question."""
    context = get_context(session_id)
    pending = context.get_pending()
    if not pending:
        return None

    text = (message or "").strip()
    normalized = text.lower()

    # A plain-language goal should resolve a pending comparison before the
    # course detector gets a chance to interpret words such as "data".
    if pending.get("kind") == "comparison_goal":
        scenario = _scenario_from_goal(text)
        if scenario:
            comparison_ids = pending.get("courses", [])
            guided = _comparison_guidance(comparison_ids, text, get_knowledge())
            context.clear_pending()
            return {"kind": "replay", "message": guided}

    # A plain-language career goal should resolve a pending course-guidance
    # prompt before course-name detection. This prevents words such as
    # "programming" from being treated as a course name when the user is
    # answering the goal question.
    if pending.get("kind") == "course_guidance":
        scenario = _scenario_from_goal(text)
        if scenario:
            course_map = {
                "mis": "excel", "data_analyst": "data_analytics",
                "back_office": "office_executive", "programming": "python",
                "accounting": "tally", "grammar": "foundation_english",
                "speaking": "rapido_english", "weak_english": "foundation_english",
            }
            cid = course_map.get(scenario)
            if cid:
                course = get_knowledge().get("courses", {}).get(cid, {})
                name = course.get("name", cid.replace("_", " ").title())
                context.set_course(cid)
                context.clear_pending()
                reasons = {
                    "mis": "Advanced Excel is directly useful for MIS work because it covers data management, analysis, reporting and dashboards.",
                    "data_analyst": "Data Analytics is directly aligned with data analyst work involving data handling, reporting and visualization.",
                    "back_office": "Office Executive is designed for office-based careers and covers office productivity and administration skills.",
                    "programming": "Python Programming builds programming and problem-solving skills for software development.",
                    "accounting": "Tally Prime with GST is focused on accounting and related business operations.",
                    "grammar": "Foundation English focuses on grammar and core English language skills.",
                    "speaking": "Rapido English focuses directly on speaking, conversation, pronunciation and confidence.",
                    "weak_english": "Foundation English is the better starting point for building essential English skills.",
                }
                return {"kind": "replay", "message": f"Based on your goal, **{name}** would be a suitable choice. {reasons[scenario]}"}

    # An explicit course name always resolves a pending course-specific prompt.
    cid, score = detect_course(text)
    if cid and score >= 85:
        kind = pending.get("kind")
        context.set_course(cid)
        context.clear_pending()
        if kind == "admission_course":
            return {"kind": "replay", "message": f"Great. You're interested in {get_knowledge().get('courses', {}).get(cid, {}).get('name', cid.replace('_',' ').title())}. You can visit any Shital Academy branch or contact the academy to complete the admission process."}
        if kind == "demo_course":
            return {"kind": "replay", "message": f"Sure. Demo classes are available for selected courses. Please contact Shital Academy to confirm a demo for {get_knowledge().get('courses', {}).get(cid, {}).get('name', cid.replace('_',' ').title())}."}
        if kind == "fees_course":
            return {"kind": "replay", "message": build_response(intent="course_fees", course=get_knowledge().get('courses', {}).get(cid), course_id=cid, knowledge=get_knowledge())}
        if kind == "duration_course":
            return {"kind": "replay", "message": build_response(intent="course_duration", course=get_knowledge().get('courses', {}).get(cid), course_id=cid, knowledge=get_knowledge())}
        return None

    if normalized in {"yes", "yeah", "yep", "sure", "ok", "okay"}:
        kind = pending.get("kind")
        if kind in {"admission_course", "demo_course", "fees_course", "duration_course"}:
            return {"kind": "replay", "message": "Sure — please tell me which course you are asking about."}
        if kind == "course_guidance":
            return {"kind": "replay", "message": "Sure — please tell me your education level and your career goal (for example: MIS, accounting, back office, programming, data analytics, or English speaking)."}
        if kind == "comparison_goal":
            original = pending.get("comparison_message", "")
            if _scenario_from_goal(original):
                guided = _comparison_guidance(pending.get("courses", []), original, get_knowledge())
                return {"kind": "replay", "message": guided}
            return {"kind": "replay", "message": "Sure — tell me your main goal, and I’ll recommend the better option for that goal."}

    # A useful answer that is not a simple yes/no means the user is answering
    # the clarification. Keep the state only when it still needs information.
    if pending.get("kind") == "course_guidance":
        scenario = _scenario_from_goal(text)
        if scenario:
            course_map = {
                "mis": "excel", "data_analyst": "data_analytics",
                "back_office": "office_executive", "programming": "python",
                "accounting": "tally", "grammar": "foundation_english",
                "speaking": "rapido_english", "weak_english": "foundation_english",
            }
            cid = course_map.get(scenario)
            if cid:
                course = get_knowledge().get("courses", {}).get(cid, {})
                name = course.get("name", cid.replace("_", " ").title())
                context.set_course(cid)
                context.clear_pending()
                reasons = {
                    "mis": "Advanced Excel is directly useful for MIS work because it covers data management, analysis, reporting and dashboards.",
                    "data_analyst": "Data Analytics is directly aligned with data analyst work involving data handling, reporting and visualization.",
                    "back_office": "Office Executive is designed for office-based careers and covers office productivity and administration skills.",
                    "programming": "Python Programming builds programming and problem-solving skills for software development.",
                    "accounting": "Tally Prime with GST is focused on accounting and related business operations.",
                    "grammar": "Foundation English focuses on grammar and core English language skills.",
                    "speaking": "Rapido English focuses directly on speaking, conversation, pronunciation and confidence.",
                    "weak_english": "Foundation English is the better starting point for building essential English skills.",
                }
                return {"kind": "replay", "message": f"Based on your goal, **{name}** would be a suitable choice. {reasons[scenario]}"}
        context.clear_pending()
        return None

    return None

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

    if len(message) > 2000:
        return {
            "response": "Please keep your message under 2000 characters.",
            "session_id": session_id,
            "trigger_lead_form": False,
            "end_session": False,
        }

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

    # Continue an explicit clarification from the previous turn before
    # running generic intent detection.
    pending_result = _handle_pending_followup(message, session_id)
    if pending_result and pending_result.get("kind") == "replay":
        response = pending_result["message"]
        save_message(session_id, "Bot", response)
        return {
            "response": response, "session_id": session_id,
            "intent": get_context(session_id).get_intent(), "intent_score": 100.0,
            "course": get_context(session_id).get_course(), "course_score": 100.0 if get_context(session_id).get_course() else 0.0,
            "course_from_context": True, "course_can_answer": False,
            "course_faq": None, "course_faq_score": 0.0,
            "academy_faq": None, "academy_faq_score": 0.0,
            "course_offered": bool(get_context(session_id).get_course()),
            "trigger_lead_form": should_trigger_lead_form(session_id),
            "end_session": False,
        }

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

    # Deterministic corrections for common academy questions where broad
    # fuzzy intent matches are misleading.
    if re.search(r"\b(when does (?:the )?academy (?:open|close)|what time does (?:the )?academy (?:open|close)|what time do you (?:open|close)|are you open at \d|opening hours?|closing hours?|working hours?)\b", normalized_message):
        intent = "academy_timings"
        intent_score = 100.0
    elif (
        "parking" not in normalized_message
        and re.search(r"\b(which branch is in vitthalwadi|branch in vitthalwadi|vitthalwadi branch)\b", normalized_message)
    ):
        intent = "branches"
        intent_score = 100.0
        # Keep this as a deterministic fact instead of returning every branch.
        direct = "Branch 2 is in Vitthalwadi: 2nd Floor, Hardik Complex, Besides Suraj Sofa, Vitthalwadi, Bhavnagar."
        save_message(session_id, "Bot", direct)
        return {"response": direct, "session_id": session_id, "intent": "branches", "intent_score": 100.0, "course": None, "course_score": 0.0, "course_from_context": False, "course_can_answer": False, "course_faq": "branch_in_vitthalwadi", "course_faq_score": 100.0, "academy_faq": None, "academy_faq_score": 0.0, "course_offered": False, "trigger_lead_form": should_trigger_lead_form(session_id), "end_session": False}
    elif re.search(r"\b(where is shital academy|what is your address|where are you located|where is your branch|where is branch [12]|address of branch [12])\b", normalized_message):
        intent = "branches"
        intent_score = 100.0

    get_context(session_id).set_intent(intent)

    # =====================================================
    # 8. DETECT COURSE
    # =====================================================

    course_id, course_score = detect_course(message)

    # Deterministic academy-level questions that are easy to phrase in many ways.
    if re.search(r"\bwhy should i (?:join|choose) (?:shital academy|the academy)\b", normalized_message):
        intent = "why_choose"
        intent_score = 100.0
    elif re.search(r"\bwhat (?:do you|does shital academy) do\b", normalized_message):
        intent = "academy_info"
        intent_score = 100.0

    inferred_scenario = _scenario_from_goal(message)
    if intent is None and inferred_scenario:
        intent = "recommendation"
        intent_score = 100.0
    comparison_signal_now = any(
        token in normalized_message
        for token in (" vs ", " versus ", " compare ", "difference", " between ", " or ")
    )

    # Generic career recommendation should not be hijacked by a weak course
    # match (for example, "speaking" matching Spoken English).
    if intent == "recommendation" and inferred_scenario and not comparison_signal_now:
        generic_map = {
            "mis": ("Advanced Excel", "It is directly useful for MIS work involving data management, analysis, reporting and dashboards."),
            "data_analyst": ("Data Analytics", "It is directly aligned with data analyst work involving data handling, reporting and visualization."),
            "back_office": ("Office Executive", "It is designed for office-based careers and covers office productivity, computer and administration skills."),
            "programming": ("Python Programming", "It focuses on programming, logical thinking, problem-solving and software development."),
            "accounting": ("Tally Prime with GST", "It focuses on accounting, ledgers, vouchers, GST, TDS and related accounts work."),
            "grammar": ("Foundation English Course", "It focuses on grammar and core English language skills."),
            "speaking": ("Rapido English Course", "It focuses directly on speaking, conversation, pronunciation, vocabulary and confidence."),
            "weak_english": ("Foundation English Course", "It is the better starting point for building essential English skills."),
        }
        if inferred_scenario in generic_map:
            name, reason = generic_map[inferred_scenario]
            direct = f"For your goal, **{name}** would be the more suitable choice. {reason}"
            save_message(session_id, "Bot", direct)
            return {"response": direct, "session_id": session_id, "intent": "recommendation", "intent_score": 100.0, "course": None, "course_score": 0.0, "course_from_context": False, "course_can_answer": False, "course_faq": None, "course_faq_score": 0.0, "academy_faq": None, "academy_faq_score": 0.0, "course_offered": True, "trigger_lead_form": should_trigger_lead_form(session_id), "end_session": False}

    # Single-course career questions should be answered directly instead of
    # returning the generic counselor prompt.
    if course_id and not comparison_signal_now and intent == "recommendation":
        knowledge = get_knowledge()
        direct = _single_course_recommendation(course_id, message, knowledge)
        if direct:
            save_message(session_id, "Bot", direct)
            return {
                "response": direct, "session_id": session_id,
                "intent": "recommendation", "intent_score": 100.0,
                "course": course_id, "course_score": course_score,
                "course_from_context": False, "course_can_answer": False,
                "course_faq": None, "course_faq_score": 0.0,
                "academy_faq": None, "academy_faq_score": 0.0,
                "course_offered": True, "trigger_lead_form": should_trigger_lead_form(session_id),
                "end_session": False,
            }

    # =====================================================
    # 9. QUERY ANALYSIS: MULTI-TOPIC + COMPARISON
    # =====================================================
    topics = analyze_topics(message)
    comparison_ids = comparison_courses(message, detect_course)

    # A comparison must name at least two recognizable courses.
    comparison_signal = any(
        token in normalized_message
        for token in ("confused", "compare", "difference", " vs ", " versus ", " or ", "between ")
    )
    if len(comparison_ids) >= 2 and (
        intent in {"comparison", "recommendation"}
        or comparison_signal
    ):
        knowledge = get_knowledge()
        response = _comparison_guidance(comparison_ids, message, knowledge)
        _set_pending(session_id, "comparison_goal", courses=comparison_ids, comparison_message=message)
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
                "placement_guarantee", "certificate_recognition", "admission",
                "payment_methods", "fee_receipt", "internship", "leave_policy",
                "teaching_methodology", "why_choose", "admission_open",
                "join_anytime", "batch_change", "practical_training",
            }:
                if topic == "online_classes":
                    if "offline" in normalized_message and "online" in normalized_message:
                        answer = (
                            "Yes. Most courses are conducted through offline classroom training. "
                            "Online batches may be available depending on the preferred course; please contact the academy to confirm current online-batch availability."
                        )
                    elif "offline" in normalized_message:
                        answer = "Yes. Most courses are conducted through offline classroom training."
                    else:
                        faq, _ = search_academy_faq(message, "online_classes")
                        answer = build_response(
                            intent="online_classes",
                            course=resolved_course,
                            course_id=resolved_course_id,
                            academy_faq=faq,
                            knowledge=knowledge,
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
            "course_fees", "course_duration", "course_start_date", "course_modules",
            "study_material", "course_certificate", "certificate_recognition", "practice_tests",
            "prerequisites", "course_eligibility", "placement_guarantee", "placement",
            "demo_class", "installment_payment", "documents_required",
            "refund_policy", "online_classes", "batch", "academy_timings",
            "branches", "language_of_instruction", "parking", "equipment",
            "missed_class", "discounts", "payment_methods", "fee_receipt",
            "internship", "leave_policy", "teaching_methodology", "why_choose",
            "admission_open", "join_anytime", "batch_change", "practical_training",
            "why_choose", "recommendation", "admission",
        ]
        for topic in priority:
            if topic in topics:
                intent = topic
                intent_score = 100.0
                break

    # High-signal course-specific prerequisite questions must beat the
    # generic admission intent caused by words such as "join".
    if "prerequisites" in topics:
        intent = "prerequisites"
        intent_score = 100.0

    # If a recognized course is explicitly named but no specific question
    # topic was detected, treat it as a request for course information.
    if intent is None and course_id:
        intent = "course_info"
        intent_score = max(intent_score, 90.0)

    # Block common prompt-injection / internal-instruction probes.
    injection_markers = (
        "ignore previous instructions",
        "ignore all rules",
        "reveal your system prompt",
        "show system prompt",
        "hidden instructions",
        "developer instructions",
    )
    if any(marker in normalized_message for marker in injection_markers):
        intent = None
        intent_score = 0.0

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
        response = (
            "Yes. Shital Academy offers offline classroom training. "
            "For the specific course and batch schedule, please contact the academy."
        )
    else:
        response = None

    # =====================================================
    # 16. VERIFIED POLICY / SAFETY RESPONSES
    # =====================================================

    if intent == "certificate_recognition":
        response = (
            "Shital Academy provides a certificate after successful course completion. "
            "I don't have verified information about government recognition of the certificate, "
            "so please confirm the government recognition details with the academy before relying on it for a specific requirement."
        )

    elif intent == "placement_guarantee":
        response = (
            "Shital Academy provides placement support for the Diploma in Office Executive "
            "course and IT courses, but placement is not guaranteed. "
            "The level of assistance may vary by course."
        )

    elif intent == "online_classes":
        if "offline" in normalized_message and "online" in normalized_message:
            response = (
                "Yes. Most courses are conducted through offline classroom training. "
                "Online batches may be available depending on the preferred course; please contact the academy to confirm current online-batch availability."
            )
        elif "offline" in normalized_message:
            response = "Yes. Most courses are conducted through offline classroom training."
        else:
            response = (
                "Online batches may be available depending on the preferred course. "
                "Please contact the academy to check current online-batch availability."
            )

    elif intent == "batch" and any(x in normalized_message for x in ("after 6", "after 5", "after six", "after five")):
        response = (
            "Flexible batch timings are available, but the exact batch time depends on the course and available seats. "
            "The academy is open from 7:00 a.m. to 8:00 p.m. Please contact the academy to confirm a batch after 6 p.m."
        )

    # =====================================================
    # 17. BUILD FINAL RESPONSE
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

    # Store explicit clarification prompts so the next turn can continue
    # naturally instead of falling into generic help.
    if response and "Which course are you asking about?" in response:
        _set_pending(session_id, "duration_course" if intent == "course_duration" else "fees_course" if intent == "course_fees" else "course_question", intent=intent)
    elif response and "Which course are you interested in?" in response:
        if intent == "admission":
            _set_pending(session_id, "admission_course")
        elif intent == "demo_class":
            _set_pending(session_id, "demo_course")
    elif intent == "recommendation" and response and (
        "What is your education and career goal?" in response
        or "What is your education level and career goal?" in response
    ):
        _set_pending(session_id, "course_guidance")

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