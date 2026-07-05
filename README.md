# Axxion AIOS Orchestrator — a reference implementation

A runnable, zero-dependency skeleton of the agentic claims-operating-system
architecture: a task enters, gets routed to a scoped agent cluster, its
findings are verified against grounded evidence, a risk-tiered human gate
decides who signs off, and an append-only hash-chained audit log records the
outcome and feeds it back into the knowledge layer.

It is built to mirror this flow:

```
User / Claims team / Executive
        │
    Intake ─► Triage & Routing ─► Agent clusters ─► Verification ─► Decision
                                   (5 domains)        (grounding +    support
                                                       red-team)         │
                                                                   Human gate
                                                                  (risk-tiered)
                                                                         │
        Scheduled jobs ─► Knowledge / Evidence ◄────────────────  Execution
                              ▲                                         │
                              └──────────  Audit / Metrics / Outcomes ◄─┘
                                           (append-only, hash-chained)
```

The loop from `Audit → Knowledge → back into Triage/Verification/Decision` is
the point. A one-way pipeline logs decisions; a closed loop lets the system
learn from its own outcomes. This repo implements the closed loop.

---

## Run it (pure Python 3.10+, no dependencies)

```bash
python3 main.py
```

On the sample batch of 9 tasks:

```
Tasks processed        : 9
Auto-executed          : 4 (44%) — no human touch
Human-reviewed         : 5
HOLD / REVIEW          : 2 / 3
AED at risk flagged    : AED 1,150.00
Audit chain intact     : True
Knowledge facts now    : 15 (grew by 9 from outcomes fed back)
```

Every task prints the exact path it took through the layers, so you can point
at any line and name the box in the diagram it came from.

---

## The layers, and the file that implements each

| Diagram box | File | What it does |
|---|---|---|
| Intake + Triage & Routing | `router.py` | Lookup table: task kind → agent cluster + base risk tier; value can escalate the tier |
| Agent clusters (5 domains) | `agents.py` | Each cluster returns reason-coded findings; a finding that changes an outcome cites the evidence it stands on |
| Verification | `verification.py` | Fact-check (strip ungrounded findings) + devil's advocate (soften unsupported holds) |
| Decision support | `decision.py` | Aggregate findings → PROCEED / REVIEW / HOLD + final risk tier |
| Human approval / override | `decision.py` `gate()` | Risk-tiered: low-risk clean tasks auto-execute with a logged reason; everything else queues for a human |
| Knowledge / evidence | `knowledge.py` | The shared source of truth agents read and the audit log writes back to |
| Audit / metrics / outcomes | `audit.py` | Append-only, hash-chained, tamper-evident; feeds outcomes back into knowledge |
| Orchestrator | `orchestrator.py` | Walks one task down every layer in order |

---

## Where AI is best used here — and where it must not be

The honest split, because it is the whole design argument:

**Rules / deterministic (the money path).** Routing, the grounded checks
(parts benchmark, total-loss threshold, limitation window), the risk tiering,
and the audit chain are deterministic. In a market where even a human loss
adjuster's report is treated as inadmissible-because-biased, a decision that
moves money has to be explainable to a regulator by pointing at a named rule
and a cited fact — not "the model scored it 0.83."

**LLMs (three narrow, non-binding jobs).**
1. *Intake extraction* — turn a police report, a photo set, or a free-text
   FNOL into the structured `payload` a Task carries. The LLM reads; the schema
   validates before anything enters the record.
2. *Verification assist* — the fact-checking layer can use an LLM to confirm a
   cited fact actually supports the finding, but it may only ever **remove** a
   finding, never invent one.
3. *Grounded drafting* — appeal letters, recovery demands, status updates:
   templated from facts on file, an LLM improves the prose but adds no facts.
   If the record can't support the claim, the agent says so (the guardrail
   from the Klaim appeal agent).

**Machine learning (later, behind the same interface).** Every human override
in the audit log is a labelled example. Once enough accumulate, a calibrated
model can replace a rule — but it plugs in behind the same reason-code
interface (SHAP values → the same code format), so the audit trail is
identical whether a threshold or a model fired the finding. Rules first
*because* they generate the labels the model will need.

The rule of thumb: **AI reads, drafts, and ranks; it never decides money
without a rule and a cited fact behind it, and a human owns every non-trivial
call.**

---

## How the automation actually scales

The naive version of "automate claims" auto-approves everything and hopes.
This design automates the *volume* while keeping humans on the *risk*:

- **Auto-execute the clean, low-risk tail.** Most tasks are clean. They
  execute with a logged justification — that logged justification is what
  makes fast approval defensible, not reckless.
- **Route only exceptions to humans.** HOLD findings and high-risk tiers queue
  for a person, who arrives at a pre-assembled file with the reason codes
  already attached — not an archaeology project.
- **Scheduled jobs keep the evidence fresh** so the agents are always checking
  against current benchmarks and regulations, not stale constants.
- **The feedback loop compounds.** Each outcome becomes a fact; each override
  becomes a training label. The system that runs the claims is the same system
  that learns to run them better.

So "1 human signs off" scales — because the volume reaching that human is
filtered by risk, not uniform.

---

## Honest limitations

- **The domain agents are intentionally shallow.** `claims_ops` implements
  real grounded checks (reused from the axxion-repair-audit prototype); the
  other four clusters are realistic stubs that prove the orchestration shape
  without pretending each domain is finished.
- **The knowledge layer is seeded in-process.** In production those facts come
  from Claim Hub, Audatex, the CBUAE rulebook, and EVG/police records — the
  `Fact` interface is the same; only the source changes.
- **No real state machine.** A production build wraps this in a durable
  workflow engine (Temporal-style) for retries, SLA timers, and long-running
  waits. That changes the runtime, not the shape of the pipeline shown here.
- **Hash-chaining is tamper-evidence, not tamper-proofing.** It proves the log
  wasn't altered after the fact; a production system also anchors the chain
  externally and controls write access.
- **It's a transparent rules layer on purpose** — the same rationale as the
  rest of this portfolio: the decisions have to be auditable before they can
  be autonomous, and the rules label the data a learned model will later train
  on.
