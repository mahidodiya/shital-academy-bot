"""It has only one responsibility: retrieve data from the 
knowledge base.It does not detect intent, search FAQs, or
generate replies."""

from knowledge_loader import get_knowledge

KNOWLEDGE = get_knowledge()

COURSES = KNOWLEDGE["courses"]
FAQ = KNOWLEDGE["academy"]["faq"]
ACADEMY = KNOWLEDGE["academy"]["academy"]
INTENTS = KNOWLEDGE["common"]["intents"]
SYNONYMS = KNOWLEDGE["common"]["synonyms"]
GREETINGS = KNOWLEDGE["common"]["greetings"]

def get_course(course_id):
    return COURSES.get(course_id)

def get_course_field(course_id, field):
    course = get_course(course_id)

    if not course:
        return None

    return course.get(field)

def get_course_faqs(course_id):
    course = get_course(course_id)

    if not course:
        return []

    return course.get("faqs", [])

def get_academy_faqs():
    return FAQ.get("faqs", [])

def get_intents():
    return INTENTS.get("intents", [])

def get_synonyms():
    return SYNONYMS.get("synonyms", {})

def get_greetings():
    return GREETINGS.get("greetings", {})