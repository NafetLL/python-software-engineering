class Evaluation:

    def __init__(self, student, course):
        self.student = student
        self.course = course
        self.approval = []

    def add_note(self, note1, note2, note3):
        notes = [note1, note2, note3]
        average = round(sum(notes) / len(notes), 2)
        print(f"AVERAGE = {average:<14}")

        # Storing the result in a clean dictionary
        final = {"average": average, "approved": average >= 14}
        self.approval.append(final)

    def display(self):
        print("-" * 30)
        for record in self.approval:
            status = "Passed" if record["approved"]==True else "Failed"
            print(
                f"{self.student} in {self.course} has average {record['average']} ({status})"
            )
        print("-" * 30)


# --- TEST ---
system = Evaluation("Jesus", "Math")
system.add_note(19, 18, 20)
system.display()