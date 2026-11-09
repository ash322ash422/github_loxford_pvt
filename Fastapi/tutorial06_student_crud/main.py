from itertools import count

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

app = FastAPI(title="Student CRUD API")


class StudentInput(BaseModel):
    """Validate the fields that clients send when creating or replacing a student."""

    name: str = Field(min_length=1, max_length=80)
    age: int = Field(ge=16, le=100)
    course: str = Field(min_length=1, max_length=80)


class Student(StudentInput):
    """Return the student fields along with the server-generated ID."""

    id: int


# The dictionary acts as a tiny database for this lesson.
students: dict[int, Student] = {
    1: Student(id=1, name="Asha Sharma", age=20, course="Python"),
    2: Student(id=2, name="Ravi Mehta", age=22, course="SQL"),
}
next_student_id = count(3)


def get_existing_student(student_id: int) -> Student:
    """Find a record by ID or return a 404 error to the client."""
    student = students.get(student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@app.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student(data: StudentInput) -> Student:
    """Generate an ID and store a new student."""
    student = Student(id=next(next_student_id), **data.model_dump())
    students[student.id] = student
    return student


@app.get("/students")
async def list_students() -> list[Student]:
    """Return all students currently in memory."""
    return list(students.values())


@app.get("/students/{student_id}")
async def read_student(student_id: int) -> Student:
    """Return one student by ID."""
    return get_existing_student(student_id)


@app.put("/students/{student_id}")
async def replace_student(student_id: int, data: StudentInput) -> Student:
    """Replace all editable fields while keeping the original ID."""
    get_existing_student(student_id)
    student = Student(id=student_id, **data.model_dump())
    students[student_id] = student
    return student


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: int) -> Response:
    """Remove an existing student and return an empty response."""
    get_existing_student(student_id)
    del students[student_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
