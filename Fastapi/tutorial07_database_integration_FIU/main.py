from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Student
from schemas import StudentInput, StudentResponse


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create missing tables at startup and release connections at shutdown."""
    try:
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        engine.dispose()


app = FastAPI(title="Student CRUD API with SQLAlchemy", lifespan=lifespan)
DbSession = Annotated[Session, Depends(get_db)]


def get_student_or_404(student_id: int, db: Session) -> Student:
    """Look up a student by primary key."""
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@app.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(data: StudentInput, db: DbSession) -> Student:
    """Insert a student and return the database-generated ID."""
    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.get("/students", response_model=list[StudentResponse])
def list_students(db: DbSession) -> list[Student]:
    """Select all students in ID order."""
    statement = select(Student).order_by(Student.id)
    return list(db.scalars(statement))


@app.get("/students/{student_id}", response_model=StudentResponse)
def read_student(student_id: int, db: DbSession) -> Student:
    """Retrieve one student by ID."""
    return get_student_or_404(student_id, db)


@app.put("/students/{student_id}", response_model=StudentResponse)
def replace_student(student_id: int, data: StudentInput, db: DbSession) -> Student:
    """Replace all editable fields and commit the changes."""
    student = get_student_or_404(student_id, db)
    student.name = data.name
    student.age = data.age
    student.course = data.course
    db.commit()
    db.refresh(student)
    return student


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: DbSession) -> Response:
    """Delete the row and return an empty response."""
    student = get_student_or_404(student_id, db)
    db.delete(student)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
