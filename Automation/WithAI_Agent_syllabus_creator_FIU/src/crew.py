import json
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task

from .config import settings
from .schemas import TeachingPackage
from .tools import (
    check_course_syllabus,
    retrieve_teaching_material,
    search_previous_lecture_notes,
)


def _text(result: Any) -> str:
    return getattr(result, "raw", str(result))


def _parse_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[1]
        candidate = candidate.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("The communications task JSON must be an object.")
    return parsed


def run_openai_crew(faculty_request: str) -> TeachingPackage:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for the OpenAI workflow. Use --demo for local mode."
        )

    llm = LLM(
        model=f"openai/{settings.openai_model}",
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    planner = Agent(
        role="Curriculum Planner",
        goal="Identify the next syllabus-aligned topic and measurable objectives.",
        backstory="You are a careful academic coordinator who never skips syllabus evidence.",
        tools=[check_course_syllabus],
        llm=llm,
        verbose=False,
    )
    researcher = Agent(
        role="Course Research Curator",
        goal="Find relevant teaching material and prior lecture context.",
        backstory="You curate authoritative, course-specific material and preserve continuity.",
        tools=[retrieve_teaching_material, search_previous_lecture_notes],
        llm=llm,
        verbose=False,
    )
    designer = Agent(
        role="Instructional Designer",
        goal="Create an engaging, practical class package from the evidence.",
        backstory="You design active-learning university lessons with assessable outcomes.",
        llm=llm,
        verbose=False,
    )
    communicator = Agent(
        role="Academic Communications Specialist",
        goal="Prepare a clear student announcement and LMS metadata.",
        backstory="You write concise, accessible communications for university students.",
        llm=llm,
        verbose=False,
    )

    plan = Task(
        description=(
            f"For course {settings.course_code} ({settings.course_name}), handle this request: "
            f"{faculty_request}. Read the syllabus. Identify the next topic and provide exactly "
            "three to five measurable learning objectives. Cite the syllabus evidence."
        ),
        expected_output="Next topic, evidence, and measurable objectives.",
        agent=planner,
    )
    research = Task(
        description=(
            "Using the planned topic, retrieve the most relevant teaching material and search "
            "previous lecture notes. Highlight continuity, misconceptions, and useful examples."
        ),
        expected_output="A concise evidence brief with material and prior-note findings.",
        agent=researcher,
        context=[plan],
    )
    design = Task(
        description=(
            "Create a complete lecture package for a 60-minute class: timed outline, explanation "
            "examples, in-class exercises with answers, and a five-question quiz with answer key. "
            "Use only the evidence supplied by the preceding tasks. Return valid JSON with exactly "
            "these string keys: lecture_outline, examples_and_exercises, and quiz."
        ),
        expected_output="Valid JSON with lecture_outline, examples_and_exercises, and quiz.",
        agent=designer,
        context=[plan, research],
    )
    communication = Task(
        description=(
            "Create a student-facing announcement and LMS metadata. Return valid JSON with keys "
            "announcement and lms_metadata. Metadata must include title, topic, estimated_minutes, "
            "and prerequisites."
        ),
        expected_output="Valid JSON containing announcement and LMS metadata.",
        agent=communicator,
        context=[plan, research, design],
    )

    Crew(
        agents=[planner, researcher, designer, communicator],
        tasks=[plan, research, design, communication],
        process=Process.sequential,
        verbose=False,
    ).kickoff()

    communication_text = _text(communication.output)
    try:
        design_data = _parse_json_object(_text(design.output))
        communication_data = _parse_json_object(communication_text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            "The content-generation tasks did not return valid JSON."
        ) from exc

    return TeachingPackage(
        course_code=settings.course_code,
        course_name=settings.course_name,
        faculty_request=faculty_request,
        next_topic=_text(plan.output),
        source_material=_text(research.output),
        previous_notes=_text(research.output),
        lecture_outline=design_data["lecture_outline"],
        examples_and_exercises=design_data["examples_and_exercises"],
        quiz=design_data["quiz"],
        announcement=communication_data["announcement"],
        lms_metadata=communication_data["lms_metadata"],
    )
