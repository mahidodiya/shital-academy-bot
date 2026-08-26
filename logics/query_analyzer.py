"""Lightweight query analysis for multi-topic and comparison questions."""

import re
from rapidfuzz import fuzz

TOPIC_PATTERNS = {
    "course_start_date": [r"\bstarting date\b", r"\bstart date\b", r"\bwhen does .*\bstart\b", r"\bwhen do .*\bstart\b"],
    "course_fees": [
        r"\bfees?\b", r"\bfee\b", r"\bprice\b", r"\bcost\b", r"\bhow much\b",
        r"\bcharges?\b", r"\bpay\b.*\bfee", r"\bpayment\b.*\bfee",
    ],
    "course_duration": [
        r"\bduration\b", r"\bhow long\b", r"\bhow many months?\b",
        r"\bhow many weeks?\b", r"\bmonths?\b.*\b(course|take|complete)\b",
    ],
    "course_certificate": [r"\bcertificate\b", r"\bcertif", r"\bcertification\b"],
    "certificate_recognition": [r"\bgovernment recognized\b", r"\bgovt recognized\b", r"\brecognized certificate\b", r"\brecognised certificate\b", r"\bstandard certificate\b", r"\bcertificate standard\b"],
    "study_material": [r"\bstudy material\b", r"\bmaterials?\b", r"\bnotes\b", r"\bbooks\b"],
    "course_modules": [r"\bsyllabus\b", r"\bmodules?\b", r"\bcurriculum\b", r"\btopics? covered\b", r"\btyping\b", r"\btyping practice\b", r"\binclude[s]?\b.*\b(tally|excel|power bi|sql|django|flask|payroll|export sales|typing|ai tools|shortcut)\b"],
    "practice_tests": [r"\bmock tests?\b", r"\bpractice tests?\b", r"\bpractice\b.*\btests?\b"],
    "course_eligibility": [r"\bage limit\b", r"\bany age\b", r"\bwho can join\b", r"\beligible\b", r"\bcan .*\bjoin\b", r"\bsenior citizen\b", r"\bsenior citizens\b"],
    "prerequisites": [r"\bprior programming\b", r"\bprior coding\b", r"\bprogramming knowledge\b",
                      r"\bcoding knowledge\b", r"\bno coding\b", r"\bno programming\b"],
    "placement": [r"\bplacement\b", r"\bjob placement\b", r"\bplacement assistance\b"],
    "demo_class": [r"\bdemo\b", r"\btrial class\b", r"\bsample class\b"],
    "installment_payment": [r"\binstallments?\b", r"\bemi\b", r"\bmonthly payment\b"],
    "discounts": [r"\bdiscount\b", r"\boffer\b", r"\btwo friends\b", r"\bgroup discount\b"],
    "documents_required": [r"\bdocuments?\b", r"\bid proof\b"],
    "online_classes": [r"\bonline\b", r"\bvirtual\b", r"\bremote\b", r"\boffline\b", r"\bin person\b", r"\bclassroom\b"],
    "batch": [r"\bbatch\b", r"\bafter 6\b", r"\bafter 5\b", r"\bweekend\b", r"\bsunday\b",
              r"\bworking professionals?\b", r"\bflexible\b.*\btime\b"],
    "academy_timings": [r"\btiming\b", r"\btimings\b", r"\bopening\b.*\bhours?\b",
                        r"\bclosing\b.*\bhours?\b", r"\bworking hours\b"],
    "branches": [r"\bbranch\b", r"\baddress\b", r"\blocation\b", r"\bwhere\b.*\bbranch\b"],
    "language_of_instruction": [r"\bgujarati\b", r"\bhindi\b", r"\blanguage of instruction\b",
                                r"\btaught in\b", r"\bonly english\b"],
    "parking": [r"\bparking\b"],
    "equipment": [r"\blaptop\b", r"\bcomputer required\b"],
    "missed_class": [r"\bmiss\b.*\bclass\b", r"\bbackup\b.*\bclass\b", r"\bmakeup\b.*\bclass\b"],
    "refund_policy": [r"\brefund\b", r"\brefundable\b", r"\bcancel\b.*\badmission\b"],
    "admission": [r"\badmission\b", r"\benroll\b", r"\bjoin\b", r"\bstarting date\b"],
    "recommendation": [r"\bconfused\b", r"\bwhich course\b", r"\bshould i\b", r"\bwhich one\b"],
}

def analyze_topics(text):
    text=(text or "").lower()
    found=[]
    for topic, patterns in TOPIC_PATTERNS.items():
        if any(re.search(p,text) for p in patterns):
            found.append(topic)
    # Remove broad admission if a specific admission-document question exists.
    if "documents_required" in found and "admission" in found:
        found.remove("admission")
    if "course_start_date" in found and "admission" in found:
        found.remove("admission")
    if "course_certificate" in found and "course_info" in found:
        found.remove("course_info")
    if "demo_class" in found and "before paying" in text and "course_fees" in found:
        found.remove("course_fees")
    return found

def comparison_courses(text, course_detector):
    """Detect up to two explicit course names for comparison questions."""
    # Use detector on chunks/aliases supplied by the detector module.
    # The full detector can only return one; split on comparison connectors.
    parts = re.split(r"\b(?:vs|versus|or|and|between)\b|[,/]", (text or "").lower())
    courses=[]
    for part in parts:
        cid, score = course_detector(part.strip())
        if cid and score >= 85 and cid not in courses:
            courses.append(cid)
    return courses[:3]
