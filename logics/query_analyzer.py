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
    "certificate_recognition": [r"\bgovernment recognized\b", r"\bgovernment recognition\b", r"\bgovt recognized\b", r"\brecognized certificate\b"],
    "study_material": [r"\bstudy material\b", r"\bmaterials?\b", r"\bnotes\b", r"\bbooks\b"],
    "course_modules": [
        r"\bsyllabus\b", r"\bmodules?\b", r"\bcurriculum\b", r"\btopics? covered\b",
        r"\b(?:include|includes|cover|covers|teach|teaches|learn|have|has|hai|milegi|milta)\b.*\b(?:payroll|export sales|django|flask|power bi|sql|gujarati typing|shortcut|shortcuts|ai tools|ai|tally|excel)\b",
        r"\b(?:payroll|export sales|django|flask|power bi|sql|gujarati typing|shortcut|shortcuts|ai tools|microsoft office|typing practice)\b",
    ],
    "practice_tests": [r"\bmock tests?\b", r"\bpractice tests?\b", r"\bpractice\b.*\btests?\b"],
    "course_eligibility": [r"\bage limit\b", r"\bany age\b", r"\bwho can join\b", r"\beligible\b", r"\bsenior citizen\b", r"\bcan .* join\b"],
    "prerequisites": [
        r"\bprior programming\b", r"\bprior coding\b", r"\bprogramming knowledge\b",
        r"\bcoding knowledge\b", r"\bno coding\b", r"\bno programming\b",
        r"\bdon[’']?t know anything about programming\b", r"\bknow nothing about programming\b",
        r"\bno coding background\b", r"\bno programming background\b",
    ],
    "placement": [r"\bplacement\b", r"\bjob placement\b", r"\bplacement assistance\b"],
    "placement_guarantee": [r"\bplacement guaranteed\b", r"\bguaranteed placement\b", r"\bguarantee.*placement\b", r"\bplacement.*guarantee\b"],
    "demo_class": [r"\bdemo\b", r"\btrial class\b", r"\bsample class\b"],
    "installment_payment": [r"\binstallments?\b", r"\bemi\b", r"\bmonthly payment\b"],
    "discounts": [r"\bdiscount\b", r"\boffer\b", r"\btwo friends\b", r"\bgroup discount\b"],
    "documents_required": [r"\bdocuments?\b", r"\bid proof\b"],
    "payment_methods": [r"\bupi\b", r"\bcash\b", r"\bbank transfer\b", r"\bcard payment\b", r"\bpayment methods?\b"],
    "fee_receipt": [r"\bfee receipt\b", r"\bpayment receipt\b", r"\breceipt\b", r"\binvoice\b"],
    "internship": [r"\binternship\b", r"\binternships\b"],
    "leave_policy": [r"\btake leave\b", r"\bleave during\b", r"\bholiday during\b"],
    "teaching_methodology": [r"\bteaching methodology\b", r"\bhow do you teach\b", r"\bteaching method\b"],
    "why_choose": [r"\bwhy should i (?:choose|join)\b", r"\bwhy choose shital\b", r"\bwhy shital academy\b", r"\bwhy should i join shital\b"],
    "admission_open": [r"\badmissions? open\b", r"\bis admission open\b"],
    "join_anytime": [r"\bjoin anytime\b", r"\bcan i join anytime\b"],
    "batch_change": [r"\bchange my batch\b", r"\bchange batch\b", r"\bshift batch\b", r"\bbatch transfer\b"],
    "practical_training": [r"\bpractical training\b", r"\bhands[- ]on training\b", r"\bdo courses include practical\b"],
    "online_classes": [r"\bonline\b", r"\bvirtual\b", r"\bremote\b", r"\boffline\b", r"\bin person\b", r"\bclassroom\b"],
    "batch": [r"\bbatch\b", r"\bafter 6\b", r"\bafter 5\b", r"\bweekend\b", r"\bsunday\b",
              r"\bworking professionals?\b", r"\bflexible\b.*\btime\b"],
    "academy_timings": [
        r"\btiming\b", r"\btimings\b", r"\bworking hours\b",
        r"\bwhen does (?:the )?academy (?:open|close)\b",
        r"\bwhat time does (?:the )?academy (?:open|close)\b",
        r"\bwhat time do you (?:open|close)\b",
        r"\bare you open at \d",
        r"\bopening hours?\b", r"\bclosing hours?\b",
    ],
    "branches": [r"\bbranch\b", r"\baddress\b", r"\blocation\b", r"\bwhere\b.*\bbranch\b"],
    "language_of_instruction": [r"\bgujarati\b", r"\bhindi\b", r"\blanguage of instruction\b",
                                r"\btaught in\b", r"\bonly english\b"],
    "parking": [r"\bparking\b"],
    "equipment": [r"\blaptop\b", r"\bcomputer required\b"],
    "missed_class": [r"\bmiss\b.*\bclass\b", r"\bbackup\b.*\bclass\b", r"\bmakeup\b.*\bclass\b"],
    "refund_policy": [r"\brefund\b", r"\brefundable\b", r"\bcancel\b.*\badmission\b"],
    "admission": [r"\badmission\b", r"\benroll\b", r"\bjoin tomorrow\b", r"\bstarting date\b"],
    "recommendation": [r"\bconfused\b", r"\bwhich course\b", r"\bshould i\b", r"\bwhich one\b", r"\bwhich course is better\b", r"\bwhich course is best\b", r"\bis .* good for (?:an? )?(?:mis|back office|programming|data analyst|office)\b", r"\bdata management\b", r"\bdata manage\b"],
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
    if "documents_required" in found and "course_eligibility" in found:
        found.remove("course_eligibility")
    if "admission_open" in found and "admission" in found:
        found.remove("admission")
    if "join_anytime" in found and "admission" in found:
        found.remove("admission")
    if "join_anytime" in found and "course_eligibility" in found:
        found.remove("course_eligibility")
    if "fee_receipt" in found and "course_fees" in found:
        found.remove("course_fees")
    if "batch_change" in found and "batch" in found:
        found.remove("batch")
    if "admission" in found and "course_eligibility" in found and "tomorrow" in text:
        found.remove("course_eligibility")
    if "course_start_date" in found and "admission" in found:
        found.remove("admission")
    if any(x in found for x in ("course_eligibility", "prerequisites", "discounts", "refund_policy", "course_fees", "course_duration", "course_modules", "study_material", "course_certificate")) and "admission" in found:
        found.remove("admission")
    if "course_certificate" in found and "course_info" in found:
        found.remove("course_info")
    if "certificate_recognition" in found and "course_certificate" in found:
        found.remove("course_certificate")
    if "prerequisites" in found and "course_eligibility" in found:
        found.remove("course_eligibility")
    if "placement_guarantee" in found and "placement" in found:
        found.remove("placement")
    if "refund_policy" in found and "course_fees" in found and not re.search(r"\b(how much|what is the (?:fee|price)|cost|price)\b", text):
        found.remove("course_fees")
    if "course_modules" in found and "typing" in text and "language_of_instruction" in found:
        found.remove("language_of_instruction")
    if "why_choose" in found and "recommendation" in found:
        found.remove("recommendation")
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
