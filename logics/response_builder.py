"""
response_builder.py

Builds final chatbot responses using the following priority:

1. Course structured data
2. Course FAQ
3. Academy FAQ
4. General knowledge
5. Nothing found
"""
UNAVAILABLE_COURSE_NAMES = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
    "html": "HTML",
    "bootstrap": "Bootstrap",
    "customized_english": "Customized English Courses",
    "basic_to_advanced_english": "Basic to Advanced English Course",
    "special_speaking_english": "Special Speaking Course for English Medium Students",
}


COURSE_FALLBACK_RESPONSES = {
    "java": (
        "Java\n\n"
        "Java is a popular programming language used for software development, "
        "web applications, enterprise applications, and problem-solving. "
        "It helps learners develop strong programming and logical thinking skills "
        "and is suitable for students and beginners.\n\n"
        "For the detailed syllabus, duration, fees, and batch timings, "
        "please contact Shital Academy."
    ),

    "html": (
        "HTML\n\n"
        "HTML (HyperText Markup Language) is the standard language used to "
        "create and structure web pages. It helps learners understand website "
        "structure and build the foundation for web development.\n\n"
        "For the detailed syllabus, duration, fees, and batch timings, "
        "please contact Shital Academy."
    ),

    "c": (
        "C\n\n"
        "C is a foundational programming language widely used for learning "
        "programming concepts, problem-solving, and logical thinking. "
        "It provides a strong foundation for understanding programming fundamentals.\n\n"
        "For the detailed syllabus, duration, fees, and batch timings, "
        "please contact Shital Academy."
    ),

    "cpp": (
        "C++\n\n"
        "C++ is a powerful programming language commonly used for programming, "
        "software development, and problem-solving. It helps learners develop "
        "strong programming and logical thinking skills and is suitable for "
        "students and beginners.\n\n"
        "For the detailed syllabus, duration, fees, and batch timings, "
        "please contact Shital Academy."
    ),

    "bootstrap": (
        "Bootstrap\n\n"
        "Bootstrap is a popular frontend framework used to create responsive "
        "and mobile-friendly websites. It helps developers build website layouts "
        "and user interfaces more efficiently.\n\n"
        "For the detailed syllabus, duration, fees, and batch timings, "
        "please contact Shital Academy."
    ),
}

def can_answer_from_course(course, intent):
    """
    Check whether the structured course data can directly
    answer the requested intent.

    IMPORTANT:
    This function checks ONLY structured course fields.
    It does NOT check course FAQs.
    """

    if not course:
        return False

    # -----------------------------------------------------
    # Course Information
    # -----------------------------------------------------

    if intent in {
        "course_info",
        "computer_course",
        "english_course",
    }:
        return bool(course.get("description"))

    # -----------------------------------------------------
    # Course Duration
    # -----------------------------------------------------

    if intent == "course_duration":

        duration = course.get("duration")

        if isinstance(duration, dict):
            return bool(
                duration.get("value")
                or duration.get("note")
            )

        return bool(duration)

    # -----------------------------------------------------
    # Course Fees
    # -----------------------------------------------------

    if intent == "course_fees":

        fees = course.get("fees")

        if isinstance(fees, dict):
            return bool(
                fees.get("range")
                or fees.get("note")
            )

        return bool(fees)

    # -----------------------------------------------------
    # Eligibility
    # -----------------------------------------------------

    if intent == "prerequisites":
        # Prerequisite questions are answered from the course FAQ so
        # the user gets the exact verified wording rather than a raw
        # field dump.
        return False

    if intent == "course_eligibility":

        eligibility = course.get("eligibility")

        if isinstance(eligibility, dict):
            return bool(
                eligibility.get("value")
                or eligibility.get("note")
            )

        return bool(eligibility)

    # -----------------------------------------------------
    # Certificate
    # -----------------------------------------------------

    if intent == "course_certificate":

        return bool(course.get("certificate"))

    # -----------------------------------------------------
    # Study Material
    # -----------------------------------------------------

    if intent == "study_material":

        return bool(course.get("study_material"))

    # -----------------------------------------------------
    # Course Modules
    # -----------------------------------------------------

    if intent == "course_modules":

        return bool(
            course.get("modules")
            or course.get("syllabus")
        )

    # -----------------------------------------------------
    # Learning Outcomes
    # -----------------------------------------------------

    if intent == "learning_outcomes":

        return bool(course.get("learning_outcomes"))

    # -----------------------------------------------------
    # Beginner Friendly
    # -----------------------------------------------------

    if intent == "beginner_friendly":

        recommended_for = course.get(
            "recommended_for",
            []
        )

        if isinstance(recommended_for, list):

            if any(
                "beginner" in str(item).lower()
                for item in recommended_for
            ):
                return True

        target_audience = course.get(
            "target_audience",
            []
        )

        if isinstance(target_audience, list):

            if any(
                "beginner" in str(item).lower()
                for item in target_audience
            ):
                return True

    # -----------------------------------------------------
    # No structured answer available
    # -----------------------------------------------------

    return False


