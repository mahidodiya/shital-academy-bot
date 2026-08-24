from chatbot import (
    process_message,
    create_session,
    get_lead,
    clear_context,
)


# =========================================================
# PRODUCTION CHATBOT REGRESSION TEST
# =========================================================

SCENARIOS = {

    # -----------------------------------------------------
    # TEST 001
    # -----------------------------------------------------
    "001 - Course Listing": [
        "What courses do you offer?"
    ],

}


# =========================================================
# TEST RUNNER
# =========================================================

def run_scenario(name, messages):

    print("\n" + "=" * 80)
    print(f"SCENARIO: {name}")
    print("=" * 80)

    session_id = create_session()

    try:

        for message in messages:

            result = process_message(
                message,
                session_id,
            )

            print("\n" + "-" * 80)
            print(f"USER: {message}")
            print(f"BOT : {result.get('response')}")
            print(f"INTENT : {result.get('intent')}")
            print(f"COURSE : {result.get('course')}")
            print(
                f"FROM CONTEXT : "
                f"{result.get('course_from_context')}"
            )
            print(
                f"TRIGGER LEAD : "
                f"{result.get('trigger_lead_form')}"
            )
            print(
                f"END SESSION : "
                f"{result.get('end_session')}"
            )

        lead = get_lead(session_id)

        print("\n" + "-" * 80)
        print(
            f"LEAD: question_count="
            f"{lead.get('question_count', 0)}, "
            f"captured="
            f"{lead.get('captured', False)}"
        )

    finally:

        clear_context(session_id)


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n" + "=" * 80)
    print("SHITAL ACADEMY CHATBOT - PRODUCTION REGRESSION TEST")
    print("=" * 80)

    for name, messages in SCENARIOS.items():

        run_scenario(
            name,
            messages,
        )


if __name__ == "__main__":
    main()