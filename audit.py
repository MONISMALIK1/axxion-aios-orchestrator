"""
Audit Trail / Metrics / Outcome store — and the loop back to Knowledge.

The log is append-only and hash-chained: each entry carries the hash of the
one before it, so any later tampering breaks the chain and verify_chain()
catches it. This is what "audit-grade" has to mean concretely — not "we kept
records" but "the records can be proven intact".

The store does two jobs beyond logging: it computes the metrics an insurer is
billed against, and it writes each finished task's outcome back into the
Knowledge layer as a Fact, so the next task's routing and verification can
learn from it. That write-back is the feedback edge the flowchart has and the
real production system was missing.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from core import Decision
from knowledge import Fact, KnowledgeBase


@dataclass
class AuditEntry:
    seq: int
    task_id: str
    task_kind: str
    outcome: str
    risk_tier: str
    action: str
    at_risk_aed: float
    codes: list[str]
    prev_hash: str
    this_hash: str = ""

    def compute_hash(self) -> str:
        body = {k: v for k, v in self.__dict__.items() if k != "this_hash"}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class AuditStore:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._log: list[AuditEntry] = []
        self._kb = kb

    def record(self, task_kind: str, decision: Decision, action: str) -> AuditEntry:
        prev = self._log[-1].this_hash if self._log else "GENESIS"
        entry = AuditEntry(
            seq=len(self._log),
            task_id=decision.task_id,
            task_kind=task_kind,
            outcome=decision.outcome,
            risk_tier=decision.risk_tier,
            action=action,
            at_risk_aed=round(decision.at_risk_aed, 2),
            codes=[f.code for f in decision.findings],
            prev_hash=prev,
        )
        entry.this_hash = entry.compute_hash()
        self._log.append(entry)
        # Feedback edge: write the outcome back into Knowledge as a Fact.
        self._kb.put(Fact(
            id=f"OUTCOME-{decision.task_id}", kind="outcome",
            key=task_kind, value=decision.outcome, source="audit_store"))
        return entry

    def verify_chain(self) -> bool:
        prev = "GENESIS"
        for e in self._log:
            if e.prev_hash != prev or e.compute_hash() != e.this_hash:
                return False
            prev = e.this_hash
        return True

    def metrics(self) -> dict:
        n = len(self._log)
        if n == 0:
            return {}
        auto = sum(1 for e in self._log if e.action == "auto_execute")
        return {
            "tasks": n,
            "auto_executed": auto,
            "auto_rate": auto / n,
            "human_reviewed": n - auto,
            "holds": sum(1 for e in self._log if e.outcome == "HOLD"),
            "reviews": sum(1 for e in self._log if e.outcome == "REVIEW"),
            "aed_at_risk_flagged": round(sum(e.at_risk_aed for e in self._log), 2),
            "chain_intact": self.verify_chain(),
        }

    @property
    def log(self) -> list[AuditEntry]:
        return self._log
