import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from pydantic import BaseModel

from chatbot import (
    process_message,
    submit_lead,
    cleanup_expired_sessions,
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Shital Academy Chatbot API"
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
    message: str
    session_id: str | None = None


class LeadData(BaseModel):
    session_id: str
    name: str
    email: str
    mobile: str


# =========================================================
# HOME
# =========================================================

@app.get("/", response_class=HTMLResponse)
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
def chat_endpoint(payload: UserMessage):

    # -----------------------------------------------------
    # Clean abandoned sessions before processing
    # -----------------------------------------------------

    cleanup_expired_sessions()

    # -----------------------------------------------------
    # Validate message
    # -----------------------------------------------------

    if not payload.message.strip():

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    # -----------------------------------------------------
    # Let chatbot.py handle EVERYTHING else
    # -----------------------------------------------------

    result = process_message(
        message=payload.message,
        session_id=payload.session_id
    )

    return result


# =========================================================
# LEAD
# =========================================================

@app.post("/lead")
def lead_endpoint(payload: LeadData):

    # -----------------------------------------------------
    # Clean abandoned sessions
    # -----------------------------------------------------

    cleanup_expired_sessions()

    # -----------------------------------------------------
    # Submit lead through chatbot orchestration
    # -----------------------------------------------------

    result = submit_lead(
        session_id=payload.session_id,
        name=payload.name,
        email=payload.email,
        mobile=payload.mobile
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )

    return result