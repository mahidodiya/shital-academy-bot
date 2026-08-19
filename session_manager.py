import threading
from uuid import uuid4
from datetime import datetime, timedelta


# ==========================================================
# Configuration
# ==========================================================

# After this much inactivity, the session is considered
# abandoned/inactive.
#
# NOTE: bumped from the old testing value of 1 minute.
# 1 minute meant that any user who took longer than a minute
# to type a reply had their session silently wiped and
# recreated from scratch (lost lead-capture state, question
# count, and transcript) the next time they sent a message.
# 20 minutes is a safer production default; tune as needed.
SESSION_TIMEOUT_MINUTES = 20


# ==========================================================
# In-memory Session Storage
# ==========================================================
#
# NOTE: this dict lives in a single process's memory. If the
# app is ever run with multiple worker processes / replicas
# behind a load balancer, each worker has its own `sessions`
# dict, so a session created on one worker will not be found
# on another -> users would randomly appear to "lose" their
# session. For multi-worker/multi-instance deployments, back
# this with a shared store (e.g. Redis) instead.

sessions = {}

# Guards read-modify-write access to `sessions` so concurrent
# requests (FastAPI runs sync endpoints in a thread pool) can't
# race on the same session dict.
_lock = threading.Lock()


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

    with _lock:
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

    with _lock:
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

    with _lock:
        if session_id in sessions:
            del sessions[session_id]


# ==========================================================
# Find Expired Sessions
# ==========================================================

def get_expired_sessions(exclude_session_id=None):
    """
    Return session IDs that have been inactive longer than
    SESSION_TIMEOUT_MINUTES.

    `exclude_session_id` lets a caller protect the session it
    is about to use right now from being swept up as "expired"
    (e.g. a request that arrives just past the timeout for its
    own session shouldn't have that session deleted out from
    under it before it gets processed).
    """

    now = datetime.now()

    timeout = timedelta(
        minutes=SESSION_TIMEOUT_MINUTES
    )

    expired = []

    # Snapshot with a lock so we're not iterating a dict that
    # another thread is mutating at the same time.
    with _lock:
        items = list(sessions.items())

    for session_id, session in items:

        if session_id == exclude_session_id:
            continue

        last_activity = session.get(
            "last_activity",
            now
        )

        if now - last_activity >= timeout:

            expired.append(session_id)

    return expired