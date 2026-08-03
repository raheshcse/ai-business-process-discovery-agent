"""Dashboard aggregates.

Computed from stored rows on request. Counting is deliberate: risk,
bottleneck and automation totals come from the most recent *completed* run
per project, so re-running an analysis updates a project's contribution
instead of inflating it.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import AnalysisRun
from app.models.document import Document, DocumentIndexStatus
from app.models.project import Project
from app.schemas.dashboard import (
    DashboardSummary,
    RecentActivityItem,
    SeverityBreakdown,
)
from app.workflows.process_discovery import WorkflowStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

DbSession = Annotated[Session, Depends(get_db)]

_RISK_CATEGORIES = {"risk", "control"}
_AUTOMATION_CATEGORIES = {"opportunity"}


@router.get("", response_model=DashboardSummary)
def get_dashboard(
    db: DbSession,
    activity_limit: Annotated[int, Query(ge=1, le=50)] = 8,
) -> DashboardSummary:
    project_count = db.scalar(select(func.count()).select_from(Project)) or 0

    document_counts = dict(
        db.execute(
            select(Document.index_status, func.count()).group_by(Document.index_status)
        ).all()
    )
    document_count = sum(document_counts.values())

    run_counts = dict(
        db.execute(
            select(AnalysisRun.status, func.count()).group_by(AnalysisRun.status)
        ).all()
    )

    latest_completed = _latest_completed_runs(db)

    severity = SeverityBreakdown()
    risk_findings = 0
    bottleneck_findings = 0
    automation_findings = 0

    for run in latest_completed:
        for finding in _findings(run.risk_analysis):
            if finding.get("category") in _RISK_CATEGORIES:
                risk_findings += 1
                _increment_severity(severity, finding.get("severity"))
        bottleneck_findings += len(_findings(run.bottleneck_analysis))
        automation_findings += sum(
            1
            for finding in _findings(run.automation_analysis)
            if finding.get("category") in _AUTOMATION_CATEGORIES
        )

    return DashboardSummary(
        project_count=project_count,
        document_count=document_count,
        indexed_document_count=document_counts.get(
            DocumentIndexStatus.INDEXED.value, 0
        ),
        documents_pending_count=(
            document_counts.get(DocumentIndexStatus.PENDING.value, 0)
            + document_counts.get(DocumentIndexStatus.PROCESSING.value, 0)
        ),
        documents_failed_count=document_counts.get(
            DocumentIndexStatus.FAILED.value, 0
        ),
        analysis_total_count=sum(run_counts.values()),
        analysis_completed_count=run_counts.get(WorkflowStatus.COMPLETED.value, 0),
        analysis_running_count=(
            run_counts.get(WorkflowStatus.RUNNING.value, 0)
            + run_counts.get(WorkflowStatus.PENDING.value, 0)
        ),
        analysis_failed_count=run_counts.get(WorkflowStatus.FAILED.value, 0),
        analysis_blocked_count=(
            run_counts.get(WorkflowStatus.GOVERNANCE_BLOCKED.value, 0)
            + run_counts.get(WorkflowStatus.INSUFFICIENT_EVIDENCE.value, 0)
        ),
        analysis_human_review_count=run_counts.get(
            WorkflowStatus.HUMAN_REVIEW_REQUIRED.value, 0
        ),
        risk_finding_count=risk_findings,
        risk_severity=severity,
        automation_opportunity_count=automation_findings,
        bottleneck_finding_count=bottleneck_findings,
        recent_activity=_recent_activity(db, activity_limit),
    )


def _latest_completed_runs(db: Session) -> list[AnalysisRun]:
    runs = db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.status == WorkflowStatus.COMPLETED.value)
        .order_by(AnalysisRun.created_at.desc())
    ).scalars()
    seen: set[str] = set()
    latest: list[AnalysisRun] = []
    for run in runs:
        if run.project_id in seen:
            continue
        seen.add(run.project_id)
        latest.append(run)
    return latest


def _findings(analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(analysis, dict):
        return []
    findings = analysis.get("findings")
    return [item for item in findings if isinstance(item, dict)] if findings else []


def _increment_severity(breakdown: SeverityBreakdown, severity: Any) -> None:
    if isinstance(severity, str) and hasattr(breakdown, severity):
        setattr(breakdown, severity, getattr(breakdown, severity) + 1)


def _recent_activity(db: Session, limit: int) -> list[RecentActivityItem]:
    items: list[RecentActivityItem] = []

    for run, project_name in db.execute(
        select(AnalysisRun, Project.name)
        .join(Project, Project.id == AnalysisRun.project_id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(limit)
    ).all():
        items.append(
            RecentActivityItem(
                kind="analysis",
                title=run.question,
                subtitle=f"Analysis {run.status.replace('_', ' ')}",
                project_id=run.project_id,
                project_name=project_name,
                analysis_run_id=run.id,
                status=run.status,
                occurred_at=run.created_at,
            )
        )

    for document, project_name in db.execute(
        select(Document, Project.name)
        .join(Project, Project.id == Document.project_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
    ).all():
        items.append(
            RecentActivityItem(
                kind="document",
                title=document.original_filename,
                subtitle=f"Document {document.index_status}",
                project_id=document.project_id,
                project_name=project_name,
                analysis_run_id=None,
                status=document.index_status,
                occurred_at=document.created_at,
            )
        )

    for project in db.execute(
        select(Project).order_by(Project.created_at.desc()).limit(limit)
    ).scalars():
        items.append(
            RecentActivityItem(
                kind="project",
                title=project.name,
                subtitle="Project created",
                project_id=project.id,
                project_name=project.name,
                analysis_run_id=None,
                status=project.status,
                occurred_at=project.created_at,
            )
        )

    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items[:limit]
