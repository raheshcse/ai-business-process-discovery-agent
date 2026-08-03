"""Governed process-discovery run endpoints.

These are new. Before them the LangGraph workflow and the whole X-Verba
governance layer were unreachable over HTTP -- fully implemented, never
invoked. Runs execute in the background because five sequential LLM calls
cannot be held inside a request.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.schemas.analysis import (
    AnalysisRunCreate,
    AnalysisRunDetail,
    AnalysisRunSummary,
)
from app.services.analysis_run_service import (
    AnalysisRunNotFoundError,
    AnalysisRunService,
    NoIndexedEvidenceError,
    ProjectNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analyses"])

DbSession = Annotated[Session, Depends(get_db)]


async def _run_analysis_in_background(run_id: str) -> None:
    """Own the session: the request-scoped one is closed by then."""
    session = SessionLocal()
    try:
        await AnalysisRunService(session).execute_run(run_id)
    finally:
        session.close()


@router.post(
    "/projects/{project_id}/analyses",
    response_model=AnalysisRunDetail,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_analysis(
    project_id: str,
    payload: AnalysisRunCreate,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> AnalysisRunDetail:
    service = AnalysisRunService(db)
    try:
        run = service.create_run(
            project_id,
            question=payload.question,
            top_k=payload.top_k,
            minimum_similarity_score=payload.minimum_similarity_score,
            document_id_filters=payload.document_id_filters,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found") from exc
    except NoIndexedEvidenceError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    background_tasks.add_task(_run_analysis_in_background, run.id)
    return AnalysisRunDetail.model_validate(run)


@router.get(
    "/projects/{project_id}/analyses",
    response_model=list[AnalysisRunSummary],
)
def list_analyses(project_id: str, db: DbSession) -> list[AnalysisRunSummary]:
    try:
        runs = AnalysisRunService(db).list_runs(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found") from exc
    return [AnalysisRunSummary.model_validate(run) for run in runs]


@router.get("/analyses/{run_id}", response_model=AnalysisRunDetail)
def get_analysis(run_id: str, db: DbSession) -> AnalysisRunDetail:
    try:
        run = AnalysisRunService(db).get_run(run_id)
    except AnalysisRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found") from exc
    return AnalysisRunDetail.model_validate(run)
