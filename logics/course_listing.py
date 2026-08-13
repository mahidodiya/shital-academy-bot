import re
from knowledge_loader import get_knowledge

KNOWLEDGE = get_knowledge()


def get_courses_offered(category=None):
    academy = KNOWLEDGE["academy"].get("academy", {})
    courses = academy.get("courses_offered", {})

    if category == "english":
        return courses.get("english", [])

    if category == "it":
        return courses.get("it", [])

    return (
        courses.get("english", [])
        + courses.get("it", [])
    )


def detect_course_listing(user_text: str):
    text = re.sub(r"[^\w\s]", "", user_text.lower()).strip()

    english_patterns = [
        "what english courses do you offer",
        "what english courses are available",
        "which english courses do you offer",
        "list english courses",
        "english courses",
        "english courses offered",
        "english courses available",
        "what english courses",
    ]

    for pattern in english_patterns:
        if pattern in text:
            return "english"

    it_patterns = [
        "what computer courses do you offer",
        "what computer courses are available",
        "which computer courses do you offer",
        "list computer courses",
        "computer courses",
        "computer courses offered",
        "computer courses available",
        "what it courses do you offer",
        "what it courses are available",
        "it courses",
    ]

    for pattern in it_patterns:
        if pattern in text:
            return "it"

    all_patterns = [
        "what courses do you provide",
        "what courses do you offer",
        "what courses are available",
        "which courses do you offer",
        "which courses are available",
        "list all courses",
        "list all available courses",
        "all courses",
        "courses offered",
        "courses available",
        "courses do you provide",
    ]

    for pattern in all_patterns:
        if pattern in text:
            return "all"

    return None


def format_course_listing(category):
    courses = get_courses_offered(category)

    if not courses:
        return "I couldn't find the course information right now."

    if category == "english":
        title = "English Courses"
    elif category == "it":
        title = "Information Technology Courses"
    else:
        title = "Courses Offered"

    response = f"{title}:\n\n"

    for course in courses:
        response += f"• {course}\n"

    return response.strip()