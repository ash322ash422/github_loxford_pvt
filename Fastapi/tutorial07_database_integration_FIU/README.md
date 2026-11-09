# FastAPI classroom project — Database integration

**Class time** 35–45 minutes. Start with the familiar Student CRUD API, replace the in-memory dictionary with SQLite, and switch the same app to PostgreSQL.

## 1. Run with SQLite on Windows

Open PowerShell in this folder with Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs). With `DATABASE_URL` unset, startup creates `students.db` in the current directory and an empty `students` table. SQLite uses a local file, so it needs no separate database server.

## 2. Explain the layers

| File | What to show in class |
| --- | --- |
| `database.py` | The **engine** knows how to connect. `SessionLocal` creates a **session** for each request. FastAPI calls `get_db()` through `Depends` and closes the session after use. |
| `models.py` | SQLAlchemy maps the `Student` class to the `students` table. An object represents a row, and the integer primary key identifies it. |
| `schemas.py` | Pydantic validates incoming JSON. The response schema reads attributes from ORM objects via `from_attributes=True`. |
| `main.py` | Endpoints use the session for CRUD. Startup calls `create_all()` to create missing tables. Use migrations when an existing schema needs to change. |

Walk through a POST. FastAPI validates the JSON, the handler creates a `Student` object, `add()` registers it with the session, `commit()` saves the transaction, and `refresh()` reloads the stored row. FastAPI then serializes it using `StudentResponse`.

| Action | Endpoint | SQLAlchemy operation | Success |
| --- | --- | --- | --- |
| Create | `POST /students` | `add()` and `commit()` | `201` with the new student |
| Read all | `GET /students` | `scalars(select(Student))` | `200` with a list |
| Read one | `GET /students/{student_id}` | `get(Student, student_id)` | `200` with one student |
| Replace | `PUT /students/{student_id}` | Change attributes and `commit()` | `200` with the updated student |
| Delete | `DELETE /students/{student_id}` | `delete()` and `commit()` | `204` with an empty body |

A missing ID gives `404`. An invalid body or a non-integer ID gives `422`. PUT requires all editable fields.

## 3. Test CRUD and persistence

1. Use `GET /students` on a fresh database. Expect `[]`.
2. POST the JSON below to `/students`. Copy the returned ID and GET that record.
3. Stop Uvicorn with Ctrl+C and restart it from the same folder. GET the same ID again. The record survives because it was committed to the SQLite file.
4. PUT the full body with `course` changed to `"SQLAlchemy"`. Confirm the new value with a GET.
5. DELETE the student, then repeat the GET to see `404`. Try POST with `age` set to `10` to see `422`.

```json
{"name": "Neha Singh", "age": 21, "course": "FastAPI"}
```

## 4. Switch to PostgreSQL

Stop Uvicorn before switching. You can use an existing PostgreSQL server and an empty database that your user can create tables in. For a local class demo with Docker Desktop running, start PostgreSQL like this.

```powershell
docker run --name fastapi-student-postgres -e POSTGRES_USER=student_app -e POSTGRES_PASSWORD=student_demo_pw -e POSTGRES_DB=student_demo -p 127.0.0.1:5433:5432 -d postgres:17
docker exec fastapi-student-postgres pg_isready -U student_app -d student_demo
```

Run the readiness check until it reports that connections are accepted. Then install the PostgreSQL driver, set the URL, and run the app from the same PowerShell session.

```powershell
.\.venv\Scripts\python.exe -m pip install "psycopg[binary]>=3.2,<4"
$env:DATABASE_URL = 'postgresql+psycopg://student_app:student_demo_pw@127.0.0.1:5433/student_demo'
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Repeat the Swagger walkthrough. PostgreSQL starts with its own empty table. Changing the connection URL switches databases. To return to SQLite, stop Uvicorn, run `Remove-Item Env:DATABASE_URL`, and start it again.

## Exercise

Add `GET /students?course=FastAPI`. Accept an optional `course` query parameter and add `where(Student.course == course)` to the select statement when it is provided. Create two students with different courses and check the filtered result.

[SQLAlchemy ORM quick start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) · [PostgreSQL Psycopg dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg) · [FastAPI dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
