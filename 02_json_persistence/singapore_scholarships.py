import json


class SingaporeScholarships:

    def __init__(self, university):
        self.university = university
        self.postulants = []

    def evaluate_candidate(self, name, english, code):
        total_score = round((english * 0.5) + (code * 0.5), 2)
        data = {
            "name": name,
            "english_score": english,
            "code_score": code,
            "total_score": total_score,
        }
        self.postulants.append(data)

    def sort_ranking(self):
        # Sort in-place by final score descending
        self.postulants.sort(key=lambda x: x["total_score"], reverse=True)

        print("\n" + "=" * 65)
        print(f" 🇸🇬 SINGAPORE SCHOLARSHIP RANKING: {self.university}")
        print("=" * 65)
        print(
            f"{'Rank':<5} | {'Candidate':<15} | {'English':<8} | {'Code':<8} | {'Total Score':<10}"
        )
        print("-" * 65)
        for i, p in enumerate(self.postulants, 1):
            print(
                f"{i:<5} | {p['name']:<15} | {p['english_score']:<8} | {p['code_score']:<8} | {p['total_score']:<10}"
            )
        print("=" * 65)

    def save(self, file_name):
        data_indexion = {
            "university_name": self.university,
            "postulants": self.postulants,
        }
        if not file_name.endswith(".json"):
            file_name += ".json"

        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data_indexion, file, indent=4, ensure_ascii=False)
        print(f"Successfully exported ranking to '{file_name}'")


# --- TEST ---
program = SingaporeScholarships("National University of Singapore (NUS)")
program.evaluate_candidate("Jesus", 20, 19)
program.evaluate_candidate("Alex", 18, 17)
program.evaluate_candidate("Chen", 19, 20)

program.sort_ranking()
program.save("2032_singapore_scholarships.json")