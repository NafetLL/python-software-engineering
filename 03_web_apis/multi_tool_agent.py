import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


# =====================================================================
# TOOL 1: External REST API Fetcher (GitHub Data)
# =====================================================================
def get_github_top_repo(language: str) -> dict:
    """Fetches the #1 top starred GitHub repository for a specified language."""
    url = "https://api.github.com/search/repositories"
    params = {"q": f"language:{language} stars:>50000", "sort": "stars", "order": "desc"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            return {"error": f"No GitHub repositories found matching language:{language}"}
        top_repo = items[0]
        desc = top_repo.get("description") or "No description provided"

        return {
            "repository": top_repo["name"],
            "owner": top_repo["owner"]["login"],
            "stars": top_repo["stargazers_count"],
            "description": desc
        }
    except Exception as err:
        return {"error": f"Failed to fetch GitHub data: {err}"}


# =====================================================================
# TOOL 2: Local File System Mutator (Executive Summary Saver)
# =====================================================================
def save_executive_summary(filename: str, content_text: str) -> dict:
    """Writes a formatted text executive summary report directly to disk inside a reports/ folder."""
    try:
        folder_path = "reports"
        os.makedirs(folder_path, exist_ok=True)

        if not filename.endswith(".txt"):
            filename += ".txt"

        full_path = os.path.join(folder_path, filename)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content_text)

        print(f"📁 Local Disk Tool Executed: Summary successfully written to '{full_path}'")

        return {
            "status": "success",
            "file_saved": full_path,
            "bytes_written": len(content_text)
        }
    except Exception as err:
        return {"error": f"Failed to write executive summary to disk: {err}"}


# =====================================================================
# ORCHESTRATOR CLASS: Resilient Multi-Tool State Machine
# =====================================================================

