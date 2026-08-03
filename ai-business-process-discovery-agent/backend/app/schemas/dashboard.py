from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SeverityBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    informational: int = 0


class RecentActivityItem(BaseModel):
    kind: str
    title: str
    subtitle: str | None
    project_id: str | None
    project_name: str | None
    analysis_run_id: str | None
    status: str | None
    occurred_at: datetime


class DashboardSummary(BaseModel):
    """Aggregates computed from real rows -- no fabricated numbers.

    Risk and automation counts come from findings on the most recent
    completed run per project, so a project is counted once rather than
    once per re-run.
    """

    project_count: int
    document_count: int
    indexed_document_count: int
    documents_pending_count: int
    documents_failed_count: int

    analysis_total_count: int
    analysis_completed_count: int
    analysis_running_count: int
    analysis_failed_count: int
    analysis_blocked_count: int
    analysis_human_review_count: int

    risk_finding_count: int
    risk_severity: SeverityBreakdown
    automation_opportunity_count: int
    bottleneck_finding_count: int

    recent_activity: list[RecentActivityItem]
