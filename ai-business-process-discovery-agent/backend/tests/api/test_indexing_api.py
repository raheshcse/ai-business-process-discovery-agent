from tests.api.conftest import SAMPLE_TEXT


def test_upload_indexes_document_in_background(client, project):
    response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("process.txt", SAMPLE_TEXT.encode(), "text/plain")},
    )
    assert response.status_code == 201
    # The response is returned before indexing runs.
    assert response.json()["index_status"] == "pending"

    document = client.get(f"/api/v1/documents/{response.json()['id']}").json()
    assert document["index_status"] == "indexed"
    assert document["chunk_count"] >= 1
    assert document["word_count"] > 0
    assert document["detected_document_type"] == "txt"
    assert document["index_error"] is None


def test_unreadable_document_is_marked_failed_not_indexed(client, project):
    response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("empty.txt", b"   \n  \n ", "text/plain")},
    )
    assert response.status_code == 201

    document = client.get(f"/api/v1/documents/{response.json()['id']}").json()
    assert document["index_status"] == "failed"
    assert document["index_error"]
    assert document["chunk_count"] == 0


def test_rejects_unsupported_file_type(client, project):
    response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("notes.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_reindex_recovers_a_failed_document(client, project, tmp_path):
    upload = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("empty.txt", b"  ", "text/plain")},
    ).json()
    assert client.get(f"/api/v1/documents/{upload['id']}").json()["index_status"] == (
        "failed"
    )

    from app.core.config import settings
    from pathlib import Path

    Path(settings.uploads_directory).mkdir(parents=True, exist_ok=True)
    stored = client.get(f"/api/v1/documents/{upload['id']}").json()
    # Replace the stored bytes with readable content, then reindex.
    from app.core.database import SessionLocal
    from app.models import Document

    session = SessionLocal()
    key = session.get(Document, stored["id"]).storage_key
    session.close()
    (Path(settings.uploads_directory) / key).write_text(SAMPLE_TEXT)

    response = client.post(f"/api/v1/documents/{upload['id']}/reindex")
    assert response.status_code == 202
    assert client.get(f"/api/v1/documents/{upload['id']}").json()["index_status"] == (
        "indexed"
    )
