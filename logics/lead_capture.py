"""
lead_capture.py

Lead capture and academy notification utilities.

This module is responsible for:
- Saving conversation messages
- Validating email addresses
- Validating mobile numbers
- Sending captured lead information and conversation
  transcript to the academy

The actual lead form is handled by the API/frontend.
"""

import os
import re
import smtplib

from datetime import datetime
from email.mime.text import MIMEText

from dotenv import load_dotenv

from session_manager import (
    get_conversation,
    get_lead,
)


# =========================================================
# Environment Configuration
# =========================================================

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

ACADEMY_EMAIL = os.getenv("ACADEMY_EMAIL")


# =========================================================
# Save Conversation Message
# =========================================================

def save_message(
    session_id,
    sender,
    message
):
    """
    Save one message to the session conversation history.
    """

    conversation = get_conversation(
        session_id
    )

    timestamp = datetime.now().strftime(
        "%H:%M:%S"
    )

    conversation.append(
        f"[{timestamp}] {sender}: {message}"
    )


# =========================================================
# Email Validation
# =========================================================

def validate_email(email):
    """
    Validate a basic email address.
    """

    if not isinstance(email, str):
        return False

    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    return bool(
        re.match(
            pattern,
            email.strip()
        )
    )


# =========================================================
# Mobile Validation
# =========================================================

def validate_mobile(number):
    """
    Validate an Indian mobile number.

    Accepts:
        9876543210
        98 765 432 10
        +919876543210
    """

    if not isinstance(number, str):
        return False

    number = number.strip()

    number = number.replace(
        " ",
        ""
    )

    if number.startswith("+91"):
        number = number[3:]

    return (
        number.isdigit()
        and len(number) == 10
    )


# =========================================================
# Save Lead
# =========================================================

def save_lead(
    session_id,
    name,
    email,
    mobile
):
    """
    Validate and save lead information.

    Returns:

        {
            "success": True,
            "message": "..."
        }

    or

        {
            "success": False,
            "message": "..."
        }
    """

    if not session_id:

        return {
            "success": False,
            "message": "Session ID is required."
        }

    if not name or not name.strip():

        return {
            "success": False,
            "message": "Name is required."
        }

    if not validate_email(email):

        return {
            "success": False,
            "message": "Please enter a valid email address."
        }

    if not validate_mobile(mobile):

        return {
            "success": False,
            "message": "Please enter a valid mobile number."
        }

    lead = get_lead(
        session_id
    )

    lead["name"] = name.strip()
    lead["email"] = email.strip()
    lead["mobile"] = mobile.strip()

    lead["captured"] = True

    return {
        "success": True,
        "message": "Lead saved successfully."
    }


# =========================================================
# Send Transcript to Academy
# =========================================================

def send_transcript_to_academy(
    session_id
):
    """
    Send captured lead details and conversation
    transcript to the academy.
    """

    lead = get_lead(
        session_id
    )

    conversation = get_conversation(
        session_id
    )

    if not lead:
        return False

    if not lead.get("captured"):
        return False

    if lead.get("email_sent"):
        return True
    # -----------------------------------------------------
    # Check SMTP configuration
    # -----------------------------------------------------

    if not all([
        SMTP_SERVER,
        SMTP_EMAIL,
        SMTP_PASSWORD,
        ACADEMY_EMAIL,
    ]):

        print(
            "Email configuration is incomplete."
        )

        return False

    # -----------------------------------------------------
    # Build email body
    # -----------------------------------------------------

    body = f"""
NEW WEBSITE LEAD

--------------------------------------

Name   : {lead.get('name', '')}
Email  : {lead.get('email', '')}
Mobile : {lead.get('mobile', '')}

--------------------------------------

Conversation

{chr(10).join(conversation)}
"""

    msg = MIMEText(
        body
    )

    msg["Subject"] = (
        f"New Chatbot Lead - "
        f"{lead.get('name', 'Unknown')}"
    )

    msg["From"] = SMTP_EMAIL
    msg["To"] = ACADEMY_EMAIL

    # -----------------------------------------------------
    # Send email
    # -----------------------------------------------------

    try:

        server = smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT
        )

        server.starttls()

        server.login(
            SMTP_EMAIL,
            SMTP_PASSWORD
        )

        server.send_message(
            msg
        )

        server.quit()
        # Mark email as sent only after successful delivery
        lead["email_sent"] = True
        return True

    except Exception as e:

        print(
            "Email Error:",
            e
        )

        return False