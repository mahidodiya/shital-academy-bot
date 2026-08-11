from knowledge_loader import get_knowledge

knowledge = get_knowledge()

python_course = knowledge["courses"].get("python")

print("\nPYTHON COURSE:")
print(python_course)

print("\nPYTHON FAQs:")
for faq in python_course.get("faqs", []):
    print(faq)