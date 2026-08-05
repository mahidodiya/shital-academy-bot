from uuid import uuid4

# ==========================================================
# In-memory Session Storage
# ==========================================================

# Structure:
#
# sessions = {
#     session_id: {
#         "lead": {...},
#         "conversation": [...]
#     }
# }
#
# NOTE:
# This is in-memory storage.
# It works perfectly on localhost and Render's free tier.
# Data resets whenever the server restarts.
# ==========================================================

sessions = {}


def create_session():
    """
    Create a brand-new user session.
    """

    session_id = str(uuid4())

    sessions[session_id] = {

        "lead": {

            "captured": False,

            "question_count": 0,

            "name": "",

            "email": "",

            "mobile": ""

        },

        "conversation": []

    }

    return session_id


def get_session(session_id):
    """
    Return an existing session.
    If it doesn't exist, create a new one.
    """

    if session_id not in sessions:

        sessions[session_id] = {

            "lead": {

                "captured": False,

                "question_count": 0,

                "name": "",

                "email": "",

                "mobile": ""

            },

            "conversation": []

        }

    return sessions[session_id]


def get_lead(session_id):
    """
    Return the lead dictionary for a session.
    """

    return get_session(session_id)["lead"]


def get_conversation(session_id):
    """
    Return the conversation list for a session.
    """

    return get_session(session_id)["conversation"]


def clear_session(session_id):
    """
    Delete a session after the chat has finished.
    """

    if session_id in sessions:

        del sessions[session_id]