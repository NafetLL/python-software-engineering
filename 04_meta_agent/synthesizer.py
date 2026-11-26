import re
from pathlib import Path
from router import LLMRouter
from schemas import TaskTuple


class CodeSynthesizer:
    """
    System 1 Code Generation & Repair Factory.
    Translates human prompts into 5-Tuple seed specs, synthesizes standalone
    Python agent scripts, and repairs failing scripts using System 2 tracebacks.
    """

    ALLOWED_IMPORTS_NOTE = (
        "json, os, sys, math, time, re, datetime, pathlib, typing, dataclasses, "
        "requests, urllib, hashlib, csv, collections, itertools, statistics, random, string"
    )

    def __init__(self, router: LLMRouter, output_dir: str | None = None) -> None:
        self.router = router
        base_dir = Path(__file__).resolve().parent
        self.output_dir = Path(output_dir) if output_dir else (base_dir / "generated_agents")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_agent_id(raw_id: str) -> str:
        """Normalizes agent_id into a safe snake_case Python module identifier."""
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", raw_id.strip().lower())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned or cleaned[0].isdigit():
            cleaned = f"agent_{cleaned}"
        return cleaned[:48]

    def parse_seed_prompt(self, raw_prompt: str, service_catalog: dict) -> dict:
        """Converts any human prompt (vague or specific) into a structured seed_spec."""
        system_instruction = (
            "You are the Intake Translator of an autonomous Meta-Agent. "
            "Convert the user's request into a deterministic JSON task specification. "
            "If the user prompt is vague (e.g., 'I don't understand'), infer a clear, "
            "high-utility visual explainer or structured study artifact. "
            "Return ONLY a JSON object with keys: "
            "'topic' (snake_case category), 'primary_service' (matching a key in the catalog if applicable), "
            "'W_what' (exact artifact or capability to build), 'W_where' (list of candidate services), "
            "'H_mech' (API endpoint or local builder mechanism), 'U_why' (clear objective rationale), "
            "and 'force_upgrade' (boolean)."
        )

        user_payload = (
            f"USER PROMPT: {raw_prompt}\n\n"
            f"AVAILABLE SERVICE CATALOG:\n{list(service_catalog.keys())}"
        )

        spec = self.router.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_payload,
            tier="slm_fast",
        )

        return {
            "topic": str(spec.get("topic", "general_automation")),
            "primary_service": spec.get("primary_service", "local_educational_artifact_builder"),
            "W_what": str(spec.get("W_what", raw_prompt)),
            "W_where": list(spec.get("W_where", ["local_educational_artifact_builder"])),
            "H_mech": str(spec.get("H_mech", "local://sandbox/artifacts")),
            "U_why": str(spec.get("U_why", "Fulfill primary user objective.")),
            "force_upgrade": bool(spec.get("force_upgrade", False)),
        }

    def synthesize_task(self, task: TaskTuple, service_catalog: dict) -> dict:
        """Generates a standalone, self-contained Python agent script for a TaskTuple."""
        service_info = service_catalog.get(task.S_which, {})
        tier = service_info.get("preferred_tier", "frontier_deep")

        system_instruction = (
            "You are an expert Python Systems Engineer inside a Neuro-Symbolic Meta-Agent. "
            "Write a complete, standalone, self-contained Python script that implements the requested task. "
            "STRICT SECURITY & SANDBOX RULES:\n"
            f"1. ONLY import from this allowlist: {self.ALLOWED_IMPORTS_NOTE}.\n"
            "2. NEVER use eval(), exec(), compile(), __import__(), os.system(), subprocess, or file deletion (os.remove, shutil.rmtree).\n"
            "3. Include a clean `run_agent()` function AND an `if __name__ == '__main__':` self-test block "
            "that executes end-to-end without requiring interactive user input or unavailable private OAuth tokens "
            "(use public endpoints or generate real local output files inside the current working directory).\n"
            "4. Print a clear JSON summary of the execution outcome to stdout.\n"
            "Return ONLY a JSON object with keys: "
            "'agent_id' (snake_case name), 'role_description' (1-sentence summary), "
            "'schema_coverage' (float between 0.70 and 1.0), and 'python_code' (complete valid Python source string)."
        )

        user_payload = (
            f"TASK 5-TUPLE SPECIFICATION:\n{task.to_dict()}\n\n"
            f"TARGET SERVICE CONTRACT:\n{service_info}"
        )

        result = self.router.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_payload,
            tier=tier,
        )

        agent_id = self._sanitize_agent_id(result.get("agent_id", f"{task.topic}_agent_k{task.k}"))
        code = str(result.get("python_code", "")).strip()
        script_path = self.output_dir / f"{agent_id}.py"
        script_path.write_text(code, encoding="utf-8")

        return {
            "agent_id": agent_id,
            "file_path": str(script_path),
            "role_description": str(result.get("role_description", task.W_what)),
            "schema_coverage": float(result.get("schema_coverage", 0.85)),
            "slm_optimized": tier == "slm_fast",
            "python_code": code,
        }

    def repair_script(self, task: TaskTuple, broken_artifact: dict, error_traceback: str) -> dict:
        """Feeds System 2 audit traceback back to SLM router to patch syntax, security, or runtime bugs."""
        system_instruction = (
            "You are a Deterministic Code Repair Specialist. Fix the Python script based on the exact audit error. "
            f"ALLOWED IMPORTS ONLY: {self.ALLOWED_IMPORTS_NOTE}. "
            "NEVER use eval, exec, subprocess, or file deletion functions. "
            "Ensure `if __name__ == '__main__':` executes cleanly and exits with status 0. "
            "Return ONLY a JSON object with keys: 'fix_summary' (string) and 'python_code' (full repaired script)."
        )

        user_payload = (
            f"ORIGINAL OBJECTIVE: {task.W_what}\n"
            f"AUDIT FAILURE TRACEBACK:\n{error_traceback}\n\n"
            f"BROKEN PYTHON CODE:\n{broken_artifact['python_code']}"
        )

        repaired = self.router.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_payload,
            tier="slm_fast",
        )

        fixed_code = str(repaired.get("python_code", broken_artifact["python_code"])).strip()
        script_path = Path(broken_artifact["file_path"])
        script_path.write_text(fixed_code, encoding="utf-8")

        updated = dict(broken_artifact)
        updated["python_code"] = fixed_code
        updated["fix_summary"] = str(repaired.get("fix_summary", "Patched audit violation."))
        return updated