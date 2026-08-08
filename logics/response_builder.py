"""
response_builder.py

Builds final chatbot responses from structured knowledge.
"""


def build_response(
    intent=None,
    course=None,
    faq=None,
    knowledge=None,
):
    """
    Build the final response using FAQ, course,
    or general knowledge.
    """

    # =========================================================
    # 1. FAQ RESPONSE
    # =========================================================

    if faq:
        answer = faq.get("answer")

        if answer:
            response = answer

            follow_up = faq.get("follow_up", [])

            if follow_up:
                response += f"\n\n{follow_up[0]}"

            return response

    # =========================================================
    # 2. COURSE RESPONSE
    # =========================================================

    if course:

        course_name = course.get("name", "this course")

        # -----------------------------------------------------
        # Course Information
        # -----------------------------------------------------

        if intent == "course_info":

            description = course.get("description")

            if description:
                return (
                    f"{course_name}\n\n"
                    f"{description}"
                )

        # -----------------------------------------------------
        # Course Duration
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Course Fees
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Eligibility
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Certificate
        # -----------------------------------------------------

        if intent == "course_certificate":

            certificate = course.get("certificate")

            if certificate:
                return certificate

        # -----------------------------------------------------
        # Course Modules
        # -----------------------------------------------------

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

    # =========================================================
    # 3. GENERAL KNOWLEDGE
    # =========================================================

    if knowledge:

        if isinstance(knowledge, str):
            return knowledge

        if isinstance(knowledge, dict):

            answer = knowledge.get("answer")

            if answer:
                return answer

    # =========================================================
    # 4. NOTHING FOUND
    # =========================================================

    return None