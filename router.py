"""
Triage & Routing engine.

Maps each task kind to the agent cluster that owns it and an initial risk
band. Routing is a plain lookup table on purpose — it is the SOP, and an SOP
you can read and version-control is worth more here than a clever classifier
that nobody can audit. A learned router can replace this later; it plugs in
behind the same interface and its choice still gets logged.
"""
from __future__ import annotations

from core import Task

# task.kind -> (agent cluster, base risk tier)
ROUTES: dict[str, tuple[str, str]] = {
    "repair_estimate":   ("claims_ops",        "medium"),
    "recovery_demand":   ("claims_ops",        "medium"),
    "total_loss":        ("claims_ops",        "high"),
    "regulatory_query":  ("legal_compliance",  "high"),
    "reserve_review":    ("finance_actuarial", "high"),
    "model_monitor":     ("data_ai_it",        "low"),
    "content_post":      ("marketing_strategy","low"),
}

DEFAULT_ROUTE = ("claims_ops", "medium")


def route(task: Task) -> tuple[str, str]:
    """Return (agent_cluster, base_risk_tier) for a task."""
    return ROUTES.get(task.kind, DEFAULT_ROUTE)


def escalate_risk(base_tier: str, amount_aed: float) -> str:
    """Value can push a task up a risk band regardless of its kind — a large
    repair estimate is never 'low risk' just because estimates usually are."""
    order = ["low", "medium", "high"]
    tier = base_tier
    if amount_aed >= 15000 and tier != "high":
        tier = "high"
    elif amount_aed >= 5000 and tier == "low":
        tier = "medium"
    return tier
