"""
Verification layer — the two checks Axxion already runs on content, applied
here to every decision that carries financial or regulatory weight.

1. FACT-CHECKING: a finding that would change the outcome (hold/review) must
   cite an evidence_ref that resolves in the Knowledge layer. If it does not,
   it is downgraded to an ungrounded note and cannot drive a HOLD — an agent
   is not allowed to hold a claim on something it can't point to. This is the
   fix for the weakness where the claims path skipped the verification chain
   that content already passes through.

2. DEVIL'S ADVOCATE: for any surviving HOLD, argue the counter-case. If the
   holding finding has no monetary basis AND no resolvable evidence, the
   red-team wins and the hold is softened to a review. The point is to make a
   human's queue smaller and higher-quality, not to auto-clear risk.
"""
from __future__ import annotations

from core import Finding, LayerResult
from knowledge import KnowledgeBase


def fact_check(result: LayerResult, kb: KnowledgeBase) -> LayerResult:
    kept: list[Finding] = []
    for f in result.findings:
        if f.severity in ("hold", "review") and not kb.resolves(f.evidence_ref):
            result.notes.append(
                f"[fact-check] {f.code} downgraded: no resolvable evidence "
                f"({f.evidence_ref!r}) — treated as opinion, not fact.")
            continue
        kept.append(f)
    result.findings = kept
    return result


def devils_advocate(result: LayerResult, kb: KnowledgeBase) -> LayerResult:
    for f in result.findings:
        if f.severity == "hold" and f.amount_aed == 0.0 and not kb.resolves(f.evidence_ref):
            f.severity = "review"
            result.notes.append(
                f"[devil's-advocate] {f.code} softened hold->review: "
                f"no monetary basis and no grounding survived the counter-case.")
    return result


def verify(result: LayerResult, kb: KnowledgeBase) -> LayerResult:
    return devils_advocate(fact_check(result, kb), kb)
