import argparse
import json
from pathlib import Path

from src.config import settings
from src.crew import run_openai_crew
from src.lms import LocalLMSClient
from src.schemas import TeachingPackage


def build_demo_package(request: str) -> TeachingPackage:
    return TeachingPackage(
        course_code=settings.course_code,
        course_name=settings.course_name,
        faculty_request=request,
        next_topic="Functional dependencies and normalization",
        learning_objectives=[
            "Compute attribute closure for a set of functional dependencies.",
            "Identify candidate keys and distinguish prime attributes.",
            "Recognize partial and transitive dependencies.",
            "Decompose a relation into 3NF while preserving meaning.",
        ],
        source_material="Armstrong's axioms; attribute closure; candidate keys; 1NF, 2NF, 3NF, BCNF; lossless join.",
        previous_notes="The last SQL lesson used joins. Students need a bridge from repeated joined data to normalization.",
        lecture_outline="0-10 min: retrieval and join-to-redundancy hook; 10-25 min: functional dependencies; 25-40 min: closure and keys; 40-55 min: normalization decomposition; 55-60 min: exit ticket.",
        examples_and_exercises="Use STUDENT_COURSE(StudentID, CourseID, StudentName, CourseName, Grade). Ask students to identify dependencies, candidate key, and a 3NF decomposition. Discuss answers in pairs.",
        quiz="1. Define a functional dependency. 2. Compute closure of {StudentID}. 3. Identify a partial dependency. 4. Why decompose? 5. State one 3NF criterion. Answer key included for faculty review.",
        announcement="Next week we move from SQL joins to functional dependencies and normalization. Bring your SQL notes; we will use a student-course example to find redundancy and decompose it.",
        lms_metadata={
            "title": "Functional Dependencies and Normalization",
            "topic": "Functional dependencies and normalization",
            "estimated_minutes": 60,
            "prerequisites": ["SQL joins", "primary and candidate keys"],
        },
    )


def save_draft(package: TeachingPackage) -> Path:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.output_dir / "draft_teaching_package.json"
    destination.write_text(
        json.dumps(package.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a faculty course package.")
    parser.add_argument("request", nargs="?", default="Prepare next week's DBMS class.")
    parser.add_argument("--demo", action="store_true", help="Run without calling OpenAI.")
    args = parser.parse_args()

    package = build_demo_package(args.request) if args.demo else run_openai_crew(args.request)
    draft_path = save_draft(package)
    print(f"\nDraft created at: {draft_path}")
    print(f"Next topic: {package.next_topic}")
    print(f"Announcement: {package.announcement}\n")

    approval = input("Approve and publish this package to the LMS? [y/N]: ").strip().lower()
    if approval not in {"y", "yes"}:
        print(f"Not published. The draft remains at {draft_path}.")
        return

    published_path = LocalLMSClient(settings.output_dir / "lms").publish(package.to_dict())
    print(f"Approved and published to LMS adapter: {published_path}")


if __name__ == "__main__":
    main()
