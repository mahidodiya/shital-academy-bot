"""
knowledge_loader.py

Loads all knowledge base JSON files into memory.
The knowledge is loaded once at application startup.
"""

from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


def _load_json(file_path: Path):
    """Load a JSON file safely."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Knowledge Loader] Failed to load {file_path.name}: {e}")
        return None


def _load_folder(folder: Path):
    """Load every JSON file inside a folder."""
    data = {}

    if not folder.exists():
        return data

    for file in sorted(folder.glob("*.json")):
        data[file.stem] = _load_json(file)

    return data


def load_knowledge():
    """Load the complete knowledge base."""

    knowledge = {
        "academy": _load_folder(KNOWLEDGE_DIR / "academy"),
        "courses": _load_folder(KNOWLEDGE_DIR / "courses"),
        "common": _load_folder(KNOWLEDGE_DIR / "common")
    }

    return knowledge


# Load once when imported
KNOWLEDGE = load_knowledge()


def get_knowledge():
    """Return the complete knowledge base."""
    return KNOWLEDGE


def get_course(course_id: str):
    """Return a single course by id."""
    return KNOWLEDGE["courses"].get(course_id)


def get_academy():
    return KNOWLEDGE["academy"]


def get_common():
    return KNOWLEDGE["common"]


def get_intents():
    return KNOWLEDGE["common"].get("intents", {})


def get_synonyms():
    return KNOWLEDGE["common"].get("synonyms", {})


def get_greetings():
    return KNOWLEDGE["common"].get("greetings", {})