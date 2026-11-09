from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Student(Base):
    """Map Student objects to rows in the students table."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    age: Mapped[int]
    course: Mapped[str] = mapped_column(String(80))
