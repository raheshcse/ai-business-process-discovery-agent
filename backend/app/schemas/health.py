from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Service health plus the provider facts the UI needs.

    The provider fields are additive. They exist because a deployment
    using the non-semantic `local` embedding provider will see analyses
    blocked at the evidence gate for reasons unrelated to its documents,
    and the interface should say so rather than let it look like a
    document problem.

    `models_available` and `provider_error` were added after a green
    "ollama - llama3.2" badge was shown while `llama3.2` was not installed
    at all. Reporting configuration as if it were health is worse than
    reporting nothing: it actively misdirects.
    """

    status: str
    application: str
    version: str
    environment: str

    llm_provider: str = "unknown"
    llm_model: str = "unknown"
    embedding_provider: str = "unknown"
    embeddings_are_semantic: bool = True
    minimum_evidence_score: float = 0.0

    # Reachability, not configuration.
    provider_reachable: bool = True
    llm_model_available: bool = True
    embedding_model_available: bool = True
    provider_error: str | None = None