def _build_faq_response(faq):
    """
    Build a response from a matched FAQ.
    """

    if not faq:
        return None

    answer = faq.get("answer")

    if not answer:
        return None

    response = answer

    follow_up = faq.get("follow_up", [])

    if follow_up:
        response += f"\n\n{follow_up[0]}"

    return response


def build_response(
    intent=None,
    course=None,
    course_id=None,
    course_faq=None,
    academy_faq=None,
    knowledge=None,
):
    """
    Build the final chatbot response.

    Priority:

    Course detected:
        1. Structured course data
        2. Course FAQ
        3. Academy FAQ
        4. General knowledge

    No course detected:
        1. Academy FAQ
        2. General knowledge
    """
    # =====================================================
    # COURSE DETECTED BUT DETAILS NOT AVAILABLE
    # =====================================================

    if course_id and not course:

        course_name = UNAVAILABLE_COURSE_NAMES.get(
            course_id,
            course_id.replace("_", " ").title()
        )

        # Answer the requested field safely when the academy offers
        # the course but its detailed JSON is not available yet.
        unavailable_by_intent = {
            "course_start_date": (
                f"I don't have a confirmed starting date for {course_name} yet. "
                f"Please contact Shital Academy for the next available batch date."
            ),
            "course_fees": (
                f"I don't have the detailed fee information for "
                f"{course_name} yet. Please contact Shital Academy "
                f"for the latest fee details."
            ),
            "course_duration": (
                f"I don't have the detailed duration for "
                f"{course_name} yet. Please contact Shital Academy "
                f"for the latest course duration."
            ),
            "course_modules": (
                f"I don't have the detailed syllabus for "
                f"{course_name} yet. Please contact Shital Academy "
                f"for the latest syllabus."
            ),
            "prerequisites": (
                f"I don't have the detailed prerequisite information for "
                f"{course_name} yet. Please contact Shital Academy."
            ),
            "course_eligibility": (
                f"I don't have the detailed eligibility information for "
                f"{course_name} yet. Please contact Shital Academy."
            ),
            "course_certificate": (
                f"I don't have the certificate details for "
                f"{course_name} yet. Please contact Shital Academy."
            ),
        }

        if intent in unavailable_by_intent:
            return unavailable_by_intent[intent]

        fallback_response = COURSE_FALLBACK_RESPONSES.get(course_id)

        if fallback_response:
            return fallback_response

        return (
            f"I don't have detailed information about "
            f"{course_name} yet."
        )

    # =====================================================
    # 1. COURSE DETECTED
    # =====================================================

    if course:

        course_name = course.get(
            "name",
            "this course"
        )

        # -------------------------------------------------
        # Prerequisites
        # -------------------------------------------------

        if intent == "prerequisites":
            response = _build_faq_response(course_faq)
            if response:
                return response

            prerequisites = course.get("prerequisites")
            if prerequisites:
                return str(prerequisites)

        # -------------------------------------------------
        # Course Information
        # -------------------------------------------------

        if intent in {
            "course_info",
            "computer_course",
            "english_course",
        }:

            description = course.get("description")

            if description:
                return (
                    f"{course_name}\n\n"
                    f"{description}"
                )

        # -------------------------------------------------
        # Course Duration
        # -------------------------------------------------

        if intent == "course_duration":

            duration = course.get("duration")

            if isinstance(duration, dict):

                value = duration.get("value")
                note = duration.get("note")

                if value:
                    return (
                        f"The duration of {course_name} "
                        f"is {value}."
                    )

                if note:
                    return note

            elif duration:

                normalized_duration = str(duration).strip().lower()

                if (
                    normalized_duration
                    and "varies" not in normalized_duration
                ):
                    return (
                        f"The duration of {course_name} "
                        f"is {duration}."
                    )

        # -------------------------------------------------
        # Course Fees
        # -------------------------------------------------

        if intent == "course_fees":

            fees = course.get("fees")

            if isinstance(fees, dict):

                fee_range = fees.get("range")
                note = fees.get("note")

                # Empty/placeholder ranges are not real prices.
                if fee_range and str(fee_range).strip():
                    normalized_fee = str(fee_range).strip().lower()

                    placeholder = (
                        not normalized_fee
                        or "varies by course" in normalized_fee
                        or "contact the academy" in normalized_fee
                    )

                    if not placeholder:
                        if note:
                            return (
                                f"The fees for {course_name} "
                                f"are {fee_range}.\n\n"
                                f"{note}"
                            )

                        return (
                            f"The fees for {course_name} "
                            f"are {fee_range}."
                        )

                if note:
                    return note

            elif fees:

                return (
                    f"The fees for {course_name} "
                    f"are {fees}."
                )

        # -------------------------------------------------
        # Course Eligibility
        # -------------------------------------------------

        if intent == "course_eligibility":

            eligibility = course.get("eligibility")

            if eligibility:

                if isinstance(eligibility, dict):

                    value = eligibility.get("value")
                    note = eligibility.get("note")

                    if value:
                        return (
                            f"The eligibility for "
                            f"{course_name} is:\n"
                            f"{value}"
                        )

                    if note:
                        return note

                return (
                    f"The eligibility for "
                    f"{course_name} is:\n"
                    f"{eligibility}"
                )

        # -------------------------------------------------
        # Study Material
        # -------------------------------------------------

        if intent == "study_material":

            study_material = course.get("study_material")

            if study_material:
                return study_material

        # -------------------------------------------------
        # Certificate
        # -------------------------------------------------

        if intent == "certificate_recognition":
            certificate = course.get("certificate")
            if certificate:
                return (
                    f"{certificate}\n\n"
                    "I don't have verified information about government recognition of the certificate, "
                    "so please confirm the government recognition details with the academy."
                )
            return (
                "I don't have verified information about government recognition of the certificate. "
                "Please confirm this directly with the academy."
            )

        if intent == "course_certificate":

            certificate = course.get("certificate")

            if certificate:
                return certificate

        # -------------------------------------------------
        # Course Modules
        # -------------------------------------------------

        if intent == "course_modules":

            # Different course files use either `modules` or `syllabus`.
            # Treat both as the same user-facing "syllabus/modules"
            # concept, but never invent syllabus content.
            modules = course.get("modules")
            syllabus = course.get("syllabus")
            curriculum = modules if modules else syllabus

            if isinstance(curriculum, dict):
                status = curriculum.get("status")
                note = curriculum.get("note")

                if note and status == "not_provided":
                    return note

                # Most course JSON files organize syllabus as
                # category -> list of topics. Flatten it into a
                # readable response without inventing content.
                explicit_content = (
                    curriculum.get("items")
                    or curriculum.get("topics")
                    or curriculum.get("content")
                )

                if explicit_content:
                    curriculum = explicit_content
                else:
                    flattened = []

                    for category, topics in curriculum.items():
                        if category in {"status", "note"}:
                            continue

                        if isinstance(topics, list):
                            flattened.append(
                                (category.replace("_", " ").title(), topics)
                            )
                        elif topics:
                            flattened.append(
                                (category.replace("_", " ").title(), [str(topics)])
                            )

                    curriculum = flattened

            if curriculum:

                if (
                    isinstance(curriculum, list)
                    and curriculum
                    and isinstance(curriculum[0], tuple)
                ):
                    sections = []

                    for category, topics in curriculum:
                        topic_text = "\n".join(
                            f"  • {topic}" for topic in topics
                        )
                        sections.append(
                            f"{category}:\n{topic_text}"
                        )

                    return (
                        f"Syllabus / modules covered in "
                        f"{course_name}:\n\n"
                        + "\n\n".join(sections)
                    )

                if isinstance(curriculum, list):

                    module_text = "\n".join(
                        f"• {module}"
                        for module in curriculum
                    )

                    return (
                        f"Syllabus / modules covered in "
                        f"{course_name}:\n\n"
                        f"{module_text}"
                    )

                return (
                    f"Syllabus / modules covered in "
                    f"{course_name}:\n\n"
                    f"{curriculum}"
                )

        # -------------------------------------------------
        # Learning Outcomes
        # -------------------------------------------------

        if intent == "learning_outcomes":

            outcomes = course.get(
                "learning_outcomes"
            )

            if outcomes:

                if isinstance(outcomes, list):

                    outcome_text = "\n".join(
                        f"• {outcome}"
                        for outcome in outcomes
                    )

                    return (
                        f"What you will learn in "
                        f"{course_name}:\n\n"
                        f"{outcome_text}"
                    )

                return (
                    f"What you will learn in "
                    f"{course_name}:\n\n"
                    f"{outcomes}"
                )

        # -------------------------------------------------
        # Beginner Friendly
        # -------------------------------------------------

        if intent == "beginner_friendly":

            recommended_for = course.get(
                "recommended_for",
                []
            )

            if isinstance(
                recommended_for,
                list
            ):

                beginner_found = any(
                    "beginner" in str(item).lower()
                    for item in recommended_for
                )

                if beginner_found:
                    return (
                        f"Yes. {course_name} is "
                        f"suitable for beginners."
                    )

            target_audience = course.get(
                "target_audience",
                []
            )

            if isinstance(
                target_audience,
                list
            ):

                beginner_found = any(
                    "beginner" in str(item).lower()
                    for item in target_audience
                )

                if beginner_found:
                    return (
                        f"Yes. {course_name} is "
                        f"suitable for beginners."
                    )

        # -------------------------------------------------
        # COURSE FAQ FALLBACK
        # -------------------------------------------------

        response = _build_faq_response(
            course_faq
        )

        if response:
            return response

        # -------------------------------------------------
        # ACADEMY FAQ FALLBACK
        # -------------------------------------------------

        response = _build_faq_response(
            academy_faq
        )

        if response:
            return response
        
        # -------------------------------------------------
        # COURSE INFORMATION UNAVAILABLE
        # -------------------------------------------------
        unavailable_messages = {
            "placement": f"I don't have placement information for {course_name} yet.",
            "demo_class": f"I don't have demo class information for {course_name} yet.",
            "admission": f"I don't have admission information specific to {course_name} yet.",
            "course_fees": f"I don't have fee information for {course_name} yet.",
            "course_duration": f"I don't have duration information for {course_name} yet.",
            "course_certificate": f"I don't have certificate information for {course_name} yet.",
            "certificate_recognition": (
                "I don't have verified information about government recognition of the certificate. "
                "Please confirm this directly with the academy."
            ),
            "placement_guarantee": (
                "Placement support may be available, but I don't have a verified guarantee of placement. "
                "Please confirm the current placement policy with the academy."
            ),
            "course_modules": (
                f"I don't have the detailed syllabus/module information "
                f"for {course_name} yet. Please contact the academy for the latest detailed syllabus."
            ),
            "prerequisites": f"I don't have prerequisite information for {course_name} yet.",
            "course_eligibility": f"I don't have eligibility information for {course_name} yet.",
        }

        return unavailable_messages.get(
            intent,
            f"I don't have information about {course_name} for this question yet."
        )

    # =====================================================
    # 2. NO COURSE DETECTED
    # =====================================================

    else:
        # -------------------------------------------------
        # Academy Contact Information
        # -------------------------------------------------

        if intent == "contact":
            return (
                "You can contact Shital Academy at:\n\n"
                "• 93 280 90 700\n"
                "• 97 14 14 77 00"
            )

        # -------------------------------------------------
        # Academy Branch Information
        # -------------------------------------------------

        if intent == "branches":
            if academy_faq and academy_faq.get("id") == "branch_near_sanskar_mandal":
                response = _build_faq_response(academy_faq)
                if response:
                    return response

            branches = []

            if isinstance(knowledge, dict):
                academy_data = knowledge.get("academy", {})

                if isinstance(academy_data, dict):
                    academy_info = academy_data.get("academy", {})

                    if isinstance(academy_info, dict):
                        branches = academy_info.get("branches", [])

            if branches:
                branch_text = []

                for branch in branches:
                    name = branch.get("name", "Branch")
                    address = branch.get("address", "")
                    city = branch.get("city", "")

                    location = ", ".join(
                        part for part in [address, city] if part
                    )

                    branch_text.append(
                        f"• {name}\n"
                        f"  {location}"
                    )

                return (
                    "Shital Academy Branches:\n\n"
                    + "\n\n".join(branch_text)
                )

            return "I don't have information about branches yet."
        # -------------------------------------------------
        # Academy Timing Information
        # -------------------------------------------------

        if intent == "academy_timings":

            if isinstance(knowledge, dict):

                academy_data = knowledge.get("academy", {})

                if isinstance(academy_data, dict):

                    academy_info = academy_data.get("academy", {})

                    if isinstance(academy_info, dict):

                        timings = academy_info.get(
                            "office_timings",
                            {}
                        )

                        if isinstance(timings, dict):

                            opening = timings.get("opening")
                            closing = timings.get("closing")

                            if opening and closing:
                                return (
                                    "Shital Academy is open from "
                                    f"{opening} to {closing}."
                                )

            return "I don't have academy timing information yet."      
                
        # -------------------------------------------------
        # Verified academy-level answers
        # -------------------------------------------------

        if intent == "payment_methods":
            return "We accept multiple payment methods, including Cash, UPI, and Online Bank Payment. Card payment availability can be confirmed with the academy."

        if intent == "fee_receipt":
            return "Yes. Students can obtain a payment receipt after successful fee payment."

        if intent == "internship":
            return "Internship opportunities vary depending on the course. Please contact the academy for current availability."

        if intent == "leave_policy":
            return "If you need leave, please inform your faculty or branch in advance whenever possible."

        if intent == "teaching_methodology":
            academy_info = (knowledge or {}).get("academy", {}).get("academy", {}) if isinstance(knowledge, dict) else {}
            return academy_info.get("teaching_methodology") or "The academy follows a personalized teaching approach with individual attention."

        if intent == "why_choose":
            academy_info = (knowledge or {}).get("academy", {}).get("academy", {}) if isinstance(knowledge, dict) else {}
            reasons = academy_info.get("why_choose_us", []) if isinstance(academy_info, dict) else []
            if reasons:
                return "Why choose Shital Academy:\n\n" + "\n".join(f"• {reason}" for reason in reasons)
            return "Shital Academy focuses on practical learning, experienced faculty, flexible batches, personalized guidance and career-oriented training."

        if intent == "admission_open":
            return "Yes, admissions are open. Availability depends on the course and batch."

        if intent == "join_anytime":
            return "Joining depends on batch availability."

        if intent == "batch_change":
            return "Batch changes depend on seat availability and academy policy."

        if intent == "practical_training":
            return "Yes. Most technical and professional courses focus on practical learning along with theory."

        # -------------------------------------------------
        # Generic course fee range
        # -------------------------------------------------

        if intent == "course_fees":
            return (
                "Course fees generally range from ₹6,500 to ₹25,000, depending on the course. "
                "Please contact the academy for the exact fee and current offers."
            )

        # -------------------------------------------------
        # Placement guarantee
        # -------------------------------------------------

        if intent == "placement_guarantee":
            return (
                "Placement support is available for the Diploma in Office Executive course and IT courses, "
                "but placement is not guaranteed. The level of assistance may vary depending on the course."
            )

        # -------------------------------------------------
        # Certificate recognition
        # -------------------------------------------------

        if intent == "certificate_recognition":
            return (
                "Shital Academy provides certificates after successful course completion. "
                "I don't have verified information that the certificate is government-recognized, "
                "so please confirm recognition details with the academy."
            )

        # -------------------------------------------------
        # Online / Offline Classes
        # -------------------------------------------------

        if intent == "online_classes":
            return (
                "Online batches may be available depending on the preferred course. "
                "Please contact the academy to check current online-batch availability."
            )

        # -------------------------------------------------
        # Academy FAQ
        # -------------------------------------------------

        response = _build_faq_response(
            academy_faq
        )

        if response:
            return response

    # =====================================================
    # 3. GENERAL KNOWLEDGE
    # =====================================================

    if knowledge:

        if isinstance(knowledge, str):
            return knowledge

        if isinstance(knowledge, dict):

            answer = knowledge.get("answer")

            if answer:
                return answer

    # =====================================================
    # 4. NOTHING FOUND
    # =====================================================

    if intent:
        return (
            f"I don't have information about "
            f"{intent.replace('_', ' ')} yet."
        )

    return "I'm sorry, I don't have that information yet."
