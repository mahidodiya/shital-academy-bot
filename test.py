from conversation import ConversationContext


context = ConversationContext()


print("Initial course:")
print(context.get_course())


print("\nSetting course to Python...")
context.set_course("python")


print("Current course:")
print(context.get_course())


print("\nSetting intent...")
context.set_intent("course_fees")


print("Current intent:")
print(context.get_intent())


print("\nClearing context...")
context.clear()


print("Course after clear:")
print(context.get_course())

print("Intent after clear:")
print(context.get_intent())