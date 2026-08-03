def test_governance_report_exposes_the_decision_trail(
    client, project, indexed_document
):
    run_id = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does the invoice approval process work?"},
    ).json()["id"]

    report = client.get(f"/api/v1/analyses/{run_id}/governance").json()

    # Five PreNodes and six invariants run on the happy path.
    assert len(report["decisions"]) == 11
    assert {decision["outcome"] for decision in report["decisions"]} == {"allowed"}
    pre_nodes = [d for d in report["decisions"] if d["construct_type"] == "pre_node"]
    invariants = [d for d in report["decisions"] if d["construct_type"] == "invariant"]
    assert len(pre_nodes) == 5
    assert len(invariants) == 6

    assert report["chain_verified"] is True
    assert report["ledger_entries"]
    assert report["checkpoint_hash"]


def test_ledger_entries_form_an_unbroken_hash_chain(client, project, indexed_document):
    run_id = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does the invoice approval process work?"},
    ).json()["id"]

    entries = client.get(f"/api/v1/analyses/{run_id}/governance").json()[
        "ledger_entries"
    ]
    assert entries == sorted(entries, key=lambda entry: entry["sequence"])
    for previous, current in zip(entries, entries[1:]):
        assert current["prev_hash"] == previous["entry_hash"]


def test_ledger_payloads_never_leak_document_content(
    client, project, indexed_document
):
    run_id = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does the invoice approval process work?"},
    ).json()["id"]

    report = client.get(f"/api/v1/analyses/{run_id}/governance").json()
    allowed_keys = {
        "node_name",
        "outcome",
        "source_count",
        "confidence",
        "terminal_state_name",
        "drift_detected",
        "result",
    }
    for entry in report["ledger_entries"]:
        assert set(entry["payload"]).issubset(allowed_keys)
        assert "invoice" not in str(entry["payload"]).lower()


def test_audit_reports_all_five_checks(client, project, indexed_document):
    run_id = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={"question": "How does the invoice approval process work?"},
    ).json()["id"]

    checks = client.get(f"/api/v1/analyses/{run_id}/governance").json()["audit_checks"]
    assert len(checks) == 5
    # A clean run writes no TERMINAL entry, so the human-authorisation
    # check passes vacuously rather than because sign-off happened.
    assert all(check["passed"] for check in checks)


def test_a_stopped_run_reports_the_missing_human_sign_off(
    client, project, indexed_document
):
    """A terminal state with no human approval must be shown as a failure.

    An impossible similarity floor forces INSUFFICIENT_EVIDENCE, which
    writes a TERMINAL ledger entry. This application has no approval
    workflow, so audit check 5 must fail -- and the API must say so rather
    than presenting the run as fully governed.
    """
    run_id = client.post(
        f"/api/v1/projects/{project['id']}/analyses",
        json={
            "question": "How does the invoice approval process work?",
            "minimum_similarity_score": 0.999999,
        },
    ).json()["id"]

    run = client.get(f"/api/v1/analyses/{run_id}").json()
    assert run["status"] == "insufficient_evidence"
    assert run["terminal_state_name"] == "INSUFFICIENT_EVIDENCE"
    assert run["final_analysis"] is None

    report = client.get(f"/api/v1/analyses/{run_id}/governance").json()
    by_name = {check["name"]: check for check in report["audit_checks"]}
    unmet = by_name["terminal_has_human_authorised_transition"]
    assert unmet["passed"] is False
    assert "no human approval" in unmet["explanation"]
    assert unmet["violation_count"] >= 1


def test_catalogue_describes_every_gate(client):
    catalogue = client.get("/api/v1/governance/catalogue").json()
    assert len(catalogue["pre_nodes"]) == 5
    assert len(catalogue["invariants"]) == 6
    assert len(catalogue["terminal_states"]) == 4
    assert catalogue["gamma_threshold"] > 0


def test_governance_report_404s_for_unknown_run(client):
    assert client.get("/api/v1/analyses/missing/governance").status_code == 404
