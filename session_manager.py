from uuid import uuid4
from datetime import datetime, timedelta


# ==========================================================
# Configuration
# ==========================================================

# After this much inactivity, the session is considered
# abandoned/inactive.
#
# For testing, 1 minute is convenient.
# For production, we can later change this to 15-30 minutes.
SESSION_TIMEOUT_MINUTES = 1


# ==========================================================
# In-memory Session Storage
# ==========================================================

sessions = {}


# ==========================================================
# Session Factory
# ==========================================================

def _new_session():
    """
    Create the internal structure for a new session.
    """

    now = datetime.now()

    return {
        "lead": {
            "captured": False,
            "email_sent": False,

            "question_count": 0,

            "name": "",
            "email": "",
            "mobile": "",
        },

        "conversation": [],

        "created_at": now,
        "last_activity": now,
    }


# ==========================================================
# Create Session
# ==========================================================

def create_session():
    """
    Create a brand-new user session.
    """

    session_id = str(uuid4())

    sessions[session_id] = _new_session()

    return session_id


# ==========================================================
# Get Session
# ==========================================================

def get_session(session_id):
    """
    Return an existing session.

    If the session does not exist, create a new one.
    """

    if session_id not in sessions:
        sessions[session_id] = _new_session()

    return sessions[session_id]


# ==========================================================
# Update Activity
# ==========================================================

def update_activity(session_id):
    """
    Update the last activity timestamp for a session.
    """

    session = get_session(session_id)

    session["last_activity"] = datetime.now()


# ==========================================================
# Get Lead
# ==========================================================

def get_lead(session_id):
    """
    Return the lead dictionary for a session.
    """

    return get_session(session_id)["lead"]


# ==========================================================
# Get Conversation
# ==========================================================

def get_conversation(session_id):
    """
    Return the conversation list for a session.
    """

    return get_session(session_id)["conversation"]


# ==========================================================
# Clear Session
# ==========================================================

def clear_session(session_id):
    """
    Delete a session after the chat has finished.
    """

    if session_id in sessions:
        del sessions[session_id]


# ==========================================================
# Find Expired Sessions
# ==========================================================

def get_expired_sessions():
    """
    Return session IDs that have been inactive longer than
    SESSION_TIMEOUT_MINUTES.
    """

    now = datetime.now()

    timeout = timedelta(
        minutes=SESSION_TIMEOUT_MINUTES
    )

    expired = []

    for session_id, session in sessions.items():

        last_activity = session.get(
            "last_activity",
            now
        )

        if now - last_activity >= timeout:

            expired.append(session_id)

    return expired