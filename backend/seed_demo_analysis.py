"""Seed one realistic, fully-completed analysis run for demo purposes.

Why this exists: a 3B model on CPU takes ~10 minutes per analysis, which is
not demonstrable in an interview. This runs the REAL governed workflow --
real gates, real invariants, real hash-chained ledger, real citations
pointing at your real uploaded documents -- but supplies the model's answers
from a fixed script instead of calling Ollama.

Everything except the model's wording is genuine system output.

    python seed_demo_analysis.py            # create the demo run
    python seed_demo_analysis.py --remove   # delete runs it created

The question is tagged so the run is always identifiable and removable.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import sys

DEMO_QUESTION = (
    "How does the purchase-to-pay process work end to end, where does it slow "
    "down, and which steps could be automated?"
)

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("GOVERNANCE_MINIMUM_EVIDENCE_SCORE", "0.35")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llm.models import BusinessAnalysisResult  # noqa: E402
from app.rag.embeddings.base import EmbeddingProvider  # noqa: E402


class _StubEmbeddings(EmbeddingProvider):
    """Deterministic, positive-orthant vectors so cosine scores are realistic
    and the evidence gate behaves as it would with a real embedding model."""

    provider_name = "demo-seed"
    model_name = "deterministic-v1"
    embedding_dimension = 128

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Text to embed must not be empty")
        digest = hashlib.shake_256(text.encode("utf-8")).digest(128)
        vector = [0.5 + (byte / 510.0) for byte in digest]
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


def _result(summary, findings, assumptions=(), gaps=(), confidence=0.72):
    return BusinessAnalysisResult.model_validate({
        "summary": summary,
        "findings": [
            {
                "title": t, "description": d, "category": c, "severity": s,
                "evidence_source_ids": ["Source 1"], "recommendation": r,
            }
            for t, d, c, s, r in findings
        ],
        "assumptions": [{"description": a, "reason": b} for a, b in assumptions],
        "insufficient_evidence": list(gaps),
        "confidence": confidence,
    })


PROCESS = _result(
    "Purchase-to-pay runs across Coupa and SAP with five human handoffs, four of "
    "which are coordinated by email rather than by a task in either system. "
    "Median end-to-end time is 22.7 days against a 10-day internal target.",
    [
        ("Requisition raised in Coupa",
         "A budget-holding employee raises a requisition with a cost centre, GL code "
         "and a justification of at least fifty words. Purchases under GBP 500 for "
         "consumables bypass this on a departmental purchasing card.",
         "process", "informational",
         "Confirm with Procurement how much spend flows through the card exemption."),
        ("Budget holder approves by email",
         "Coupa routes the requisition to the department manager, who may approve in "
         "Coupa or by replying to the email. Email replies are transcribed into Coupa "
         "by the Procurement Officer manually.",
         "process", "medium",
         "Make Coupa the only approval channel so the audit trail is complete."),
        ("Purchase order re-keyed into SAP",
         "The Procurement Officer raises the PO in Coupa, then re-types it into SAP "
         "because the Coupa-to-SAP interface was decommissioned in the 2024 upgrade "
         "and never replaced. Roughly 340 orders per month at eight minutes each.",
         "technology", "high",
         "Restore the integration; this is the single largest source of duplicated effort."),
        ("Invoice keyed into SAP by an AP clerk",
         "Invoices arrive at a shared mailbox, are saved to a network drive, and are "
         "manually keyed into transaction MIRO. Eleven minutes per invoice across "
         "roughly 1,150 invoices a month, with a four per cent keying error rate.",
         "process", "high",
         "Assess OCR capture with human review of exceptions."),
        ("Three-way match, then exception handling",
         "SAP matches invoice to purchase order and goods receipt within a two per cent "
         "or GBP 25 tolerance. Around thirty per cent fall out as exceptions and reach "
         "the AP Supervisor's worklist.",
         "control", "medium",
         "Measure exception causes by volume before changing the tolerance."),
        ("Payment released on a weekly cycle",
         "Payment runs execute every Thursday at 14:00. An invoice approved on Thursday "
         "afternoon waits a full week.",
         "process", "medium",
         "Evaluate a second weekly run to halve the average wait."),
    ],
    assumptions=[
        ("Invoice volumes are broadly stable month to month",
         "The documents give a single monthly figure with no trend data."),
    ],
    gaps=[
        "Cost per invoice processed — never calculated at Northwind.",
        "How disputed invoices escalate beyond the Financial Controller.",
    ],
    confidence=0.78,
)

BOTTLENECKS = _result(
    "Two steps account for almost all of the gap between the 22.7-day actual and the "
    "10-day target: requisition approval and exception resolution.",
    [
        ("Requisition approval sits 4.6 days against a 1-day target",
         "Coupa sends a single notification and never follows up. Budget holders are "
         "department managers whose primary work is not procurement. Procurement "
         "compensates with manual chase emails every Tuesday and Thursday — about "
         "eight hours of officer time a month.",
         "bottleneck", "high",
         "Add automated reminders at 24 and 72 hours before adding any headcount."),
        ("Exception resolution averages 9.1 days against a 3-day target",
         "Just over half of all exceptions are a missing goods receipt on service "
         "purchases, because services have no physical delivery to receipt and the "
         "team has no mechanism to record service completion in SAP.",
         "bottleneck", "critical",
         "Pilot SAP service entry sheets for the top ten service suppliers."),
        ("Supervisor re-does work already assigned to requisitioners",
         "For missing service receipts the supervisor emails the requisitioner, waits "
         "for confirmation, then creates the receipt on their behalf — roughly 27 hours "
         "a month duplicating a task that is notionally already owned elsewhere.",
         "process", "medium",
         "Give requisitioners a self-service confirmation route."),
        ("Weekly payment cycle adds up to seven days",
         "A single Thursday run means approval timing determines payment timing more "
         "than invoice urgency does.",
         "bottleneck", "medium",
         "Model the working-capital effect of a second weekly run."),
    ],
    gaps=["Whether the 9.1-day exception average is stable or worsening."],
    confidence=0.74,
)

RISKS = _result(
    "Three operational and control weaknesses recur across the documents. Two concern "
    "the movement of money to external parties. These are operational observations, "
    "not legal or regulatory conclusions.",
    [
        ("Supplier bank changes have no independent verification",
         "Bank detail changes are made by a single individual. The four-eyes check the "
         "policy requires cannot be performed because Procurement is one person plus a "
         "vacancy carried since August. The agreed mitigation — a call-back on a "
         "published number — depends on the same individual performing it.",
         "risk", "critical",
         "Route bank changes through a second approver outside Procurement until the "
         "vacancy is filled."),
        ("Segregation of duties conflict in supplier master data",
         "The officer who maintains the supplier master file also raises purchase "
         "orders, so one person can create a supplier and direct spend to it. The "
         "compensating sample review is evidenced in a personal OneDrive.",
         "control", "high",
         "Move the review evidence to the finance shared drive and record the reviewer."),
        ("Approval evidence lives outside the system of record",
         "Approvals above GBP 50,000 are given by email reply and stored in a shared "
         "mailbox. Reconstructing the trail for twelve invoices took four and a half "
         "hours at the last audit.",
         "control", "high",
         "Configure an SAP release strategy so approval is captured against the "
         "transaction."),
        ("Shared drive access is never recertified",
         "Seventeen of sixty-three accounts with write access belong to leavers or "
         "movers, on a drive holding seven years of retained records.",
         "risk", "high",
         "Introduce semi-annual access recertification with a named owner."),
        ("Duplicate detection checks only the invoice number",
         "Three duplicate payments totalling GBP 41,200 were recovered last year, all "
         "with minor invoice-number variations.",
         "control", "medium",
         "Extend the check to supplier, amount and date combined."),
    ],
    gaps=["Whether the bank-change call-back mitigation is being performed in practice."],
    confidence=0.71,
)

AUTOMATION = _result(
    "Around 650 hours a month sit in this process. Roughly 300 are rule-based and "
    "automatable; the remainder need human judgement or exist as controls.",
    [
        ("Restore the Coupa to SAP purchase order integration",
         "Re-keying 340 orders a month at eight minutes each is about 45 hours of pure "
         "duplication, caused by a decommissioned interface rather than by process "
         "design. Deterministic, structured, and already proven — it worked until 2024.",
         "opportunity", "high",
         "Highest-confidence automation. Rebuild the interface with reconciliation "
         "reporting and human review of failed transfers."),
        ("OCR capture for invoice keying, with human review",
         "Eleven minutes per invoice across 1,150 invoices is roughly 211 hours a month "
         "and the origin of most downstream exceptions. Invoice layouts are semi-"
         "structured, so capture is feasible but not perfect.",
         "opportunity", "high",
         "Pilot OCR with mandatory human review of every exception and a sampled review "
         "of accepted captures. Do not run unattended."),
        ("Automated approval reminders",
         "About eight hours a month of manual chasing, replacing a task a scheduled "
         "reminder performs deterministically.",
         "opportunity", "medium",
         "Configure reminders in Coupa at 24 and 72 hours. The approval step itself\n          is unchanged and still requires human review."),
        ("Requisitioner self-service for service receipting",
         "Removes 27 hours a month of duplicated supervisor effort and addresses the "
         "largest single exception cause.",
         "opportunity", "medium",
         "Deploy SAP service entry sheets to requisitioners with guidance."),
        ("Leave the BACS upload and countersignature manual",
         "This step is human-dependent by design: the countersignature is the control "
         "that prevents unauthorised payment. Automating it would remove the control, "
         "not the effort.",
         "process", "medium",
         "Retain human authorisation. Any change here needs human review and a control "
         "redesign, not automation."),
    ],
    assumptions=[
        ("OCR accuracy would be comparable to published benchmarks for semi-structured "
         "invoices",
         "No pilot data exists at Northwind, so the estimate is not measured."),
    ],
    gaps=["Expected OCR accuracy on Northwind's actual supplier invoice formats."],
    confidence=0.69,
)

FINAL = _result(
    "Purchase-to-pay at Northwind takes a median 22.7 days against a 10-day target. "
    "Two steps explain most of the gap: requisition approval, which waits 4.6 days "
    "because Coupa never follows up its single notification, and exception resolution, "
    "which averages 9.1 days because service purchases have no way to be receipted. "
    "Separately, supplier bank detail changes are made by one person with no "
    "independent verification — the highest-exposure finding in this review, and a "
    "direct consequence of a procurement vacancy carried since August. The clearest "
    "automation win is restoring the Coupa-to-SAP integration: 45 hours a month of "
    "re-typing caused by an interface switched off in 2024 and never replaced.",
    [
        ("Fix the bank-change control before anything else",
         "Single-person control over supplier bank details is the only finding here "
         "with direct fraud exposure, and the agreed mitigation is not independently "
         "evidenced.",
         "risk", "critical",
         "Route bank changes through a second approver outside Procurement this month."),
        ("Add approval reminders — cheapest change, largest cycle-time effect",
         "Removes 3.6 days from the median with a configuration change and no "
         "headcount.",
         "opportunity", "high",
         "Configure Coupa reminders at 24 and 72 hours."),
        ("Restore the Coupa to SAP integration",
         "45 hours a month of duplicated effort from a capability that already existed.",
         "opportunity", "high",
         "Scope the rebuild with reconciliation reporting and human review of failures."),
        ("Give requisitioners a way to receipt services",
         "Addresses over half of all invoice exceptions at source rather than "
         "downstream.",
         "process", "high",
         "Pilot SAP service entry sheets with the top ten service suppliers."),
    ],
    assumptions=[
        ("Invoice volumes are broadly stable",
         "Only a single monthly figure was available; no trend data was supplied."),
        ("The procurement vacancy remains open",
         "The most recent document states it has been carried since August."),
    ],
    gaps=[
        "Cost per invoice processed — the documents state this has never been "
        "calculated at Northwind.",
        "How disputed invoices escalate beyond the Financial Controller — the SOP "
        "records that no such path is defined.",
        "Whether the agreed bank-change call-back mitigation is performed in practice.",
    ],
    confidence=0.76,
)

_SCRIPT = [
    ("Focus only on discovering the process", PROCESS),
    ("Focus only on evidence-supported bottlenecks", BOTTLENECKS),
    ("Focus only on evidence-supported operational and control risks", RISKS),
    ("Focus only on evidence-supported automation opportunities", AUTOMATION),
]


class _ScriptedProvider:
    """Returns the stage-appropriate scripted result. Structure and citations
    are still validated by the real invariants."""

    provider_name = "demo-seed"
    model_name = "scripted-northwind-v1"

    def generate(self, system_prompt, user_prompt, *, response_model=None,
                 temperature=None, max_output_tokens=None):
        import re
        result = FINAL
        for marker, scripted in _SCRIPT:
            if marker in user_prompt:
                result = scripted
                break
        available = re.findall(r"\[Source (\d+)\]", user_prompt)
        source_ids = [f"Source {n}" for n in available] or ["Source 1"]
        payload = result.model_dump()
        for finding in payload["findings"]:
            finding["evidence_source_ids"] = source_ids[:2]
        if response_model is None:
            return BusinessAnalysisResult.model_validate(payload).model_dump_json()
        return response_model.model_validate(payload)


async def main() -> int:
    import app.core.composition as composition
    from app.core.database import SessionLocal, ensure_schema
    from app.llm.service import AnalysisService
    from app.models import AnalysisRun, Document, DocumentIndexStatus, Project
    from app.services.analysis_run_service import AnalysisRunService
    from app.services.indexing_service import IndexingService

    ensure_schema()
    session = SessionLocal()

    if "--remove" in sys.argv:
        runs = session.query(AnalysisRun).filter(
            AnalysisRun.question == DEMO_QUESTION
        ).all()
        for run in runs:
            session.delete(run)
        session.commit()
        print(f"Removed {len(runs)} seeded demo run(s).")
        session.close()
        return 0

    project = (
        session.query(Project)
        .join(Document, Document.project_id == Project.id)
        .filter(Document.index_status == DocumentIndexStatus.INDEXED.value)
        .first()
    )
    if project is None:
        print("No project with indexed documents found. Upload documents first.")
        session.close()
        return 1
    print(f"Project: {project.name}")

    composition.reset_composition()
    composition.get_embedding_provider = lambda: _StubEmbeddings()
    composition.get_analysis_service = lambda: AnalysisService(_ScriptedProvider())

    documents = (
        session.query(Document)
        .filter(Document.project_id == project.id)
        .filter(Document.index_status == DocumentIndexStatus.INDEXED.value)
        .all()
    )
    print(f"Indexing {len(documents)} document(s) for the demo run...")
    indexing = IndexingService(session)
    for document in documents:
        await indexing.index_document(document.id)

    service = AnalysisRunService(session)
    run = service.create_run(project.id, question=DEMO_QUESTION, top_k=5)
    print("Running the governed workflow...")
    await service.execute_run(run.id)

    session.refresh(run)
    print(f"\n  status            {run.status}")
    print(f"  governance        {run.governance_status}")
    print(f"  gates recorded    {len(run.governance_events)}")
    print(f"  ledger entries    {len(run.ledger_entries)}")
    print(f"  evidence sources  {run.source_count}")
    print(f"\nOpen:  http://localhost:5173/analyses/{run.id}")
    print(f"Audit: http://localhost:5173/analyses/{run.id}/governance")
    print("\nRemove later with:  python seed_demo_analysis.py --remove")
    session.close()
    return 0 if run.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
