import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import spacy as sa
from llm_helper import ask_llm

# Import the logic you already wrote from chatbot.py
from chatbot import (
    preprocess,
    greetings,
    goodbye,
    save_message,
    send_transcript_to_academy,
    validate_email,
    validate_mobile,
)

from session_manager import (
    create_session,
    get_lead,
)

app = FastAPI(title="Shital Academy Chatbot API")

templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

nlp = sa.load("en_core_web_sm")

class UserMessage(BaseModel):
    message: str
    session_id: str | None = None
    
class LeadData(BaseModel):
    session_id: str
    name: str
    email: str
    mobile: str

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request
        }
    )
    

@app.post("/chat")
def chat_endpoint(payload: UserMessage):
    session_id = payload.session_id

    if session_id is None:
        session_id = create_session()
        
    user_msg = payload.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    save_message(session_id, "User", user_msg)
    clean_msg = user_msg.lower()

    # Match your existing goodbye logic
    if goodbye(clean_msg):
        reply = "Goodbye! Thank you for contacting Shital Academy."
        save_message(session_id, "Bot", reply)
        send_transcript_to_academy(session_id)
        return {
            "reply": reply,
            "trigger_lead_form": False,
            "end_session": True,
            "session_id": session_id,
}
    # Match your existing greeting logic
    if greetings(clean_msg):
        reply = "Hello! How can I help you today?"
        save_message(session_id, "Bot", reply)

        return {
            "reply": reply,
            "trigger_lead_form": False,
            "end_session": False,
            "session_id": session_id,
}
    # Increment question count for lead tracking
    lead = get_lead(session_id)
    lead["question_count"] += 1
    
    # Check if lead capture is needed (Returns a flag so your frontend knows to show a form)
    trigger_lead_form = False
    if lead["question_count"] >= 3 and not lead["captured"]:
        trigger_lead_form = True

    # Get response from local KB or Groq LLM
    doc = nlp(user_msg)
    reply = preprocess(doc)

    if reply == "Sorry, I didn't understand that. Can you please rephrase?":

        try:
            reply = ask_llm(user_msg)

        except Exception:

            reply = (
                "Sorry, I'm having trouble reaching the AI service right now. "
                "Please try again in a moment."
                )
        
    save_message(session_id, "Bot", reply)
    
    return {
    "reply": reply,
    "trigger_lead_form": trigger_lead_form,
    "end_session": False,
    "session_id": session_id,
}
    
@app.post("/lead")
def submit_lead(payload: LeadData):

    if not payload.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Name is required."
        )

    if not validate_email(payload.email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email address."
        )

    if not validate_mobile(payload.mobile):
        raise HTTPException(
            status_code=400,
            detail="Invalid mobile number."
        )

    lead = get_lead(payload.session_id)

    lead["name"] = payload.name.strip()
    lead["email"] = payload.email.strip()
    lead["mobile"] = payload.mobile.strip()
    lead["captured"] = True

    return {
        "success": True,
        "message": "Lead saved successfully."
    }