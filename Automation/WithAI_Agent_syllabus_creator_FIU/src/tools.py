from pathlib import Path

from crewai.tools import tool

from .config import settings


def _read_data_file(filename: str) -> str:
    path = settings.data_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"Course data file not found: {path}")
    return path.read_text(encoding="utf-8")


@tool("check_course_syllabus")
def check_course_syllabus() -> str:
    """Read the current course syllabus and completed-topic information."""
    return _read_data_file("syllabus.md")


@tool("retrieve_teaching_material")
def retrieve_teaching_material(topic: str) -> str:
    """Retrieve local teaching material relevant to a requested course topic."""
    catalogue = _read_data_file("teaching_materials.md")
    return f"Requested topic: {topic}\n\n{catalogue}"


@tool("search_previous_lecture_notes")
def search_previous_lecture_notes(topic: str) -> str:
    """Search previous lecture notes for context and student learning gaps."""
    notes = _read_data_file("previous_lecture_notes.md")
    return f"Search focus: {topic}\n\n{notes}"
