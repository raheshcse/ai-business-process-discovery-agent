"""The health badge must report reachability, not configuration.

Regression: the UI showed a green "ollama - llama3.2" badge while llama3.2
was not installed, because /health only echoed settings. Two debugging
sessions were spent trusting that badge.
"""

import json
from io import BytesIO
from urllib.error import URLError

import pytest


def _tags_response(*names: str) -> BytesIO:
    payload = json.dumps({"models": [{"name": n} for n in names]}).encode()
    stream = BytesIO(payload)
    stream.__enter__ = lambda: stream  # type: ignore[method-assign]
    stream.__exit__ = lambda *a: None  # type: ignore[method-assign]
    return stream


@pytest.fixture
def ollama_models(monkeypatch):
    """Patch the health route's urlopen with a controllable fake."""
    import app.api.routes.health as health_module

    state: dict = {"names": ("llama3.2:latest", "nomic-embed-text:latest"),
                   "unreachable": False}

    def fake_urlopen(url, timeout=None):
        if state["unreachable"]:
            raise URLError("connection refused")
        return _tags_response(*state["names"])

    monkeypatch.setattr(health_module, "urlopen", fake_urlopen)
    return state


def test_reports_healthy_when_models_are_installed(client, ollama_models, monkeypatch):
    import app.api.routes.health as health_module

    monkeypatch.setattr(health_module.settings, "llm_provider", "ollama")
    monkeypatch.setattr(health_module.settings, "embedding_provider", "ollama")

    health = client.get("/api/v1/health").json()

    assert health["status"] == "healthy"
    assert health["provider_reachable"] is True
    assert health["llm_model_available"] is True
    assert health["embedding_model_available"] is True
    assert health["provider_error"] is None


def test_missing_llm_model_is_reported_with_a_pull_command(
    client, ollama_models, monkeypatch
):
    import app.api.routes.health as health_module

    monkeypatch.setattr(health_module.settings, "llm_provider", "ollama")
    monkeypatch.setattr(health_module.settings, "embedding_provider", "ollama")
    ollama_models["names"] = ("nomic-embed-text:latest",)  # llama3.2 absent

    health = client.get("/api/v1/health").json()

    assert health["status"] == "degraded"
    assert health["llm_model_available"] is False
    assert health["embedding_model_available"] is True
    assert "ollama pull llama3.2" in health["provider_error"]


def test_unreachable_ollama_is_not_reported_as_healthy(
    client, ollama_models, monkeypatch
):
    import app.api.routes.health as health_module

    monkeypatch.setattr(health_module.settings, "llm_provider", "ollama")
    monkeypatch.setattr(health_module.settings, "embedding_provider", "ollama")
    ollama_models["unreachable"] = True

    health = client.get("/api/v1/health").json()

    assert health["status"] == "degraded"
    assert health["provider_reachable"] is False
    assert "ollama serve" in health["provider_error"]


def test_tag_matching_tolerates_the_latest_suffix(client, ollama_models, monkeypatch):
    """Config says `llama3.2`; Ollama reports `llama3.2:latest`."""
    import app.api.routes.health as health_module

    monkeypatch.setattr(health_module.settings, "llm_provider", "ollama")
    monkeypatch.setattr(health_module.settings, "embedding_provider", "ollama")
    monkeypatch.setattr(health_module.settings, "ollama_model", "llama3.2")

    assert client.get("/api/v1/health").json()["llm_model_available"] is True


def test_non_ollama_setup_skips_the_probe_entirely(client):
    """LLM_PROVIDER=mock and EMBEDDING_PROVIDER=local -- nothing to probe."""
    health = client.get("/api/v1/health").json()
    assert health["status"] == "healthy"
    assert health["provider_reachable"] is True
    assert health["provider_error"] is None
