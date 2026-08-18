import json
import logging
import socket
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

# Short on purpose: this is a liveness probe the UI polls, not a workload.
_PROBE_TIMEOUT_SECONDS = 3.0


def _installed_ollama_models() -> tuple[set[str] | None, str | None]:
    """Ask Ollama what it actually has. Returns (models, error)."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        with urlopen(url, timeout=_PROBE_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, socket.timeout, TimeoutError):
        return None, (
            f"Cannot reach Ollama at {settings.ollama_base_url}. "
            f"Start it with: ollama serve"
        )
    except (json.JSONDecodeError, OSError):
        logger.exception("Ollama tag listing could not be parsed")
        return None, "Ollama responded but its model list could not be read."

    names: set[str] = set()
    for model in payload.get("models") or []:
        name = str(model.get("name", ""))
        if not name:
            continue
        names.add(name)
        # Ollama reports "llama3.2:latest"; config usually says "llama3.2".
        names.add(name.split(":", 1)[0])
    return names, None


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    llm_provider = settings.llm_provider.strip().lower()
    llm_model = (
        settings.ollama_model if llm_provider == "ollama" else settings.openai_model
    )
    uses_ollama = (
        llm_provider == "ollama"
        or settings.embedding_provider.strip().lower() == "ollama"
    )

    reachable = True
    llm_available = True
    embedding_available = True
    error: str | None = None

    if uses_ollama:
        installed, error = _installed_ollama_models()
        if installed is None:
            reachable = False
            llm_available = llm_provider != "ollama"
            embedding_available = (
                settings.embedding_provider.strip().lower() != "ollama"
            )
        else:
            missing: list[str] = []
            if llm_provider == "ollama":
                llm_available = settings.ollama_model in installed
                if not llm_available:
                    missing.append(settings.ollama_model)
            if settings.embedding_provider.strip().lower() == "ollama":
                embedding_available = settings.ollama_embedding_model in installed
                if not embedding_available:
                    missing.append(settings.ollama_embedding_model)
            if missing:
                error = (
                    "Ollama is running but these models are not installed: "
                    + ", ".join(missing)
                    + ". Install with: "
                    + "; ".join(f"ollama pull {name}" for name in missing)
                )

    healthy = reachable and llm_available and embedding_available
    return HealthResponse(
        status="healthy" if healthy else "degraded",
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        llm_model=llm_model,
        embedding_provider=settings.embedding_provider,
        embeddings_are_semantic=settings.embeddings_are_semantic,
        minimum_evidence_score=settings.governance_minimum_evidence_score,
        provider_reachable=reachable,
        llm_model_available=llm_available,
        embedding_model_available=embedding_available,
        provider_error=error,
    )
