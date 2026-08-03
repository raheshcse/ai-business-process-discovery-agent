import pytest


def test_analysis_requires_indexed_evidence(client, project):
    response = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does invoice approval work?"},
    )
    assert response.status_code == 409
    assert "indexed" in response.json()["detail"]


def test_analysis_runs_the_full_governed_workflow(client, project, indexed_document):
    response = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does the invoice approval process work end to end?"},
    )
    assert response.status_code == 202
    run_id = response.json()["id"]

    run = client.get(f"/api/v1/analyses/{run_id}").json()
    assert run["status"] == "completed"
    assert run["current_stage"] == "completed"
    assert run["governance_status"] == "allowed"
    assert run["terminal_state_name"] is None
    assert run["errors"] == []

    for stage in (
        "process_analysis",
        "bottleneck_analysis",
        "risk_analysis",
        "automation_analysis",
        "final_analysis",
    ):
        assert run[stage] is not None, stage
        assert run[stage]["findings"]

    assert run["source_count"] == 1
    assert run["citations"][0]["source_id"] == "Source 1"
    assert run["citations"][0]["document_id"] == indexed_document["id"]
    assert run["citations"][0]["filename"] == "invoice-process.txt"


def test_findings_only_cite_sources_that_exist(client, project, indexed_document):
    run_id = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does the invoice approval process work?"},
    ).json()["id"]
    run = client.get(f"/api/v1/analyses/{run_id}").json()

    available = {citation["source_id"] for citation in run["citations"]}
    for finding in run["final_analysis"]["findings"]:
        assert set(finding["evidence_source_ids"]).issubset(available)


def test_runs_are_listed_newest_first(client, project, indexed_document):
    for question in ("First question about approval?", "Second question about approval?"):
        client.post(
            f"/api/v1/projects/{project['id']}/analyses", json={"question": question}
        )

    runs = client.get(f"/api/v1/projects/{project['id']}/analyses").json()
    assert len(runs) == 2
    assert runs[0]["question"] == "Second question about approval?"


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "hi"},
        {"question": "   "},
        {"question": "Valid question here", "top_k": 0},
        {"question": "Valid question here", "minimum_similarity_score": 2},
        {"question": "Valid question here", "unexpected": True},
    ],
)
def test_rejects_invalid_requests(client, project, indexed_document, payload):
    response = client.post(
        f"/api/v1/projects/{project['id']}/analyses", json=payload
    )
    assert response.status_code == 422


def test_unknown_ids_return_404(client):
    assert client.get("/api/v1/analyses/missing").status_code == 404
    assert client.get("/api/v1/projects/missing/analyses").status_code == 404
    assert (
        client.post(
            "/api/v1/projects/missing/analyses", json={"question": "A real question?"}
        ).status_code
        == 404
    )
