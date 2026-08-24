import re
from rapidfuzz import fuzz
from knowledge_loader import get_knowledge

KNOWLEDGE = get_knowledge()

# =========================================================
# TYPO-TOLERANT LISTING DETECTION
# =========================================================
#
# The old version of this function matched a fixed list of exact
# phrases like "what courses do you provide". That silently missed
# very common real-world phrasings:
#
#   - singular "course" instead of "courses"
#       ("what course do you provide")
#   - typos ("what course you offfer")
#
# Anything that fell through here used to be picked up (badly) by
# the generic fuzzy intent detector, which can misfire on short,
# unrelated keywords like "bye" or "job" for long sentences. This
# rewrite keeps the check narrow and safe by matching on
# WORD-LEVEL tokens (never whole-sentence fuzzy matching), the same
# pattern used by course_detector.py and greeting_detector.py.

COURSE_WORD_RE = re.compile(r"\bcourses?\b")
ENGLISH_WORD_RE = re.compile(r"\benglish\b")
IT_WORD_RE = re.compile(r"\b(it|computer|computers|technical)\b")

# Words that signal "I want to see the list of courses".
LISTING_TRIGGERS = [
    "provide", "provides", "providing",
    "offer", "offers", "offering", "offered",
    "available", "avail",
    "list", "lists", "listing",
]

# Words that mean the user is asking about a specific ATTRIBUTE of
# a course (fees, duration, ...) rather than asking for a listing,
# even though "course" appears in the sentence. If any of these are
# present we back off and let the normal intent pipeline
# (course_fees, course_duration, ...) handle the message instead.
NON_LISTING_TRIGGERS = [
    "fee", "fees", "price", "cost", "duration", "certificate",
    "eligibility", "syllabus", "module", "modules", "curriculum",
    "batch", "timing", "timings", "placement", "faculty",
]

FUZZY_WORD_THRESHOLD = 82


def _fuzzy_token_match(tokens, trigger, threshold=FUZZY_WORD_THRESHOLD):
    """
    True if any single token is an exact or near (typo-tolerant)
    match for `trigger`. Word-vs-word only - never matched against
    the whole sentence - to avoid the false-positive problem seen
    in the generic intent detector.
    """

    for token in tokens:

        if token == trigger:
            return True

        if len(token) < 3 or len(trigger) < 3:
            continue

        if fuzz.ratio(token, trigger) >= threshold:
            return True

    return False


def _any_fuzzy_token_match(tokens, trigger_list):
    return any(
        _fuzzy_token_match(tokens, trigger)
        for trigger in trigger_list
    )


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
    """
    Detect a "show me the list of courses" request.

    Typo-tolerant and works with singular ("course") or plural
    ("courses") phrasing - matched word-by-word, never as a fuzzy
    match against the whole sentence.
    """

    text = re.sub(r"[^\w\s]", "", user_text.lower()).strip()

    if not text:
        return None

    tokens = text.split()

    # Must mention "course"/"courses" in some form.
    if not (
        COURSE_WORD_RE.search(text)
        or _any_fuzzy_token_match(tokens, ["course", "courses"])
    ):
        return None

    # If the message is really asking about a specific attribute
    # (fees, duration, placement, ...) this is NOT a listing
    # request - let the normal intent pipeline handle it.
    if _any_fuzzy_token_match(tokens, NON_LISTING_TRIGGERS):
        return None

    # A bare mention of "course" (e.g. "python course") should not
    # be treated as "list everything" - we need an explicit
    # listing-style trigger word too.
    if not _any_fuzzy_token_match(tokens, LISTING_TRIGGERS):
        return None

    if ENGLISH_WORD_RE.search(text):
        return "english"

    if IT_WORD_RE.search(text):
        return "it"

    return "all"


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