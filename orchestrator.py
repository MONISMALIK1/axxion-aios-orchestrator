"""
The orchestrator — walks a task down the flowchart, one layer at a time.

    intake -> route -> agent cluster -> verification -> decision -> human gate
           -> execute -> audit (which writes the outcome back to Knowledge)

It is deliberately a linear, readable pipeline: you can point at any line and
say which box in the diagram it is. The state machine, retries, and SLA timers
that a production build needs (Temporal-style) would wrap this — they do not
change the shape of it.
"""
from __future__ import annotations

from agents import run_agent
from audit import AuditStore
from core import Decision, Task
from decision import decide, gate
from knowledge import KnowledgeBase
from router import route
from verification import verify


def process(task: Task, kb: KnowledgeBase, audit: AuditStore) -> Decision:
    trail: list[str] = []

    # Intake -> Triage & Routing
    cluster, base_tier = route(task)
    trail.append(f"intake: {task.kind} from {task.origin}")
    trail.append(f"routed -> {cluster} (base risk {base_tier})")

    # Agent cluster
    result = run_agent(cluster, task, kb)
    trail.append(f"{cluster}: {len(result.findings)} finding(s)")

    # Verification layer
    before = len(result.findings)
    result = verify(result, kb)
    if len(result.findings) != before:
        trail.append(f"verification: {before - len(result.findings)} finding(s) removed/softened")
    else:
        trail.append("verification: all findings grounded")

    # Decision Support
    decision = decide(task.id, base_tier, result)
    decision.trail = trail + list(result.notes)
    decision.trail.append(f"decision: {decision.outcome} (risk {decision.risk_tier})")

    # Human Approval / Override gate
    action, reason = gate(decision)
    decision.trail.append(f"gate: {action} — {reason}")

    # Execution + Audit (audit writes the outcome back into Knowledge)
    audit.record(task.kind, decision, action)
    decision.trail.append("audit: recorded, hash-chained, outcome fed back to knowledge")

    return decision
