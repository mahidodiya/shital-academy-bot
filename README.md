# 🤖 Shital Academy Virtual Assistant

An AI-powered chatbot built with **FastAPI**, **spaCy**, and **Groq LLM** to answer student queries about Shital Academy. The chatbot first searches a local knowledge base for fast, accurate responses and falls back to an LLM when no suitable answer is found.

🌐 **Live Demo:** https://shital-academy-bot.onrender.com

---

## ✨ Features

- 📚 Answers questions from a local knowledge base
- 🧠 Natural Language Processing using spaCy
- 🤖 Groq LLM fallback for unknown questions
- 💬 Web-based chat interface
- 👤 Automatic lead capture after multiple questions
- 📧 Conversation transcript emailed to the academy
- ⚡ FastAPI REST API
- 🌍 Deployed on Render

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Backend |
| FastAPI | Web framework |
| spaCy | NLP preprocessing |
| Groq API | AI response generation |
| HTML/CSS/JavaScript | Frontend |
| Jinja2 | HTML templating |
| Render | Cloud deployment |

---

## 📂 Project Structure

```
shital-academy-bot/
│
├── main.py
├── chatbot.py
├── knowledge_base.py
├── llm_helper.py
├── session_manager.py
├── templates/
├── static/
├── requirements.txt
└── README.md
---

## 🚀 Getting Started

### Clone the repository

```bash
git clone https://github.com/mahidodiya/mini-projects-hub.git
cd 01-NLP-Chatbots/shital-academy-bot
```

### Create a virtual environment

```bash
python -m venv .venv
```

### Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file:

```env
API_KEY=your_groq_api_key

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ACADEMY_EMAIL=academy@example.com
```

### Run the application

```bash
uvicorn main:app --reload
```

Visit:

```
http://127.0.0.1:8000
```

API Documentation:

```
http://127.0.0.1:8000/docs
---

## 🌐 Deployment

The application is deployed on **Render**.

Live URL:

https://shital-academy-bot.onrender.com

---

## 🔮 Future Improvements

- Database integration
- User authentication
- Admin dashboard
- Conversation analytics
- Multi-language support
- Voice interaction

---

## 👨‍💻 Author

**Mahi Dodiya**
---

## 📄 License

This project is licensed under the MIT License.
