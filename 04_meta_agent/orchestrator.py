import json
import time
from dataclasses import asdict
from pathlib import Path
from auditor import DeterministicAuditor
from planner import PlannerEngine
from reporter import TelemetryReporter
from router import LLMRouter
from schemas import AgentManifest
from synthesizer import CodeSynthesizer


class MetaAgentOrchestrator:
    """
    Master Closed-Loop State Machine.
    Coordinates Planner decisions, System 1 synthesis, System 2 sandbox auditing,
    bounded traceback repair, registry persistence, and Reporter-driven expansion.
    """

    def __init__(
        self,
        max_agents: int = 6,
        max_repairs_per_agent: int = 3,
        pacing_cooldown_sec: float = 3.0,
    ) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.registry_path = self.base_dir / "agent_registry.json"
        self.catalog_path = self.base_dir / "service_catalog.json"
        self.quarantine_dir = self.base_dir / "quarantine"
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.max_repairs_per_agent = max_repairs_per_agent
        self.quarantined_records: list[dict] = []

        self.planner = PlannerEngine(
            registry_path=str(self.registry_path),
            catalog_path=str(self.catalog_path),
            max_agents=max_agents,
        )
        self.router = LLMRouter(pacing_cooldown_sec=pacing_cooldown_sec)
        self.synthesizer = CodeSynthesizer(router=self.router)
        self.auditor = DeterministicAuditor()
        self.reporter = TelemetryReporter(router=self.router)

    def _persist_registry(self) -> None:
        """Writes updated AgentManifest entries back to agent_registry.json."""
        serialized = {
            aid: asdict(manifest) for aid, manifest in self.planner.registry.items()
        }
        self.registry_path.write_text(
            json.dumps(serialized, indent=4, ensure_ascii=False), encoding="utf-8"
        )

    def _persist_quarantine(self) -> None:
        """Logs scripts that failed 3 repair attempts into quarantine/failed_agents.json."""
        if not self.quarantined_records:
            return
        q_path = self.quarantine_dir / "failed_agents.json"
        q_path.write_text(
            json.dumps(self.quarantined_records, indent=4, ensure_ascii=False), encoding="utf-8"
        )

    def run(self, user_seed_prompt: str) -> None:
        start_ts = time.perf_counter()
        print("=" * 72)
        print("🧠 META-AGENT ORCHESTRATOR INITIALIZED")
        print(f"💬 Seed Prompt: '{user_seed_prompt}'")
        print(f"📊 Initial Registry Size: {len(self.planner.registry)}/{self.planner.max_agents}")
        print("=" * 72)

        # Convert raw human prompt into structured 5-Tuple seed specification
        seed_spec = self.synthesizer.parse_seed_prompt(
            user_seed_prompt, self.planner.service_catalog
        )
        print(f"🧭 Parsed Seed Spec -> Topic: '{seed_spec['topic']}' | Target: {seed_spec['W_what']}\n")

        while True:
            elapsed = time.perf_counter() - start_ts
            decision = self.planner.plan_next_step(seed_spec=seed_spec, elapsed_sec=elapsed)

            print(f"📌 Planner Decision: [{decision.action}] ({decision.regime}) -> {decision.rationale}")

            if decision.action == "COMPLETE_BATCH":
                break

            if decision.action == "REUSE_CACHED":
                print(f"⚡ Cache Hit! Reusing verified tool: '{decision.cached_agent_id}'\n")
                continue

            if decision.action == "SKIP_DUPLICATE" or decision.task is None:
                continue

            task = decision.task
            print(f"\n🔨 Synthesizing Candidate Agent [k={task.k}, d={task.d}] -> '{task.W_what}'")

            try:
                artifact = self.synthesizer.synthesize_task(task, self.planner.service_catalog)
            except Exception as err:
                print(f"❌ Synthesis API Failure: {err}\n")
                if task.k == 0:
                    self.planner.seed_completed = True
                continue

            # Bounded System 2 Verification & Traceback Repair Loop
            audit = self.auditor.audit_code_and_run(artifact["file_path"])
            repair_attempts = 0

            while not audit.passed and repair_attempts < self.max_repairs_per_agent:
                repair_attempts += 1
                print(
                    f"🛠️ Audit Failed [{audit.stage_failed}]. "
                    f"Triggering Repair {repair_attempts}/{self.max_repairs_per_agent}..."
                )
                try:
                    artifact = self.synthesizer.repair_script(
                        task, artifact, audit.error_traceback
                    )
                    audit = self.auditor.audit_code_and_run(artifact["file_path"])
                except Exception as repair_err:
                    print(f"⚠️ Repair Call Error: {repair_err}")
                    break

            if not audit.passed:
                print(f"🚫 Quarantined '{artifact['agent_id']}' after {repair_attempts} failed repairs.\n")
                self.quarantined_records.append({
                    "agent_id": artifact["agent_id"],
                    "topic": task.topic,
                    "stage_failed": audit.stage_failed,
                    "traceback": audit.error_traceback[-600:],
                })
                self._persist_quarantine()
                if task.k == 0:
                    self.planner.seed_completed = True
                continue

            # Evaluate Mathematical Usefulness Gate U_why
            qos = self.router.get_qos_snapshot()
            q_score = self.planner.compute_quality_score(
                qos_health=qos["qos_health"],
                schema_coverage=artifact["schema_coverage"],
                latency_sec=audit.execution_latency_sec,
                slm_optimized=artifact["slm_optimized"],
            )
            gate_verdict = self.planner.evaluate_usefulness(
                topic=task.topic,
                candidate_score=q_score,
                deterministic_pass=True,
            )

            print(
                f"✅ Sandbox Passed ({audit.execution_latency_sec}s) | "
                f"Q(a) = {q_score} | U_why Gate = [{gate_verdict}]"
            )

            if gate_verdict in ("REGISTER", "UPGRADE"):
                manifest = AgentManifest(
                    agent_id=artifact["agent_id"],
                    scope=task.scope,
                    topic=task.topic,
                    file_path=artifact["file_path"],
                    role_description=artifact["role_description"],
                    quality_score=q_score,
                    qos_health=qos["qos_health"],
                    schema_coverage=artifact["schema_coverage"],
                    avg_latency_sec=audit.execution_latency_sec,
                    slm_optimized=artifact["slm_optimized"],
                )
                self.planner.registry[manifest.agent_id] = manifest
                self._persist_registry()

                report = self.reporter.build_and_save_report(
                    task=task,
                    manifest=manifest,
                    audit=audit,
                    decision_label=gate_verdict,
                    qos_snapshot=qos,
                )
                self.planner.ingest_report(report)
                print(f"📥 Registered '{manifest.agent_id}' & ingested Reporter deltas.\n")
            else:
                print(f"🗑️ Discarded '{artifact['agent_id']}' (did not beat existing topic tool + delta).\n")

            if task.k == 0:
                self.planner.seed_completed = True

        total_elapsed = time.perf_counter() - start_ts
        final_qos = self.router.get_qos_snapshot()
        json_rep, md_rep = self.reporter.compile_master_report(
            registry=self.planner.registry,
            quarantined=self.quarantined_records,
            qos_snapshot=final_qos,
            elapsed_sec=total_elapsed,
        )

        print("=" * 72)
        print("🏁 META-AGENT FACTORY RUN COMPLETE")
        print(f"📊 Master JSON Report: {json_rep}")
        print(f"📄 Master Markdown Report: {md_rep}")
        print("=" * 72)


if __name__ == "__main__":
    # Pilot batch: 4 pre-seeded agents + 2 newly synthesized agents = 6 total.
    # Increase max_agents=100 for full unattended factory scaling.
    orchestrator = MetaAgentOrchestrator(max_agents=6, max_repairs_per_agent=3)
    sample_prompt = (
        "Create a Jupyter Notebook (.ipynb) slide deck using only green colors "
        "that explains the architectural differences between Python and C++."
    )
    orchestrator.run(sample_prompt)