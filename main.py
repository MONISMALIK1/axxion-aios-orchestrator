"""
Run a batch of tasks through the whole AIOS orchestrator and print:
  1. the seeded Knowledge layer (what "scheduled data jobs" put on file)
  2. each task's decision + the per-layer trail it took through the flowchart
  3. the final audit metrics, including the tamper-evidence chain check

    python3 main.py
"""
from audit import AuditStore
from core import Task
from knowledge import Fact, KnowledgeBase
from orchestrator import process


def seed_knowledge(kb: KnowledgeBase) -> None:
    """Stands in for the 'scheduled data jobs' box: benchmarks and regulations
    written into the Knowledge layer before any task runs."""
    kb.put(Fact("BM-parts-front_bumper-non_agency", "benchmark",
                "front_bumper-non_agency", 950.0, "claim_hub"))
    kb.put(Fact("BM-parts-front_bumper-agency", "benchmark",
                "front_bumper-agency", 2400.0, "claim_hub"))
    kb.put(Fact("REG-total-loss-threshold", "regulation",
                "total_loss_threshold", 0.65, "cbuae_rulebook"))
    kb.put(Fact("REG-limitation-days", "regulation",
                "limitation_days", 1095, "uae_civil_code_art_1036"))
    kb.put(Fact("REG-decree-6-2025", "regulation",
                "outsourcing_repaper", "2026-09-16", "cbuae_decree_6_2025"))
    kb.put(Fact("REG-police-required", "regulation",
                "police_report_required", True, "cbuae_unified_motor_policy"))


TASKS = [
    Task("T-01", "repair_estimate", {
        "damage_type": "front_bumper", "workshop_type": "non_agency",
        "parts_cost_aed": 2100.0, "vehicle_value_aed": 80000.0,
        "total_estimate_aed": 2660.0}, origin="claims_team"),
    Task("T-02", "repair_estimate", {
        "damage_type": "front_bumper", "workshop_type": "non_agency",
        "parts_cost_aed": 900.0, "vehicle_value_aed": 60000.0,
        "total_estimate_aed": 1400.0}, origin="claims_team"),
    Task("T-03", "repair_estimate", {
        "damage_type": "front_bumper", "workshop_type": "agency",
        "parts_cost_aed": 2450.0, "vehicle_value_aed": 6000.0,
        "total_estimate_aed": 4500.0}, origin="claims_team"),
    Task("T-04", "recovery_demand", {
        "days_since_loss": 40, "police_report_ref": "DXB-2026-55123"},
        origin="claims_team"),
    Task("T-05", "recovery_demand", {
        "days_since_loss": 1200, "police_report_ref": "DXB-2024-11999"},
        origin="claims_team"),
    Task("T-06", "recovery_demand", {
        "days_since_loss": 20, "police_report_ref": None},
        origin="claims_team"),
    Task("T-07", "regulatory_query", {"touches_outsourcing": True},
         origin="executive"),
    Task("T-08", "content_post", {"topic": "claims transparency"},
         origin="marketing"),
    Task("T-09", "repair_estimate", {
        "damage_type": "front_bumper", "workshop_type": "non_agency",
        "parts_cost_aed": 900.0, "vehicle_value_aed": 70000.0,
        "total_estimate_aed": 1400.0, "unverified_hold": True},
        origin="claims_team"),
]


def main() -> None:
    kb = KnowledgeBase()
    seed_knowledge(kb)
    SEEDED = len(kb)
    audit = AuditStore(kb)

    print("=" * 78)
    print("Axxion AIOS orchestrator — reference run")
    print("=" * 78)
    print(f"Knowledge layer seeded with {len(kb)} facts "
          f"(benchmarks + regulations from scheduled jobs).\n")

    for task in TASKS:
        d = process(task, kb, audit)
        codes = ", ".join(f.code for f in d.findings) or "-"
        print(f"[{task.id}] {task.kind:<16} -> {d.outcome:<7} "
              f"risk={d.risk_tier:<6} codes: {codes}")
        for line in d.trail:
            print(f"       · {line}")
        print()

    m = audit.metrics()
    print("=" * 78)
    print("Audit metrics")
    print("=" * 78)
    print(f"Tasks processed        : {m['tasks']}")
    print(f"Auto-executed          : {m['auto_executed']} ({m['auto_rate']:.0%}) "
          f"— no human touch")
    print(f"Human-reviewed         : {m['human_reviewed']}")
    print(f"HOLD / REVIEW          : {m['holds']} / {m['reviews']}")
    print(f"AED at risk flagged    : AED {m['aed_at_risk_flagged']:,.2f}")
    print(f"Audit chain intact     : {m['chain_intact']}")
    print(f"Knowledge facts now    : {len(kb)} "
          f"(grew by {len(kb) - SEEDED} from outcomes fed back)")
    print()


if __name__ == "__main__":
    main()
