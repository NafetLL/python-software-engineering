import json
import os
import requests
from dotenv import load_dotenv

class Pillar5_6:
    def __init__(self, today):
        self.today = today
        self.main_data=[]

    def pillar5(self, stars):
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"stars:>{stars}"
        }

        try:
            response=requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data=response.json()

            print ("="*20)
            print (f"#1 Repository of <{self.today}>")
            print ("="*50)
            print (f"{'REPOSITORY':<15} | {'STARS':<10} | {'OWNER':<15} | {'DESCRIPTION':<10}")

            bestrep0=data["items"]
            for bestrep in bestrep0[:5]:
                repository_name = bestrep["name"]
                repo_stars = bestrep["stargazers_count"]
                repo_owner = bestrep["owner"]["login"]
                description = bestrep["description"]

                clean_repo_data={
                        "date": self.today,
                        "user": repo_owner,
                        "repository": repository_name,
                        "stars": repo_stars,
                        "description": description
                    }
                self.main_data.append(clean_repo_data)
                print (f"{repository_name:<15} | {repo_stars:<10} | {repo_owner:<15} | {description:<10}")
            print ("="*50)

        except requests.exceptions.RequestException as err:
            print (f"Error detected correctly: '{err}'")

    def pillar6(self, query):

        load_dotenv()
        api_key=os.getenv("GEMINI_API_KEY")
        if not api_key:
            print ("No API KEY to use")
            exit()

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key
            }

        prompt = (f"Using this data: [{self.main_data}] respond this query: [{query}]")
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        print ("The request is being sent in HTTP POST ...")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            ai_data = response.json()
            ai_response = ai_data["candidates"][0]["content"]["parts"][0]["text"]
            ai_localsave = {"AI_response": ai_response}
            self.main_data.append(ai_localsave)

            print ("AI response:")
            print ("="*60)
            print (ai_response.strip())
            print ("="*60)

        except requests.exceptions.RequestException as errAi:
            print (f"Error catched correctly: '{errAi}'")

    def save_file(self, file_name):
        if not self.main_data:
            print ("No data to save")
            exit()

        if not file_name.endswith(".json"):
            file_name+=".json"
        with open (file_name, "w", encoding="utf-8") as file:
            json.dump(self.main_data, file, indent=4, ensure_ascii=False)
            print (f"Data correctly saved as '{file_name}'")

test1=Pillar5_6("06/10/26")
test1.pillar5(1000)
test1.pillar6("About what it is the selected repository and why it is important for software engineering")
test1.save_file("Pillar1-6")