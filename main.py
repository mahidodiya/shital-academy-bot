import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field

from chatbot import (
    process_message,
    submit_lead,
    cleanup_expired_sessions,
)

from session_manager import create_session


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Shital Academy Chatbot API",
    version="1.0.0",
)

# Configurable CORS for embedding the chatbot/API on the academy website.
# Set ALLOWED_ORIGINS to a comma-separated list in production, for example:
# https://shitalacademy.com,https://www.shitalacademy.com
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )


# =========================================================
# TEMPLATES
# =========================================================

templates = Jinja2Templates(
    directory="templates"
)


# =========================================================
# STATIC FILES
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# =========================================================
# REQUEST MODELS
# =========================================================

class UserMessage(BaseModel):

    message: str = Field(min_length=1, max_length=2000)

    session_id: str | None = Field(default=None, max_length=128)


class LeadData(BaseModel):

    session_id: str = Field(min_length=1, max_length=128)

    name: str = Field(min_length=1, max_length=100)

    email: str = Field(min_length=3, max_length=254)

    mobile: str = Field(min_length=10, max_length=16)


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {"status": "ok", "service": "shital-academy-chatbot", "version": "1.0.0"}


# =========================================================
# HOME
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
def home(request: Request):

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request
        }
    )


# =========================================================
# CHAT
# =========================================================

@app.post("/chat")
def chat_endpoint(
    payload: UserMessage
):

    # -----------------------------------------------------
    # Validate message
    # -----------------------------------------------------

    user_message = payload.message.strip()

    if not user_message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    # -----------------------------------------------------
    # Create session if necessary
    # -----------------------------------------------------

    session_id = payload.session_id

    if session_id is None:

        session_id = create_session()

    # -----------------------------------------------------
    # Cleanup inactive sessions
    #
    # Runs after we know which session_id this request will
    # use, and excludes it, so a session can never be expired
    # and wiped out from under the very message that's about
    # to use it.
    # -----------------------------------------------------

    cleanup_expired_sessions(exclude_session_id=session_id)

    # -----------------------------------------------------
    # Main chatbot
    # -----------------------------------------------------

    result = process_message(
        message=user_message,
        session_id=session_id
    )

    return result


# =========================================================
# LEAD SUBMISSION
# =========================================================

@app.post("/lead")
def submit_lead_endpoint(
    payload: LeadData
):

    try:

        result = submit_lead(
            session_id=payload.session_id,
            name=payload.name,
            email=payload.email,
            mobile=payload.mobile,
        )

    except Exception as exc:

        # e.g. send_transcript_to_academy() hitting a network/
        # email failure. Without this, an unhandled exception
        # here would surface as a raw 500 with no clean message,
        # and the caller wouldn't know if the lead was saved.
        raise HTTPException(
            status_code=500,
            detail="Could not submit lead. Please try again."
        ) from exc

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )

    return result