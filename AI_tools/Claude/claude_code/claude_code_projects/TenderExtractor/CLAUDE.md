# Project: PDF Keyword Extraction Tool

## Project Architecture & Tech Stack
- **Runtime Environment:** Python 3.11+ on Windows 11 Desktop
- **Code Execution:** Run local scripts directly in the integrated workspace terminal.

## Core Coding Conventions
- **Code Style:** Strict adherence to PEP 8 style standards.
- **Modularity:** Always write code inside clear, functional blocks or standalone modules.
- **Type Hinting:** Mandatory parameter and return type annotations on all function signatures.
- **Error Handling:** Explicitly trap system faults using clean `try-except` blocks (e.g., `FileNotFoundError`). Do not catch blind `Exception` wrappers unless logging.
- **Console Output:** Never slice dictionary data frames structurally when printing. Loop over dictionary items explicitly (`.items()`) to print full file contents to the screen.

## Project Layout
- `backend/` — the pipeline, services, CLI (`main.py`), tests, dev scripts, and all runtime data folders (`data_uploads/`, `cache/`, `output/`, `logs/`).
- `frontend/` — `streamlit_app.py`, the browser UI. Talks to the backend's REST API over HTTP only (JWT login, no direct imports of backend code), so it can run against a backend on a different host/process entirely.

## Development
- **Run the full extraction app:**  `python backend/main.py`
- **Run the REST API:**  `cd backend && uvicorn app.api.main:app --reload`
- **Run the browser UI (needs the API running first):**  `streamlit run frontend/streamlit_app.py`
- **Run tests:**  `cd backend && pytest tests/`
