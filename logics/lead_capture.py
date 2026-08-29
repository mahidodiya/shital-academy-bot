"""
lead_capture.py

Lead capture and academy notification utilities.

This module is responsible for:
- Saving conversation messages
- Validating email addresses
- Validating mobile numbers
- Sending captured lead information and conversation
  transcript to the academy using Resend

The actual lead form is handled by the API/frontend.
"""

import os
import re
import requests

from datetime import datetime

from dotenv import load_dotenv

from session_manager import (
    get_conversation,
    get_lead,
)


# =========================================================
# Environment Configuration
# =========================================================

load_dotenv()

# Resend API configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# Academy email where leads should be received
ACADEMY_EMAIL = os.getenv("ACADEMY_EMAIL")

# Sender email
#
# If you have not verified your own domain in Resend,
# use Resend's testing sender:
#
# onboarding@resend.dev
#
# Later, after verifying your domain, you can change
# this environment variable to your own academy email.
RESEND_FROM_EMAIL = os.getenv(
    "RESEND_FROM_EMAIL",
    "onboarding@resend.dev"
)


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
# Send Transcript to Academy using Resend
# =========================================================

def send_transcript_to_academy(
    session_id
):
    """
    Send captured lead details and conversation
    transcript to the academy using Resend API.
    """

    lead = get_lead(
        session_id
    )

    conversation = get_conversation(
        session_id
    )

    # -----------------------------------------------------
    # Validate lead
    # -----------------------------------------------------

    if not lead:
        return False

    if not lead.get("captured"):
        return False

    # -----------------------------------------------------
    # Prevent duplicate emails
    # -----------------------------------------------------

    if lead.get("email_sent"):
        return True

    # -----------------------------------------------------
    # Check Resend configuration
    # -----------------------------------------------------

    if not RESEND_API_KEY:

        print(
            "Email configuration error: "
            "RESEND_API_KEY is missing."
        )

        return False

    if not ACADEMY_EMAIL:

        print(
            "Email configuration error: "
            "ACADEMY_EMAIL is missing."
        )

        return False

    if not RESEND_FROM_EMAIL:

        print(
            "Email configuration error: "
            "RESEND_FROM_EMAIL is missing."
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

    subject = (
        f"New Chatbot Lead - "
        f"{lead.get('name', 'Unknown')}"
    )

    # -----------------------------------------------------
    # Resend API request
    # -----------------------------------------------------

    url = "https://api.resend.com/emails"

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [ACADEMY_EMAIL],
        "subject": subject,
        "text": body,
    }

    # -----------------------------------------------------
    # Send email
    # -----------------------------------------------------

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        # Resend returns HTTP 200 when the email
        # request is accepted successfully.
        if response.status_code in (200, 201):

            # Mark email as sent only after
            # successful API response.
            lead["email_sent"] = True

            print(
                "Lead email sent successfully."
            )

            return True

        # -------------------------------------------------
        # Resend returned an error
        # -------------------------------------------------

        print(
            "Resend Email Error:",
            response.status_code,
            response.text
        )

        return False

    except requests.RequestException as e:

        print(
            "Email Network Error:",
            e
        )

        return False

    except Exception as e:

        print(
            "Email Error:",
            e
        )

        return False