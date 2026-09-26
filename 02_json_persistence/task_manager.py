import json


class TaskManager:

    def __init__(self, module_name):
        self.module = module_name
        self.tasks = []

    def add_task(self, name, priority):
        # Structured dictionary with fixed keys
        task_item = {"name": name, "priority": priority}
        self.tasks.append(task_item)

    def sort_by_priority(self):
        # 1. Sort the entire list in-place by the "priority" key (highest to lowest)
        self.tasks.sort(key=lambda x: x["priority"], reverse=True)

        # 2. Display the sorted tasks
        print(f"\n📋 TASKS FOR MODULE: {self.module}")
        print("-" * 35)
        for i, task in enumerate(self.tasks, 1):
            print(f"{i}. {task['name']:<20} | Priority: {task['priority']}")
        print("-" * 35)

    def save_json(self, file_name):
        # Ensure filename ends with .json
        if not file_name.endswith(".json"):
            file_name += ".json"

        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(self.tasks, file, indent=4, ensure_ascii=False)
        print(f"✅ Saved correctly as '{file_name}'")


# --- TEST ---
proj = TaskManager("Software Development")
proj.add_task("Math", 4)
proj.add_task("Code", 5)
proj.add_task("English Practice", 3)

proj.sort_by_priority()
proj.save_json("tasks.json")