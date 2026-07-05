"""
Knowledge / Evidence layer.

This is the shared source of truth every other layer reads from and the
Audit layer writes back into — the feedback loop that closes the flowchart.
In the real Axxion system these Facts would come from Claim Hub (peer
pricing), Audatex (labour time guides), the CBUAE rulebook, EVG/police
records, and the append-only outcome store. Here they are seeded by the
"scheduled data jobs" in main.py so the demo is self-contained.

Why it matters: agents may only cite facts that live here. That is what makes
the difference between an auditable decision ("held because PARTS-001 against
benchmark BM-parts-front_bumper") and an unaccountable one ("the model
flagged it").
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Fact:
    id: str
    kind: str            # "benchmark" | "regulation" | "history" | "outcome"
    key: str
    value: object
    source: str


class KnowledgeBase:
    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}

    def put(self, fact: Fact) -> None:
        self._facts[fact.id] = fact

    def get(self, fact_id: str | None) -> Fact | None:
        if fact_id is None:
            return None
        return self._facts.get(fact_id)

    def resolves(self, fact_id: str | None) -> bool:
        """The grounding check the Verification layer relies on."""
        return fact_id is not None and fact_id in self._facts

    def find(self, kind: str | None = None, key: str | None = None) -> list[Fact]:
        out = []
        for f in self._facts.values():
            if kind is not None and f.kind != kind:
                continue
            if key is not None and f.key != key:
                continue
            out.append(f)
        return out

    def __len__(self) -> int:
        return len(self._facts)
