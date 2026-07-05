"""
Shared data model for the AIOS orchestrator.

Every layer in the flowchart passes these objects along. Two design rules
carry through the whole system and are worth stating up front:

1. GROUNDING — a Finding that changes an outcome must cite an evidence_ref
   that resolves to a real Fact in the Knowledge layer. A finding with no
   resolvable evidence is treated as an opinion, not a fact, and the
   Verification layer strips it. This is the same non-fabrication guardrail
   used across the portfolio (Klaim appeal agent, careem-support-resolver).

2. REASON CODES, NOT SCORES — every decision is explained by named codes and,
   where money is involved, an exact AED amount. An insurer's or regulator's
   question is never "what's the score" but "prove why", so the audit trail
   is the product.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    """One unit of work entering the system from any origin."""
    id: str
    kind: str            # routing key, e.g. "repair_estimate", "recovery_demand"
    payload: dict        # the domain data for this task
    origin: str          # "claims_team" | "executive" | "policyholder" | "scheduled_job"


@dataclass
class Finding:
    code: str
    severity: str        # "hold" | "review" | "info"
    message: str
    evidence_ref: str | None = None   # id of a Fact in the Knowledge layer
    amount_aed: float = 0.0


@dataclass
class LayerResult:
    """What an agent cluster produced for a task."""
    agent: str
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def at_risk_aed(self) -> float:
        return sum(f.amount_aed for f in self.findings)


@dataclass
class Decision:
    task_id: str
    outcome: str = "PROCEED"        # "PROCEED" | "REVIEW" | "HOLD"
    risk_tier: str = "low"          # "low" | "medium" | "high"
    findings: list[Finding] = field(default_factory=list)
    trail: list[str] = field(default_factory=list)   # human-readable per-layer trail

    @property
    def at_risk_aed(self) -> float:
        return sum(f.amount_aed for f in self.findings)
