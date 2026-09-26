import requests
import json

class TechRadar:
    def __init__(self):
        self.main_data=[]

    def build_tech_radar(self, language, stars):
        url="https://api.github.com/search/repositories"
        params={
            "q": f"{language} stars:>{stars}", 
                "order": "stars",
                "sort": "desc",
                }

        try:
            response=requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data=response.json()
            repos=data["items"]
            print ("="*40)
            print (f" {'RANK':<10} | {'REPOSITORY':<15} | {'STARS':<10} | {'OWNER':<15} | {'URL':<10}")

            for rank, display in enumerate(repos, 1):
                project_name=display["name"]
                star_count=display["stargazers_count"]
                owner_username=display["owner"]["login"]
                repository_url=display["html_url"]
                position={
                    "rank": f"user_{rank}",
                    "name": owner_username,
                    "project": project_name,
                    "stars": star_count,
                    "url": repository_url
                    }
                self.main_data.append(position)
                print (f" {rank:<10} | {project_name:<15} | {star_count:<10} | {owner_username:<15} | {repository_url:<10}")

            print ("="*40)
        except requests.exceptions.RequestException as err:
            print (f"Program trapped error: {err}")

    def save(self, filename):
        if not self.main_data:
            print ("No data to save")
        else:
            if not filename.endswith(".json"):
                filename+=".json"
            with open (filename, "w", encoding="utf-8") as file:
                json.dump(self.main_data, file, indent=4, ensure_ascii=False)
                print(f"File saved correctly as '{filename}'")

test1=TechRadar()
test1.build_tech_radar("python", 100)
test1.save("techRadarTRYexcept")