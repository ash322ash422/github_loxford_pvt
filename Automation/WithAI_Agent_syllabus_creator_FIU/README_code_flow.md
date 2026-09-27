# Code Flow

## Workflow

1. The faculty submits a request, such as `Prepare next week's DBMS class.`
2. [`main.py`](./main.py) reads the request and selects either:
   - demo mode, which uses local sample content; or
   - the CrewAI/OpenAI workflow.
3. [`src/crew.py`](./src/crew.py) runs four sequential CrewAI agents:
   - **Curriculum Planner** checks the syllabus and identifies the next topic.
   - **Course Research Curator** retrieves teaching material and previous lecture notes.
   - **Instructional Designer** creates the lecture outline, exercises, and quiz.
   - **Academic Communications Specialist** creates the announcement and LMS metadata.
4. The generated content is assembled into a [`TeachingPackage`](./src/schemas.py).
5. The draft is saved to `output/draft_teaching_package.json`.
6. The program asks the faculty member for approval.
7. If approved, [`src/lms.py`](./src/lms.py) publishes the package through the local LMS adapter.
8. If rejected, the draft remains available but nothing is published.

## Directory structure

```text
automation_using_ai_agent/
├── data/       Course knowledge used by retrieval tools
├── output/     Generated drafts and LMS output
├── src/        Application code
└── tests/      Automated tests
```

## File purposes

### Project files

- [`README.md`](./README.md): Setup, run commands, architecture overview, and operational notes.
- [`code_flow.md`](./code_flow.md): This workflow and file reference.
- [`requirements.txt`](./requirements.txt): CrewAI and environment configuration dependencies.
- [`.env.example`](./.env.example): Template for the OpenAI key, model, course settings, and output location.
- [`main.py`](./main.py): Command-line entry point, demo workflow, draft saving, approval prompt, and publish orchestration.

### `src/`

- [`src/config.py`](./src/config.py): Loads environment variables and defines application settings.
- [`src/schemas.py`](./src/schemas.py): Defines the `TeachingPackage` data structure used throughout the workflow.
- [`src/tools.py`](./src/tools.py): CrewAI retrieval tools for reading the syllabus, teaching materials, and previous notes.
- [`src/crew.py`](./src/crew.py): Defines the CrewAI agents and sequential tasks, configures the OpenAI LLM, and assembles the result.
- [`src/lms.py`](./src/lms.py): Contains the local LMS adapter. A production LMS API client can replace this implementation.
- [`src/__init__.py`](./src/__init__.py): Marks `src` as a Python package.

### `data/`

- [`data/syllabus.md`](./data/syllabus.md): Course topics and completed-topic information.
- [`data/teaching_materials.md`](./data/teaching_materials.md): Topic-specific teaching material and activity suggestions.
- [`data/previous_lecture_notes.md`](./data/previous_lecture_notes.md): Prior lecture context and observed student learning gaps.

### `tests/`

- [`tests/test_local_workflow.py`](./tests/test_local_workflow.py): Verifies generated demo content and LMS adapter behavior.

## Important design boundary

Content generation is automated, but publication is not. The LMS adapter is called only
after explicit faculty approval. This keeps the workflow useful for automation while
ensuring that a human reviews the generated class material before students see it.
