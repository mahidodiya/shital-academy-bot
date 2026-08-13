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
    # Course Modules
    # -----------------------------------------------------

    if intent == "course_modules":

        return bool(course.get("modules"))

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

                if fee_range:

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
        # Certificate
        # -------------------------------------------------

        if intent == "course_certificate":

            certificate = course.get("certificate")

            if certificate:
                return certificate

        # -------------------------------------------------
        # Course Modules
        # -------------------------------------------------

        if intent == "course_modules":

            modules = course.get("modules")

            if modules:

                if isinstance(modules, list):

                    module_text = "\n".join(
                        f"• {module}"
                        for module in modules
                    )

                    return (
                        f"Modules covered in "
                        f"{course_name}:\n\n"
                        f"{module_text}"
                    )

                return (
                    f"Modules covered in "
                    f"{course_name}:\n\n"
                    f"{modules}"
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
            "course_modules": f"I don't have module information for {course_name} yet.",
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
