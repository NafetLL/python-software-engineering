import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def get_github_top_repo(language: str) -> dict:
    """Fetches the #1 top starred GitHub repository for a specified language."""
    url = "https://api.github.com/search/repositories"
    params = {"q": f"language:{language} stars:>50000", "sort": "stars", "order": "desc"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        top_repo = data["items"][0]
        desc = top_repo.get("description") or "No description provided"

        return {
            "repository": top_repo["name"],
            "owner": top_repo["owner"]["login"],
            "stars": top_repo["stargazers_count"],
            "description": desc
        }
    
    except Exception as err:
        return {"error": f"Failed to fetch GitHub data: {err}"}

class AutonomousAgent:
    """Orchestrates tool registration, function call interception, and multi-turn state sync."""
#Phase1
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }
        self.execution_history = []

    def _get_tool_declarations(self) -> list:
        return [{
            "functionDeclarations": [{
                "name": "get_github_top_repo",
                "description": "Fetches real-time data about the most starred GitHub repository for a programming language.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "language": {
                            "type": "STRING",
                            "description": "The programming language to search for (e.g., 'python', 'cpp')."
                        }
                    },
                    "required": ["language"]
                }
            }]
        }]

    def run(self, user_prompt: str) -> None:
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "tools": self._get_tool_declarations()
        }

        try:
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Preserve full model content object from Phase 1
            model_content = data["candidates"][0]["content"]
            part = model_content["parts"][0]

            if "functionCall" in part:
                func_name = part["functionCall"]["name"]
                func_args = part["functionCall"]["args"]

                if func_name == "get_github_top_repo":
                    lang = func_args.get("language", "python")
                    tool_result = get_github_top_repo(lang)

                    # Hand off to Phase 2
                    self._send_tool_response(user_prompt, model_content, func_name, tool_result)
            else:
                print(part["text"].strip())

        except requests.exceptions.RequestException as err:
            print(f"❌ Agent Network Failure: {err}")

#Phase2
    def _send_tool_response(self, prompt: str, model_content: dict, func_name: str, result: dict) -> None:
        followup_payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]},
                model_content,
                {
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": func_name,
                            "response": {"output": result}
                        }
                    }]
                }
            ],
            "tools": self._get_tool_declarations()
        }

        try:
            response = requests.post(self.url, headers=self.headers, json=followup_payload, timeout=30)
            response.raise_for_status()
            final_data = response.json()
            final_text = final_data["candidates"][0]["content"]["parts"][0]["text"].strip()

            print("\n AGENT EXECUTIVE ASSESSMENT:")
            print("=" * 65)
            print(final_text)
            print("=" * 65)

            self.execution_history = [
                {"prompt": prompt},
                {"tool_executed": func_name, "tool_output": result},
                {"agent_assessment": final_text}
            ]

        except requests.exceptions.RequestException as err:
            print(f"❌ Phase 2 Network Failure: {err}")

    def save_agent_report(self, file_path: str) -> None:
        """Exports the complete agent execution loop to disk as structured JSON."""
        if not self.execution_history:
            print("No execution history available to save.")
            return

        if not file_path.endswith(".json"):
            file_path += ".json"

        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(self.execution_history, file, indent=4, ensure_ascii=False)
            print(f"\n Agent execution log saved cleanly to '{file_path}'")


if __name__ == "__main__":
    if api_key:
        agent = AutonomousAgent(api_key=api_key)
        agent.run("What is currently the most popular Python repository on Github and why is it important?")
        agent.save_agent_report("03_web_apis/autonomous_agent_report.json")