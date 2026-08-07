from logics.faq_matcher import search_faq

tests = [
    ("python", "What is the duration?"),
    ("python", "How much are the fees?"),
    ("python", "Do I get certificate?"),
    ("python", "Who can join?"),
    ("python", "Is placement available?"),
    (None, "How can I take admission?"),
    (None, "Can I pay in installments?"),
    (None, "Do you provide demo classes?"),
]

for course, question in tests:

    faq, score = search_faq(question, course)

    print()
    print(question)
    print(score)

    if faq:
        print(faq["question"])
        print(faq["answer"])
    else:
        print("No FAQ found.")