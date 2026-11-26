import json
from dataclasses import asdict
from pathlib import Path
from auditor import AuditResult
from router import LLMRouter
from schemas import AgentManifest, TaskTuple


class TelemetryReporter:
    """
    Top-Layer Audit & Improvement Delta Generator.
    Compresses execution metrics into structured JSON reports, proposes next-step
    autonomous improvements, and compiles the final topic-grouped Master Report.
    """

    def __init__(self, router: LLMRouter, inbox_dir: str | None = None) -> None:
        self.router = router
        base_dir = Path(__file__).resolve().parent
        self.inbox_dir = Path(inbox_dir) if inbox_dir else (base_dir / "reports_inbox")
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir = base_dir

    def _propose_improvements(self, task: TaskTuple, manifest: AgentManifest, audit: AuditResult) -> list[dict]:
        """Uses SLM routing to propose 1-2 high-utility follow-up tools or verification steps."""
        system_instruction = (
            "You are the Strategic Auditor of an autonomous Meta-Agent. "
            "Given a newly verified agent, propose 1 or 2 high-value follow-up tools or quality upgrades "
            "(for example: adding a verification/anti-hallucination checker, adding a visual renderer, or caching outputs). "
            "Return ONLY a JSON object with key 'suggestions', containing a list of objects with keys: "
            "'target_scope' ('tool' or 'global'), 'target_topic' (snake_case string), "
            "'proposed_what' (concrete capability description), and 'priority' (integer 1 to 3)."
        )

        user_payload = (
            f"COMPLETED AGENT: {manifest.agent_id} (Topic: {manifest.topic})\n"
            f"ROLE: {manifest.role_description}\n"
            f"STDOUT PREVIEW: {audit.stdout_preview}"
        )

        try:
            res = self.router.generate_json(
                system_instruction=system_instruction,
                user_prompt=user_payload,
                tier="slm_fast",
            )
            suggestions = res.get("suggestions", [])
            if isinstance(suggestions, list) and suggestions:
                return suggestions[:2]
        except Exception:
            pass

        # Deterministic fallback suggestion if SLM router is congested
        return [
            {
                "target_scope": "tool",
                "target_topic": f"{manifest.topic}_verification",
                "proposed_what": f"Build a deterministic output schema and integrity validator for {manifest.agent_id}.",
                "priority": 2,
            }
        ]

    def build_and_save_report(
        self,
        task: TaskTuple,
        manifest: AgentManifest,
        audit: AuditResult,
        decision_label: str,
        qos_snapshot: dict,
    ) -> dict:
        """Builds compressed agent_report.json and saves it to reports_inbox/."""
        suggestions = self._propose_improvements(task, manifest, audit)

        report = {
            "agent_id": manifest.agent_id,
            "scope": manifest.scope,
            "topic": manifest.topic,
            "role_description": manifest.role_description,
            "tuple_audit": {
                "W_what": task.W_what,
                "W_where": task.W_where,
                "H_mech": task.H_mech,
                "S_which": task.S_which,
                "U_why": {
                    "decision": decision_label,
                    "quality_score": manifest.quality_score,
                    "rationale": task.U_why,
                },
            },
            "efficiency_telemetry": {
                "model_tier": "SLM_optimized" if manifest.slm_optimized else "Frontier_deep",
                "traffic_health_pct": qos_snapshot["traffic_health_percentage"],
                "latency_sec": audit.execution_latency_sec,
                "g_det": audit.g_det,
            },
            "improvement_suggestions": suggestions,
        }

        report_path = self.inbox_dir / f"{manifest.agent_id}_report.json"
        report_path.write_text(json.dumps(report, indent=4, ensure_ascii=False), encoding="utf-8")
        return report

    def compile_master_report(
        self,
        registry: dict[str, AgentManifest],
        quarantined: list[dict],
        qos_snapshot: dict,
        elapsed_sec: float,
    ) -> tuple[str, str]:
        """Generates final JSON and Markdown Master Executive Reports grouped by Topic."""
        grouped: dict[str, list[dict]] = {}
        for manifest in registry.values():
            grouped.setdefault(manifest.topic, []).append(asdict(manifest))

        master_data = {
            "summary": {
                "total_registered_agents": len(registry),
                "total_quarantined_attempts": len(quarantined),
                "total_wall_clock_sec": round(elapsed_sec, 2),
                "network_qos": qos_snapshot,
            },
            "agents_by_topic": grouped,
            "quarantined_log": quarantined,
        }

        json_out = self.base_dir / "master_meta_report.json"
        json_out.write_text(json.dumps(master_data, indent=4, ensure_ascii=False), encoding="utf-8")

        lines = [
            "# Meta-Agent Master Executive Report",
            "",
            "## System Telemetry & Efficiency Overview",
            f"- **Total Registered Agents:** {len(registry)}",
            f"- **Quarantined Failures:** {len(quarantined)}",
            f"- **Total Execution Time:** {round(elapsed_sec, 2)}s",
            f"- **Network QoS Health:** {qos_snapshot['traffic_health_percentage']}% "
            f"({qos_snapshot['successful_calls']}/{qos_snapshot['total_calls']} calls)",
            f"- **Error Breakdown:** {qos_snapshot['error_breakdown']}",
            "",
            "## Registered Agents Grouped by Topic",
        ]

        for topic, agents in sorted(grouped.items()):
            lines.append(f"\n### Topic: `{topic}` ({len(agents)} agents)")
            for ag in agents:
                lines.append(
                    f"- **`{ag['agent_id']}`** (`scope: {ag['scope']}` | $Q(a) = {ag['quality_score']}$)\n"
                    f"  - **Purpose:** {ag['role_description']}\n"
                    f"  - **File:** `{ag['file_path']}`\n"
                    f"  - **Run Command:** `python {ag['file_path']}`"
                )

        md_out = self.base_dir / "master_meta_report.md"
        md_out.write_text("\n".join(lines), encoding="utf-8")
        return str(json_out), str(md_out)