class MultiToolAutonomousAgent:
    """Orchestrates multi-tool registration, state loops, dynamic QoS telemetry, and cycle-window 429 backoff."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }
        self.execution_history = []
        
        # Telemetry & QoS Tracking Metrics
        self.total_post_calls = 0
        self.successful_post_calls = 0
        self.cycle_429_count = 0
        self.error_breakdown = {"429": 0, "503": 0, "other": 0}

    def _get_tool_declarations(self) -> list:
        """Registers tool declarations inside the OpenAPI schema payload."""
        return [{
            "functionDeclarations": [
                {
                    "name": "get_github_top_repo",
                    "description": "Fetches real-time data about the most starred GitHub repository for a programming language.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "language": {
                                "type": "STRING",
                                "description": "The programming language to search for (e.g., 'python', 'cpp', 'rust')."
                            }
                        },
                        "required": ["language"]
                    }
                },
                {
                    "name": "save_executive_summary",
                    "description": "Saves an executive summary text report to disk inside the reports/ directory.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "filename": {
                                "type": "STRING",
                                "description": "The target text filename to save (e.g., 'cpp_overview.txt')."
                            },
                            "content_text": {
                                "type": "STRING",
                                "description": "The full body of the executive summary text to write to the file."
                            }
                        },
                        "required": ["filename", "content_text"]
                    }
                }
            ]
        }]

    def _post_with_retry(self, payload: dict, max_retries: int | None = 100, max_backoff: int = 60) -> dict:
        """Executes HTTP POST requests with 10-attempt cycle resets, QoS error logging, and heavy 429 backoff."""
        attempt = 1

        while True:
            if max_retries is not None and attempt > max_retries:
                raise RuntimeError(f"❌ Exceeded absolute retry budget of {max_retries} attempts for this turn.")

            # Calculate 1-to-10 step position within the current cycle
            cycle_step = ((attempt - 1) % 10) + 1

            # Reset cycle-specific 429 counter at the start of every new 10-attempt cycle
            if cycle_step == 1:
                self.cycle_429_count = 0

            standard_wait = min(2 ** cycle_step, max_backoff)
            self.total_post_calls += 1

            try:
                response = requests.post(self.url, headers=self.headers, json=payload, timeout=130)
                response.raise_for_status()

                # HTTP 200 OK -> Record success & reset cycle 429 counter
                self.successful_post_calls += 1
                self.cycle_429_count = 0
                return response.json()

            except requests.exceptions.HTTPError as err:
                status_code = err.response.status_code if err.response is not None else 0

                # 1. Handle Rate Limits (HTTP 429)
                if status_code == 429:
                    self.cycle_429_count += 1
                    self.error_breakdown["429"] += 1

                    # Heavy Scalar Escalation if more than 5 rate limits occur in the current 10-attempt cycle
                    if self.cycle_429_count > 5:
                        tier = self.cycle_429_count - 5
                        wait_time = min(600 * (3 ** tier), 10800)  # Capped at 3 hours (10,800s)
                        print(f"🛑 Heavy Rate Limit (429)! Cycle 429 Count: {self.cycle_429_count}/10. "
                              f"Escalating wait to {wait_time // 60}m (Attempt #{cycle_step} | Total Calls: {self.total_post_calls})...")
                    else:
                        wait_time = standard_wait
                        print(f"⚠️ Network Status 429. Retrying in {wait_time}s (Turn Attempt #{cycle_step} | Total Calls: {self.total_post_calls})...")

                    time.sleep(wait_time)
                    attempt += 1

                # 2. Handle Transient Server Errors (HTTP 503, 502, 504)
                elif status_code in [503, 502, 504]:
                    self.error_breakdown["503"] += 1

                    if attempt % 10 == 0:
                        print(f"🔄 Milestone: 10 turn attempts completed (Status {status_code}). Resetting wait timer back to 2s for Cycle {attempt // 10 + 1}...")

                    print(f"⚠️ Network Status {status_code}. Retrying in {standard_wait}s (Turn Attempt #{cycle_step} | Total Calls: {self.total_post_calls})...")
                    time.sleep(standard_wait)
                    attempt += 1

                # 3. Fail Fast on Unrecoverable Errors (HTTP 400, 401, 403, 501)
                else:
                    self.error_breakdown["other"] += 1
                    raise err

            except requests.exceptions.RequestException as err:
                self.error_breakdown["other"] += 1
                print(f"⚠️ Network Exception: {err}. Retrying in {standard_wait}s (Turn Attempt #{cycle_step} | Total Calls: {self.total_post_calls})...")
                time.sleep(standard_wait)
                attempt += 1

    def run(self, user_prompt: str) -> None:
        history = [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ]
        self.execution_history = [{"prompt": user_prompt}]

        # Reset telemetry metrics for new execution run
        self.total_post_calls = 0
        self.successful_post_calls = 0
        self.error_breakdown = {"429": 0, "503": 0, "other": 0}

        print(f"💬 Initial Multi-Tool Prompt: '{user_prompt}'\n")

        while True:
            payload = {
                "contents": history,
                "tools": self._get_tool_declarations()
            }

            try:
                data = self._post_with_retry(payload, max_retries=100)

                model_content = data["candidates"][0]["content"]
                history.append(model_content)

                tool_response_parts = []
                turn_text_blocks = []

                # 1. Inspect EVERY part in the model's response turn
                for part in model_content.get("parts", []):
                    if "text" in part:
                        clean_text = part["text"].strip()
                        if clean_text:
                            turn_text_blocks.append(clean_text)

                    elif "functionCall" in part:
                        func_name = part["functionCall"]["name"]
                        func_args = part["functionCall"].get("args", {})

                        if func_name == "get_github_top_repo":
                            lang = func_args.get("language", "cpp")
                            print(f"🤖 Agent Step: Calling tool '{func_name}' for language='{lang}'")
                            tool_result = get_github_top_repo(lang)
                            print(f"⚙️ GitHub Tool Output: {tool_result}\n")

                        elif func_name == "save_executive_summary":
                            fname = func_args.get("filename", "summary.txt")
                            content = func_args.get("content_text", "No content provided.")
                            print(f"🤖 Agent Step: Calling tool '{func_name}' for file='{fname}'")
                            tool_result = save_executive_summary(fname, content)
                            print(f"⚙️ Disk Saver Tool Output: {tool_result}\n")

                        else:
                            print(f"⚠️ Agent requested unknown tool: {func_name}")
                            tool_result = {"error": f"Tool '{func_name}' is not registered."}

                        # Collect each tool result for this turn
                        tool_response_parts.append({
                            "functionResponse": {
                                "name": func_name,
                                "response": {"output": tool_result}
                            }
                        })

                        self.execution_history.append({
                            "tool_executed": func_name,
                            "tool_output": tool_result
                        })

                # 2. State Transition Decision (evaluated AFTER inspecting all parts)
                if tool_response_parts:
                    # If the model emitted reasoning text alongside a tool call, log it
                    if turn_text_blocks:
                        print(f"💭 Agent Intermediate Thought: {' '.join(turn_text_blocks)}\n")

                    # Send ALL tool outputs back in a single user turn and continue loop
                    history.append({
                        "role": "user",
                        "parts": tool_response_parts
                    })
                else:
                    # Zero tool calls in any part -> Final assessment reached
                    final_text = "\n".join(turn_text_blocks)
                    print("🤖 AGENT FINAL EXECUTIVE ASSESSMENT:")
                    print("=" * 65)
                    print(final_text)
                    print("=" * 65)

                    self.execution_history.append({"agent_assessment": final_text})
                    break

            except Exception as err:
                print(f"❌ Unrecoverable Agent Network Failure: {err}")
                break

    def save_agent_report(self, file_path: str) -> None:
        """Exports execution history and QoS telemetry (health percentage & error breakdown) to disk as JSON."""
        has_assessment = any("agent_assessment" in record for record in self.execution_history)

        if not has_assessment:
            print("⚠️ No completed agent assessment available to save.")
            return

        if not file_path.endswith(".json"):
            file_path += ".json"

        # Calculate Quality of Service (QoS) Health Percentage
        health_pct = (
            round((self.successful_post_calls / self.total_post_calls) * 100, 2)
            if self.total_post_calls > 0
            else 0.0
        )

        # Attach complete QoS Telemetry dictionary to report
        if not any("telemetry" in record for record in self.execution_history):
            self.execution_history.append({
                "telemetry": {
                    "total_post_calls": self.total_post_calls,
                    "successful_post_calls": self.successful_post_calls,
                    "traffic_health_percentage": health_pct,
                    "error_breakdown": self.error_breakdown
                }
            })

        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(self.execution_history, file, indent=4, ensure_ascii=False)
            print(f"📊 QoS Telemetry Summary:")
            print(f"   • Total POST Calls: {self.total_post_calls}")
            print(f"   • Successful Steps: {self.successful_post_calls}")
            print(f"   • Traffic Health: {health_pct}%")
            print(f"   • Error Breakdown: {self.error_breakdown}")
            print(f"💾 Agent execution log saved cleanly to '{file_path}'")


if __name__ == "__main__":
    if api_key:
        agent = MultiToolAutonomousAgent(api_key=api_key)
        prompt = (
            "Find the top C++ repository on GitHub and save an executive summary "
            "explaining why it is important into a file named 'cpp_overview.txt'."
        )
        agent.run(prompt)
        agent.save_agent_report("python-software-engineering/03_web_apis/multi_tool_agent_report.json")