# Faculty Course Management Agent

This project uses **CrewAI** with an **OpenAI model** to turn a faculty request such as:

> Prepare next week's DBMS class.

into a reviewable teaching package containing:

- the next syllabus topic and learning objectives;
- relevant teaching material and previous lecture notes;
- a lecture outline;
- examples and exercises;
- a short quiz;
- a student announcement; and
- an LMS-ready package.

The workflow intentionally stops at a human approval gate. Nothing is published to the
LMS until the faculty member confirms the draft.

## Architecture

```text
Faculty goal
    |
    v
CrewAI Flow / sequential Crew
    |
    +--> Curriculum planner: syllabus and next topic
    +--> Research curator: teaching material and prior notes
    +--> Instructional designer: outline, examples, exercises, quiz
    +--> Communications specialist: announcement and LMS metadata
    |
    v
Draft teaching package
    |
    v
Human approval gate
    |
    +--> approve: publish through LMS adapter
    +--> reject: save draft only
```

## Setup

PowerShell:

```powershell
cd C:\Users\Ash\Desktop\educational\play_langchain_langgraph_llamaindex\automation_using_ai_agent
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY
```

The default model is `gpt-4o-mini`; change `OPENAI_MODEL` in `.env` if needed.

## Run

Run the real CrewAI/OpenAI workflow:

```powershell
..\.venv\Scripts\python.exe main.py "Prepare next week's DBMS class."
```

Run without an API key to inspect the complete local workflow and approval gate:

```powershell
..\.venv\Scripts\python.exe main.py "Prepare next week's DBMS class." --demo
```

The generated package is saved in `output/`. In a real deployment, replace
`LocalLMSClient` in `src/lms.py` with the institution's LMS API client. The adapter
interface keeps publishing separate from content generation and makes the approval
boundary explicit.

## Safety and operational notes

- Retrieval tools only read from the configured `data/` directory.
- The LMS adapter is a local, auditable stand-in and does not make network calls.
- The approval decision is collected after generation, not delegated to the model.
- Do not place API keys in source control; use `.env`.
