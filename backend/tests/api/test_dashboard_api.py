def test_dashboard_is_empty_before_any_work(client):
    summary = client.get("/api/v1/dashboard").json()
    assert summary["project_count"] == 0
    assert summary["document_count"] == 0
    assert summary["analysis_total_count"] == 0
    assert summary["recent_activity"] == []


def test_dashboard_counts_real_rows(client, project, indexed_document):
    client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does the invoice approval process work?"},
    )

    summary = client.get("/api/v1/dashboard").json()
    assert summary["project_count"] == 1
    assert summary["document_count"] == 1
    assert summary["indexed_document_count"] == 1
    assert summary["analysis_completed_count"] == 1
    assert summary["risk_finding_count"] == 1
    assert summary["automation_opportunity_count"] == 1
    assert summary["bottleneck_finding_count"] == 1
    assert sum(summary["risk_severity"].values()) == summary["risk_finding_count"]


def test_rerunning_an_analysis_does_not_double_count(client, project, indexed_document):
    for _ in range(3):
        client.post(
            f"/api/v1/projects/{project['id']}/analyses",
            json={"question": "How does the invoice approval process work?"},
        )

    summary = client.get("/api/v1/dashboard").json()
    assert summary["analysis_total_count"] == 3
    # Only the latest completed run per project contributes findings.
    assert summary["risk_finding_count"] == 1


def test_recent_activity_is_newest_first(client, project, indexed_document):
    activity = client.get("/api/v1/dashboard").json()["recent_activity"]
    assert activity
    timestamps = [item["occurred_at"] for item in activity]
    assert timestamps == sorted(timestamps, reverse=True)
    assert {item["kind"] for item in activity} <= {"project", "document", "analysis"}


def test_health_reports_provider_configuration(client):
    health = client.get("/api/v1/health").json()
    assert health["status"] == "healthy"
    assert health["llm_provider"] == "mock"
    # `local` embeddings are not semantic; the UI needs to be able to say so.
    assert health["embeddings_are_semantic"] is False
