class StudentManager:
    def __init__(self):
        """Initialize the student manager with an empty student list."""
        self.students = []

    def add_student(self, student):
        """Add a student to the manager."""
        if student not in self.students:
            self.students.append(student)
            return True
        return False

    def remove_student(self, student):
        """Remove a student from the manager."""
        if student in self.students:
            self.students.remove(student)
            return True
        return False

    def search_student(self, student):
        """Return True if the student exists."""
        return student in self.students

    def list_students(self):
        """Return a list of current students."""
        return list(self.students)


def main():
    manager = StudentManager()

    print("Adding students Alice, Bob, and Charlie...")
    manager.add_student("Alice")
    manager.add_student("Bob")
    manager.add_student("Charlie")

    print("Current students:", manager.list_students())
    print("Searching for Bob:", manager.search_student("Bob"))
    print("Removing Bob...")
    manager.remove_student("Bob")
    print("Searching for Bob after removal:", manager.search_student("Bob"))
    print("Final student list:", manager.list_students())


if __name__ == "__main__":
    main()
