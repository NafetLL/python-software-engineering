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

        # Sanitize description to prevent null values in Protobuf payload
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
    """Orchestrates tool registration, function call interception, and multi-turn state sync via a while loop."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }
        self.execution_history = []  # Local memory buffer for JSON report export

    def _get_tool_declarations(self) -> list:
        """Constructs OpenAPI / Protobuf-compliant JSON Schema sent in payload['tools']."""
        # Standardized camelCase 'functionDeclarations' for REST API Protobuf parser

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
        # 1. Initialize conversational state array
        history = [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ]
        self.execution_history = [{"prompt": user_prompt}]

        print(f"💬 Initial Prompt: '{user_prompt}'\n")

        # 2. Dynamic Agent Decision Loop
        while True:
            payload = {
                "contents": history,
                "tools": self._get_tool_declarations()
            }

            try:
                response = requests.post(self.url, headers=self.headers, json=payload, timeout=70)
                response.raise_for_status()
                data = response.json()

                # Preserve full model content object returned from API
                model_content = data["candidates"][0]["content"]
                part = model_content["parts"][0]

                # Append model output turn to conversation history
                history.append(model_content)

                # 3. Branching Logic: Intercept Function Call vs. Display Final Text
                if "functionCall" in part:
                    func_name = part["functionCall"]["name"]
                    func_args = part["functionCall"]["args"]

                    if func_name == "get_github_top_repo":
                        lang = func_args.get("language", "python")
                        print(f"🤖 Agent Decision: Call tool '{func_name}' with language='{lang}'")
                        
                        tool_result = get_github_top_repo(lang)
                        print(f"⚙️ Tool Output Retrieved: {tool_result}\n")

                        # Append tool execution turn to conversation history
                        history.append({
                            "role": "user",
                            "parts": [{
                                "functionResponse": {
                                    "name": func_name,
                                    "response": {"output": tool_result}
                                }
                            }]
                        })

                        self.execution_history.append({
                            "tool_executed": func_name,
                            "tool_output": tool_result
                        })
                        # Loop automatically continues back to the top of 'while True'
                else:
                    # Final synthesis reached -> Print assessment and break out of loop
                    final_text = part["text"].strip()
                    print("🤖 AGENT EXECUTIVE ASSESSMENT:")
                    print("=" * 65)
                    print(final_text)
                    print("=" * 65)

                    self.execution_history.append({"agent_assessment": final_text})
                    break  # <--- Cleanly terminates the while True loop

            except requests.exceptions.RequestException as err:
                print(f"❌ Agent Loop Network Failure: {err}")
                break  # <--- Safety break on network failure

    def save_agent_report(self, file_path: str) -> None:
        """Exports the complete agent execution loop to disk as structured JSON."""

        has_assessment = any("agent_assessment" in record for record in self.execution_history)

        if not has_assessment:
            print("⚠️ No completed agent assessment available to save.")
            return
        
        if not file_path.endswith(".json"):
            file_path += ".json"

        # Defensive path safety: create directory if it doesn't exist
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(self.execution_history, file, indent=4, ensure_ascii=False)
            print(f"\n💾 Agent execution log saved cleanly to '{file_path}'")


if __name__ == "__main__":
    if api_key:
        agent = AutonomousAgent(api_key=api_key)
        agent.run("What is currently the most popular Python repository on Github and why is it important?")
        agent.save_agent_report("03_web_apis/autonomous_agent_report.json")