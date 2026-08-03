from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        llm_model=(
            settings.ollama_model
            if settings.llm_provider.strip().lower() == "ollama"
            else settings.openai_model
        ),
        embedding_provider=settings.embedding_provider,
        embeddings_are_semantic=settings.embeddings_are_semantic,
        minimum_evidence_score=settings.governance_minimum_evidence_score,
    )
