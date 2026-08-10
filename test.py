from knowledge_loader import get_knowledge

knowledge = get_knowledge()

python = knowledge["courses"].get("python")

print("\n--- PYTHON COURSE ---")
print(python)