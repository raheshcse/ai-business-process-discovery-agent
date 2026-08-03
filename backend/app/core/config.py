from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Business Process Discovery Agent"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./business_process_discovery.db"
    cors_origins: str = "http://localhost:5173"
    uploads_directory: str = "uploads"
    max_upload_size_bytes: int = 25 * 1024 * 1024

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 60.0
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 2_000

    # --- RAG indexing / retrieval -------------------------------------
    # `ollama` is the default because it is the only provider whose
    # similarity scores are semantic. The bundled `local` provider hashes
    # text, so its cosine scores are effectively random and frequently
    # negative -- and the process-discovery PreNode denies any citation
    # scoring below `governance_minimum_evidence_score`, which means a
    # `local` run is blocked at the first gate roughly half the time.
    # Keep `local` for unit tests, not for running analyses.
    embedding_provider: str = "ollama"
    ollama_embedding_model: str = "nomic-embed-text"
    local_embedding_dimension: int = 128
    chunk_size: int = 1_000
    chunk_overlap: int = 200
    max_context_characters: int = 12_000
    retrieval_top_k: int = 5

    # --- Governance ----------------------------------------------------
    # `governance_minimum_evidence_score` is the citation-score floor the
    # process-discovery PreNode enforces. `ProcessDiscoveryGovernanceConfig`
    # constrains it to [0.0, 1.0]. 0.35 is a deliberately modest floor for
    # `nomic-embed-text`; raise it as retrieval quality is tuned.
    governance_gamma_threshold: float = 1.1
    governance_minimum_evidence_score: float = 0.35
    governance_minimum_process_findings: int = 1
    governance_ledger_path: str = "governance_ledger.jsonl"
    governance_ledger_fsync: bool = False
    # Audit check 1 (`no_monitoring_gaps`) needs a domain-chosen cadence.
    # None skips it rather than inventing a threshold.
    governance_max_monitor_gap_seconds: float | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def embeddings_are_semantic(self) -> bool:
        """False when retrieval scores carry no meaning.

        The UI surfaces this, because a `local` deployment will see runs
        blocked at the evidence gate for reasons that have nothing to do
        with the documents.
        """
        return self.embedding_provider.strip().lower() == "ollama"

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
