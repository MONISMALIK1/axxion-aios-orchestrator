"""
Decision Support + Human Approval layers.

decide() turns verified findings into one outcome and a final risk tier.
gate() then applies the "people first, AI second" rule with a twist that makes
it scale: a human does not touch every task — only the ones where a human's
judgement changes something. Low-risk PROCEED tasks auto-execute WITH a logged
justification (that logged justification is the licence to go fast). Everything
else queues for a person, who still owns the call.
"""
from __future__ import annotations

from core import Decision, LayerResult
from router import escalate_risk


def decide(task_id: str, base_tier: str, result: LayerResult) -> Decision:
    d = Decision(task_id=task_id, findings=list(result.findings))
    if any(f.severity == "hold" for f in result.findings):
        d.outcome = "HOLD"
    elif any(f.severity == "review" for f in result.findings):
        d.outcome = "REVIEW"
    else:
        d.outcome = "PROCEED"
    d.risk_tier = escalate_risk(base_tier, d.at_risk_aed)
    return d


def gate(decision: Decision) -> tuple[str, str]:
    """Return (action, reason). action is 'auto_execute' or 'human_review'."""
    if decision.outcome == "PROCEED" and decision.risk_tier == "low":
        return "auto_execute", "Clean, low-risk — auto-executed with logged justification."
    if decision.outcome == "PROCEED" and decision.risk_tier == "medium":
        return "auto_execute", "Clean, medium-risk within auto-band — executed, logged for sampling."
    if decision.outcome == "HOLD":
        return "human_review", "Structural finding — escalated with reason codes attached."
    if decision.risk_tier == "high":
        return "human_review", "High-risk tier — human owns this decision regardless of outcome."
    return "human_review", "Flagged for review — queued with full trail."
