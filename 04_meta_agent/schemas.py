from dataclasses import dataclass, field, asdict
from typing import Literal


@dataclass
class TaskTuple:
    """Invariant 5-Tuple T_k^(d) governing every Planner decision."""
    k: int                                      # Factory iteration (0 to 99)
    d: int                                      # Recursion depth (0 to 3)
    W_what: str                                 # Target capability or artifact
    W_where: list[str]                          # Candidate services or local modules
    H_mech: str                                 # API endpoint / OpenAPI GET check
    S_which: str                                # Selected optimal service + SLM/API route
    U_why: str                                  # Strategic rationale or upgrade justification
    mode: Literal["create", "upgrade", "reuse"] = "create"
    scope: Literal["global", "tool"] = "tool"
    topic: str = "general"
    time_budget_sec: float = 120.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentManifest:
    """Compressed metadata stored in agent_registry.json (no raw code bloat)."""
    agent_id: str
    scope: Literal["global", "tool"]
    topic: str
    file_path: str
    role_description: str
    quality_score: float
    qos_health: float
    schema_coverage: float
    avg_latency_sec: float
    slm_optimized: bool = False


@dataclass
class ImprovementSuggestion:
    """Actionable delta emitted by a Reporter to drive autonomous branching."""
    source_agent_id: str
    target_scope: Literal["global", "tool"]
    target_topic: str
    proposed_what: str
    priority: int = 1  # 1 (Highest) to 5 (Lowest)


@dataclass
class PlannerDecision:
    """Deterministic command packet emitted by Planner to Orchestrator/Factory."""
    action: Literal["EXECUTE_TUPLE", "REUSE_CACHED", "SKIP_DUPLICATE", "COMPLETE_BATCH"]
    regime: Literal["B0_FAST_AUDIT", "B_SEED_DEEP", "B_K_AUTONOMOUS"]
    task: TaskTuple | None = None
    cached_agent_id: str | None = None
    rationale: str = ""