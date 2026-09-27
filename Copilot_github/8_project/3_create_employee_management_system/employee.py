"""Employee management module.

This module provides a simple employee management system using classes.
It supports adding, removing, searching, and displaying employees.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Employee:
    """A simple employee record."""
    employee_id: int
    name: str
    department: str
    salary: float


class EmployeeManager:
    """Manage a collection of employees."""

    def __init__(self) -> None:
        """Initialize an empty employee manager."""
        self._employees: List[Employee] = []

    def add_employee(self, employee: Employee) -> bool:
        """Add a new employee.

        Returns True if the employee was added, False if an employee with the
        same ID already exists.
        """
        if self.search_employee(employee.employee_id) is not None:
            return False
        self._employees.append(employee)
        return True

    def remove_employee(self, employee_id: int) -> bool:
        """Remove an employee by ID.

        Returns True if removed successfully, False if the employee was not found.
        """
        employee = self.search_employee(employee_id)
        if employee is None:
            return False
        self._employees.remove(employee)
        return True

    def search_employee(self, employee_id: int) -> Optional[Employee]:
        """Find an employee by ID and return the record, or None if missing."""
        for employee in self._employees:
            if employee.employee_id == employee_id:
                return employee
        return None

    def display_employees(self) -> List[Employee]:
        """Return a list of all employees."""
        return list(self._employees)


def main() -> None:
    """Simple demo of the employee management workflow."""
    manager = EmployeeManager()
    manager.add_employee(Employee(employee_id=1, name="Alice", department="HR", salary=60000))
    manager.add_employee(Employee(employee_id=2, name="Bob", department="IT", salary=75000))

    print("All employees:")
    for emp in manager.display_employees():
        print(emp)

    print("\nSearching for employee ID 2:")
    print(manager.search_employee(2))

    print("\nRemoving employee ID 1:")
    print(manager.remove_employee(1))
    print("Remaining employees:")
    for emp in manager.display_employees():
        print(emp)


if __name__ == "__main__":
    main()
