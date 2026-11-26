import json
import os
from typing import Literal
from schemas import AgentManifest, ImprovementSuggestion, PlannerDecision, TaskTuple

class PlannerEngine:
    """
    Base Pillar of the Meta-Agent.
    Operates purely on compressed metadata to run B_0 Fast Audits, resolve 5-Tuple
    dependencies, enforce U_why quality gates, and branch autonomously up to N=100.
    """

    def __init__(
        self,
        registry_path: str = "04_meta_agent/agent_registry.json",
        catalog_path: str = "04_meta_agent/service_catalog.json",
        max_agents: int = 100,
        max_depth: int = 3,
        upgrade_delta: float = 0.05,
        total_time_budget_sec: float = 86400.0,  # 24h macro ceiling
        seed_time_ceiling_sec: float = 10800.0,  # 3h max ceiling for human seed
    ):
        self.registry_path = registry_path
        self.catalog_path = catalog_path
        self.max_agents = max_agents
        self.max_depth = max_depth
        self.upgrade_delta = upgrade_delta
        self.total_time_budget_sec = total_time_budget_sec
        self.seed_time_ceiling_sec = seed_time_ceiling_sec

        self.registry: dict[str, AgentManifest] = {}
        self.service_catalog: dict[str, dict] = {}
        self.suggestion_queue: list[ImprovementSuggestion] = []
        self.seed_completed: bool = False

        self._load_state()

    def _load_state(self) -> None:
        """Loads compressed registry headers and static service catalog into RAM."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                self.registry = {
                    aid: AgentManifest(**meta) for aid, meta in raw.items()
                }

        if os.path.exists(self.catalog_path):
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                self.service_catalog = json.load(f)

    # -----------------------------------------------------------------
    # REGIME B_0: Speed-of-Light Local Board Audit (O(1) Latency)
    # -----------------------------------------------------------------
    def run_fast_board_audit(self, topic: str, required_service: str | None = None) -> dict:
        """Audits local registry and service catalog in RAM before spending LLM tokens."""
        global_modules = [m for m in self.registry.values() if m.scope == "global"]
        topic_tools = [
            m for m in self.registry.values()
            if m.scope == "tool" and m.topic == topic
        ]
        best_existing = max(topic_tools, key=lambda m: m.quality_score, default=None)
        service_known = (
            required_service in self.service_catalog if required_service else False
        )

        return {
            "global_body_count": len(global_modules),
            "degraded_global_modules": [
                m.agent_id for m in global_modules if m.qos_health < 0.70
            ],
            "topic_existing_count": len(topic_tools),
            "best_existing_tool": best_existing.agent_id if best_existing else None,
            "best_existing_score": best_existing.quality_score if best_existing else 0.0,
            "service_spec_cached": service_known,
        }

    # -----------------------------------------------------------------
    # MATHEMATICAL USEFULNESS GATE: Q(a) & U_why
    # -----------------------------------------------------------------
    @staticmethod
    def compute_quality_score(
        qos_health: float,
        schema_coverage: float,
        latency_sec: float,
        slm_optimized: bool,
    ) -> float:
        """Computes composite Singapore efficiency & quality score Q(a) in [0, 1]."""
        w1, w2, w3, w4 = 0.35, 0.30, 0.20, 0.15
        latency_term = 1.0 / (1.0 + max(latency_sec, 0.0))
        token_efficiency = 1.0 if slm_optimized else 0.5
        score = (
            w1 * qos_health
            + w2 * schema_coverage
            + w3 * latency_term
            + w4 * token_efficiency
        )
        return round(score, 4)

    def evaluate_usefulness(
self, topic: str, candidate_score: float, deterministic_pass: bool
    ) -> Literal["REGISTER", "UPGRADE", "DISCARD"]:
        """Evaluates U_why(a_new) = G_det * I(Q(a_new) > Q(a_existing) + delta)."""
        if not deterministic_pass:
            return "DISCARD"

        board = self.run_fast_board_audit(topic)
        best_score = board["best_existing_score"]

        if board["topic_existing_count"] == 0:
            return "REGISTER"
        if candidate_score > (best_score + self.upgrade_delta):
            return "UPGRADE"
        return "DISCARD"

    # -----------------------------------------------------------------
    # REPORTER INGESTION & ADAPTIVE TIME BUDGETING
    # -----------------------------------------------------------------
    def ingest_report(self, report: dict) -> None:
        """Ingests compressed Reporter output and queues prioritized improvement deltas."""
        for item in report.get("improvement_suggestions", []):
            self.suggestion_queue.append(
                ImprovementSuggestion(
                    source_agent_id=report.get("agent_id", "unknown"),
                    target_scope=item.get("target_scope", "tool"),
                    target_topic=item.get("target_topic", "general"),
                    proposed_what=item.get("proposed_what", ""),
                    priority=item.get("priority", 2),
                )
            )
        self.suggestion_queue.sort(key=lambda s: s.priority)

    def _allocate_time_budget(self, k: int, elapsed_sec: float) -> float:
        """Computes dynamic ceiling for B_seed (k=0) vs B_k (k>=1)."""
        remaining_total = max(self.total_time_budget_sec - elapsed_sec, 60.0)
        if k == 0 and not self.seed_completed:
            return min(self.seed_time_ceiling_sec, remaining_total)

        remaining_slots = max(self.max_agents - k, 1)
        return round(min(900.0, remaining_total / remaining_slots), 2)

    # -----------------------------------------------------------------
    # MASTER STATE TRANSITION CONTROLLER
    # -----------------------------------------------------------------
    def plan_next_step(
        self,
        seed_spec: dict | None,
        elapsed_sec: float,
        depth: int = 0,
    ) -> PlannerDecision:
        """Decides the next factory action across B_0, B_seed, and B_k regimes."""
        registered_count = len(self.registry)

        if registered_count >= self.max_agents or elapsed_sec >= self.total_time_budget_sec:
            return PlannerDecision(
                action="COMPLETE_BATCH",
                regime="B_K_AUTONOMOUS",
                rationale=f"Reached boundary: {registered_count}/{self.max_agents} agents.",
            )

        if depth > self.max_depth:
            return PlannerDecision(
                action="SKIP_DUPLICATE",
                regime="B_SEED_DEEP",
                rationale=f"Recursion depth {depth} exceeded max_depth={self.max_depth}.",
            )

        # 1. REGIME B_SEED: Handle initial human prompt if not yet satisfied
        if not self.seed_completed and seed_spec is not None:
            topic = seed_spec.get("topic", "general")
            service = seed_spec.get("primary_service")
            board = self.run_fast_board_audit(topic, service)

            # B_0 Fast Cache Hit: Reuse if high-scoring tool already exists
            if board["best_existing_score"] >= 0.90 and not seed_spec.get("force_upgrade"):
                self.seed_completed = True
                return PlannerDecision(
                    action="REUSE_CACHED",
                    regime="B0_FAST_AUDIT",
                    cached_agent_id=board["best_existing_tool"],
                    rationale="B_0 Fast Audit hit high-utility cached tool; skipping synthesis.",
                )

            mode = "upgrade" if board["topic_existing_count"] > 0 else "create"
            budget = self._allocate_time_budget(k=0, elapsed_sec=elapsed_sec)
            task = TaskTuple(
                k=0,
                d=depth,
                W_what=seed_spec["W_what"],
                W_where=seed_spec.get("W_where", []),
                H_mech=seed_spec.get("H_mech", "GET /openapi.json"),
                S_which=service or "auto_select",
                U_why=seed_spec.get("U_why", "Satisfy primary human seed objective."),
                mode=mode,
                scope="tool",
                topic=topic,
                time_budget_sec=budget,
            )
            return PlannerDecision(
                action="EXECUTE_TUPLE",
                regime="B_SEED_DEEP",
                task=task,
                rationale=f"Dispatched seed task (mode={mode}) with {budget}s ceiling.",
            )

        # 2. REGIME B_K: Autonomous expansion driven by Reporter suggestions
        while self.suggestion_queue:
            suggestion = self.suggestion_queue.pop(0)
            board = self.run_fast_board_audit(suggestion.target_topic)
            k_next = registered_count
            budget = self._allocate_time_budget(k=k_next, elapsed_sec=elapsed_sec)

            mode = "upgrade" if board["topic_existing_count"] > 0 else "create"
            task = TaskTuple(
                k=k_next,
                d=0,
                W_what=suggestion.proposed_what,
                W_where=[suggestion.target_topic],
                H_mech="INSPECT_CATALOG_OR_OPENAPI",
                S_which="slm_routed_synthesizer",
                U_why=f"Autonomous expansion from {suggestion.source_agent_id} report.",
                mode=mode,
                scope=suggestion.target_scope,
                topic=suggestion.target_topic,
                time_budget_sec=budget,
            )
            return PlannerDecision(
                action="EXECUTE_TUPLE",
                regime="B_K_AUTONOMOUS",
                task=task,
                rationale=f"Autonomous branch k={k_next} queued under topic '{suggestion.target_topic}'.",
            )

        return PlannerDecision(
            action="COMPLETE_BATCH",
            regime="B_K_AUTONOMOUS",
            rationale="Seed satisfied and Reporter suggestion queue drained.",
        )