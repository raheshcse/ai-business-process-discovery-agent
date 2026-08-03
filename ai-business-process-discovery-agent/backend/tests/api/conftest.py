"""Isolated app fixture for the new HTTP surface.

Each test gets its own database, uploads directory and ledger file, and a
stub embedding provider that scores like a real semantic model. The bundled
deterministic provider hashes text, so its cosine scores are frequently
negative and the evidence gate would deny every run for reasons unrelated
to what is being tested.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.rag.embeddings.base import EmbeddingProvider

SAMPLE_TEXT = """Invoice Approval Process

The invoice approval process begins when a supplier emails an invoice to
accounts payable.

An accounts payable clerk manually keys the invoice into the finance system.
This step takes about ten minutes per invoice and causes transcription errors.

The invoice is routed to the department manager for approval. There is no
reminder, so invoices frequently wait three to five days at this step.

A second approver in finance re-checks the invoice against the purchase order.

Payment runs happen weekly on Thursdays.
"""


class StubSemanticEmbeddingProvider(EmbeddingProvider):
    """Positive-orthant unit vectors, so cosine scores land in a realistic
    range instead of straddling zero."""

    provider_name = "stub-semantic"
    model_name = "stub-v1"
    embedding_dimension = 64

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Text to embed must not be empty")
        digest = hashlib.shake_256(text.encode("utf-8")).digest(64)
        vector = [0.5 + (byte / 510.0) for byte in digest]
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("UPLOADS_DIRECTORY", str(tmp_path / "uploads"))
    monkeypatch.setenv("GOVERNANCE_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("GOVERNANCE_MINIMUM_EVIDENCE_SCORE", "0.35")

    import app.core.config as config_module

    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()
    monkeypatch.setattr(config_module, "settings", settings)

    for module_name in (
        "app.core.database",
        "app.core.composition",
        "app.api.routes.documents",
        "app.api.routes.governance",
        "app.api.routes.health",
        "app.services.indexing_service",
        "app.services.analysis_run_service",
        "app.api.routes.dashboard",
    ):
        module = __import__(module_name, fromlist=["settings"])
        if hasattr(module, "settings"):
            monkeypatch.setattr(module, "settings", settings)

    import app.core.database as database_module
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "SessionLocal", session_factory)

    import app.api.routes.documents as documents_module
    import app.api.routes.analyses as analyses_module

    monkeypatch.setattr(documents_module, "SessionLocal", session_factory)
    monkeypatch.setattr(analyses_module, "SessionLocal", session_factory)
    documents_module.get_document_storage.cache_clear()

    import app.core.composition as composition

    composition.reset_composition()
    monkeypatch.setattr(
        composition, "get_embedding_provider", lambda: StubSemanticEmbeddingProvider()
    )

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    composition.reset_composition()
    config_module.get_settings.cache_clear()


@pytest.fixture
def project(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Accounts Payable Review",
            "client_name": "Northwind Ltd",
            "department": "Finance",
            "industry": "Manufacturing",
            "objective": "Understand and improve the invoice approval process.",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def indexed_document(client: TestClient, project: dict) -> dict:
    response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("invoice-process.txt", SAMPLE_TEXT.encode(), "text/plain")},
    )
    assert response.status_code == 201
    return client.get(f"/api/v1/documents/{response.json()['id']}").json()
