"""
Agent clusters — the five domains from the flowchart.

Each cluster is a scoped handler: it takes a Task plus read-only access to the
Knowledge layer and returns a LayerResult of reason-coded Findings. Crucially,
a finding that should change the outcome cites the Fact id it is grounded in,
so the Verification layer can confirm it later.

Only claims_ops is fleshed out in depth (it reuses the repair-estimate audit
logic from the axxion-repair-audit prototype); the others are realistic stubs
that show the same shape — scope in, grounded findings out — so the
orchestration is complete end to end without pretending every domain is
finished.
"""
from __future__ import annotations

from core import Finding, LayerResult, Task
from knowledge import KnowledgeBase


def _claims_ops(task: Task, kb: KnowledgeBase) -> LayerResult:
    r = LayerResult(agent="claims_ops")

    if task.kind == "repair_estimate":
        p = task.payload
        # An agent may surface a pattern-based hunch, but if it can't cite a
        # benchmark the Verification layer will strip it — shown here on purpose.
        if p.get("unverified_hold"):
            r.findings.append(Finding(
                code="HUNCH-001", severity="hold",
                message="Flagged on an unverified pattern — no benchmark cited."))
        # Parts check, grounded in a peer-pricing benchmark Fact.
        bm_id = f"BM-parts-{p['damage_type']}-{p['workshop_type']}"
        bm = kb.get(bm_id)
        if bm is not None and p["parts_cost_aed"] > bm.value * 1.25:
            over = p["parts_cost_aed"] - bm.value
            r.findings.append(Finding(
                code="PARTS-001", severity="review",
                message=(f"Parts AED {p['parts_cost_aed']:,.0f} vs "
                         f"AED {bm.value:,.0f} peer average "
                         f"({over/bm.value:.0%} over)."),
                evidence_ref=bm_id, amount_aed=over))
        # Total-loss routing, grounded in the regulatory threshold Fact.
        tl = kb.get("REG-total-loss-threshold")
        if tl is not None and p["total_estimate_aed"] > p["vehicle_value_aed"] * tl.value:
            r.findings.append(Finding(
                code="TL-001", severity="hold",
                message=(f"Estimate is "
                         f"{p['total_estimate_aed']/p['vehicle_value_aed']:.0%} of "
                         f"vehicle value (> {tl.value:.0%} total-loss threshold) "
                         f"— route to total-loss, not repair."),
                evidence_ref="REG-total-loss-threshold"))
        if not r.findings:
            r.notes.append("Estimate within all benchmarks.")
        return r

    if task.kind == "recovery_demand":
        p = task.payload
        # Grounded in the limitation-period regulation.
        lim = kb.get("REG-limitation-days")
        if lim is not None and p["days_since_loss"] > lim.value:
            r.findings.append(Finding(
                code="LIMIT-001", severity="hold",
                message=(f"{p['days_since_loss']} days since loss exceeds the "
                         f"{lim.value}-day limitation window — recovery barred."),
                evidence_ref="REG-limitation-days"))
        elif not p.get("police_report_ref"):
            r.findings.append(Finding(
                code="POLICE-001", severity="review",
                message="No police report reference on file — demand not yet admissible.",
                evidence_ref="REG-police-required"))
        else:
            r.notes.append("Recovery demand pack is complete and in-window.")
        return r

    if task.kind == "total_loss":
        r.notes.append("Total-loss valuation handled by claims_ops specialist.")
        return r

    r.notes.append(f"claims_ops received unhandled kind '{task.kind}'.")
    return r


def _legal_compliance(task: Task, kb: KnowledgeBase) -> LayerResult:
    r = LayerResult(agent="legal_compliance")
    reg = kb.find(kind="regulation")
    r.notes.append(f"Checked against {len(reg)} regulation facts on file.")
    if task.payload.get("touches_outsourcing"):
        r.findings.append(Finding(
            code="REG-OUTSRC", severity="review",
            message="Touches an outsourcing arrangement — re-paper before Sep 2026 deadline.",
            evidence_ref="REG-decree-6-2025"))
    return r


def _finance_actuarial(task: Task, kb: KnowledgeBase) -> LayerResult:
    r = LayerResult(agent="finance_actuarial")
    r.notes.append("Reserve/number audit stub — would reconcile against portfolio facts.")
    return r


def _data_ai_it(task: Task, kb: KnowledgeBase) -> LayerResult:
    r = LayerResult(agent="data_ai_it")
    r.notes.append("Model-monitoring stub — would check drift against benchmark facts.")
    return r


def _marketing_strategy(task: Task, kb: KnowledgeBase) -> LayerResult:
    r = LayerResult(agent="marketing_strategy")
    r.notes.append("Content/strategy stub — non-money path, still routed through verification.")
    return r


CLUSTERS = {
    "claims_ops":         _claims_ops,
    "legal_compliance":   _legal_compliance,
    "finance_actuarial":  _finance_actuarial,
    "data_ai_it":         _data_ai_it,
    "marketing_strategy": _marketing_strategy,
}


def run_agent(cluster: str, task: Task, kb: KnowledgeBase) -> LayerResult:
    handler = CLUSTERS.get(cluster)
    if handler is None:
        return LayerResult(agent=cluster, notes=[f"No handler for cluster '{cluster}'."])
    return handler(task, kb)
