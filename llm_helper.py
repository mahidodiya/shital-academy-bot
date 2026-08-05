import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Create LLM client
client = Groq(
    api_key=os.getenv("API_KEY")
)

SYSTEM_PROMPT = """
You are the AI assistant for Shital Academy.

Rules:
- Answer only general knowledge questions.
- Never make up information about Shital Academy.
- If asked about Shital Academy and you don't know the answer,
  politely ask the user to contact the academy.
- Keep answers under 120 words.
- Be friendly and professional.
"""

def ask_llm(user_message):
    """
    Send a user message to the configured LLM
    and return the generated response.
    """

    try:

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.3,
            max_tokens=250,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        print("LLM Error:", e)

        return (
            "I'm sorry, I'm unable to answer your question at the moment. "
            "Please try again later."
        )