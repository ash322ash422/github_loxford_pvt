import pytest

from employee import Employee, EmployeeManager


@pytest.fixture
def manager() -> EmployeeManager:
    m = EmployeeManager()
    m.add_employee(Employee(employee_id=1, name="Alice", department="HR", salary=60000))
    m.add_employee(Employee(employee_id=2, name="Bob", department="IT", salary=75000))
    return m


def test_add_employee_success(manager):
    employee = Employee(employee_id=3, name="Charlie", department="Sales", salary=50000)
    assert manager.add_employee(employee) is True
    assert manager.search_employee(3) == employee


def test_add_employee_duplicate_id(manager):
    duplicate = Employee(employee_id=1, name="Alice Jr.", department="HR", salary=65000)
    assert manager.add_employee(duplicate) is False


def test_remove_employee_success(manager):
    assert manager.remove_employee(1) is True
    assert manager.search_employee(1) is None


def test_remove_employee_not_found(manager):
    assert manager.remove_employee(99) is False


def test_search_employee_found(manager):
    employee = manager.search_employee(2)
    assert employee is not None
    assert employee.name == "Bob"


def test_search_employee_not_found(manager):
    assert manager.search_employee(99) is None


def test_display_employees(manager):
    employees = manager.display_employees()
    assert len(employees) == 2
    assert employees[0].employee_id == 1
    assert employees[1].employee_id == 2
