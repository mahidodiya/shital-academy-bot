import time

from chatbot import (
    process_message,
    submit_lead,
    cleanup_expired_sessions,
)

from session_manager import (
    create_session,
    get_session,
)


print("=" * 70)
print("SESSION TIMEOUT TEST")
print("=" * 70)


# ---------------------------------------------------------
# Create session
# ---------------------------------------------------------

session_id = create_session()

print("\nSession created:")
print(session_id)


# ---------------------------------------------------------
# Simulate conversation
# ---------------------------------------------------------

result = process_message(
    "tell me about python",
    session_id
)

print("\nBot:")
print(result["response"])


# ---------------------------------------------------------
# Simulate lead capture
# ---------------------------------------------------------

result = submit_lead(
    session_id,
    name="Test User",
    email="test.user@example.com",
    mobile="9876543210",
)

print("\nLead submission:")
print(result)


# ---------------------------------------------------------
# Check session
# ---------------------------------------------------------

session = get_session(session_id)

print("\nBefore timeout:")
print(
    "Captured:",
    session["lead"]["captured"]
)

print(
    "Email sent:",
    session["lead"]["email_sent"]
)


# ---------------------------------------------------------
# Wait for timeout
# ---------------------------------------------------------

print("\nWaiting for session timeout...")

time.sleep(65)


# ---------------------------------------------------------
# Cleanup
# ---------------------------------------------------------

print("\nRunning cleanup...")

cleanup_expired_sessions()


# ---------------------------------------------------------
# Check result
# ---------------------------------------------------------

print("\nRemaining session:")

from session_manager import sessions

print(
    session_id in sessions
)