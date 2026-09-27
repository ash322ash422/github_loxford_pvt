from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TeachingPackage:
    course_code: str
    course_name: str
    faculty_request: str
    next_topic: str = ""
    learning_objectives: list[str] = field(default_factory=list)
    source_material: str = ""
    previous_notes: str = ""
    lecture_outline: str = ""
    examples_and_exercises: str = ""
    quiz: str = ""
    announcement: str = ""
    lms_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
