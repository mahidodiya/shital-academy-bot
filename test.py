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

    "Greeting": [
        "hello",
        "hi",
        "helo",
    ],

    "Academy Information": [
        "tell me about shital academy",
        "what is shital academy",
    ],

    "Location": [
        "where are you located",
        "where is your branch",
        "where are your branches",
        "what is your address",
        "what is your location",
        "how can i reach you",
    ],

    "Timings": [
        "what are your timings",
        "what are the batch timings",
    ],

    "Course Listing": [
        "what courses do you provide",
        "which courses do you offer",
    ],

    "Python Course Context": [
        "tell me about python",
        "what are the fees",
        "what is the duration",
        "is it beginner friendly",
        "what are the modules",
        "what are the eligibility requirements",
        "do i get a certificate",
    ],

    "Web Development Course Context": [
        "tell me about web development",
        "what are the fees",
        "what is the duration",
    ],

    "Academy Services": [
        "do you provide placement",
        "how can i contact",
        "what are the admission requirements",
    ],

    "Goodbye": [
        "bye",
        "byee",
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