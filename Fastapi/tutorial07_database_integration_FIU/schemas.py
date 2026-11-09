from pydantic import BaseModel, ConfigDict, Field


class StudentInput(BaseModel):
    """Validate the JSON used to create or replace a student."""

    name: str = Field(min_length=1, max_length=80)
    age: int = Field(ge=16, le=100)
    course: str = Field(min_length=1, max_length=80)


class StudentResponse(StudentInput):
    """Read attributes from a SQLAlchemy object and return student JSON."""

    model_config = ConfigDict(from_attributes=True)
    id: int
