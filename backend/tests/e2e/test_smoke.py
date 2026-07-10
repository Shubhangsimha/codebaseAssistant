"""
End-to-end smoke test: ingest a tiny public repo → chat → assert citation returned.

Run with:
    pytest tests/e2e/ -v -s

Requires the backend to be running at http://localhost:8000 and valid API keys in .env.
Skip with: pytest tests/ --ignore=tests/e2e
"""
import json
import time

import pytest
import requests

BASE = "http://localhost:8000"
# Small, stable public repo (~50 Python files) — fast to clone + parse
TEST_REPO = "https://github.com/pallets/click"
TIMEOUT = 600  # seconds to wait for ingestion to reach READY


def _get(path, **kwargs):
    return requests.get(f"{BASE}{path}", **kwargs)


def _post(path, **kwargs):
    return requests.post(f"{BASE}{path}", **kwargs)


def _delete(path, **kwargs):
    return requests.delete(f"{BASE}{path}", **kwargs)


@pytest.fixture(scope="module")
def project_id():
    """Create a project, wait for it to reach READY, yield its ID, then delete it."""
    # Create
    r = _post("/projects", json={"name": "e2e-smoke", "source_type": "github", "source_url": TEST_REPO}, timeout=30)
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]

    # Ingest — returns 202 immediately; pipeline runs in background
    r = _post(f"/projects/{pid}/ingest", timeout=30)
    assert r.status_code == 202, r.text

    # Poll until ready
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        r = _get(f"/projects/{pid}/status", timeout=10)
        assert r.status_code == 200
        status = r.json()["status"]
        if status == "ready":
            break
        if status == "failed":
            pytest.fail(f"Ingestion failed: {r.json().get('error_message')}")
        time.sleep(4)
    else:
        pytest.fail(f"Ingestion did not complete within {TIMEOUT}s")

    yield pid

    # Cleanup
    _delete(f"/projects/{pid}", timeout=10)


def test_project_is_ready(project_id):
    r = _get(f"/projects/{project_id}/status", timeout=10)
    assert r.json()["status"] == "ready"


def test_file_tree_non_empty(project_id):
    r = _get(f"/projects/{project_id}/files", timeout=10)
    assert r.status_code == 200
    tree = r.json()["tree"]
    assert len(tree) > 0, "File tree should not be empty"


def test_search_returns_chunks(project_id):
    r = _get(f"/projects/{project_id}/search", params={"q": "command", "top_k": 5}, timeout=15)
    assert r.status_code == 200
    results = r.json()
    assert len(results) > 0, "Search should return at least one chunk"
    assert "chunk_id" in results[0]
    assert "file_path" in results[0]


def test_chat_returns_cited_answer(project_id):
    """The core RAG assertion: a chat response must contain at least one citation."""
    with requests.post(
        f"{BASE}/projects/{project_id}/chat",
        json={"message": "What does this project do?"},
        headers={"Accept": "text/event-stream"},
        stream=True,
        timeout=60,
    ) as resp:
        assert resp.status_code == 200

        citations_event = None
        done_event = None

        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data: "):
                continue
            try:
                ev = json.loads(raw_line[6:])
            except json.JSONDecodeError:
                continue

            if ev.get("type") == "citations":
                citations_event = ev
            if ev.get("type") == "done":
                done_event = ev
                break

    assert done_event is not None, "Stream must end with a 'done' event"
    assert citations_event is not None, "Response must include a 'citations' event"
    citations = citations_event.get("citations", [])
    assert len(citations) > 0, "At least one citation must be returned"

    first = citations[0]
    assert "file" in first, "Citation must have a 'file' key"
    assert "line_start" in first, "Citation must have a 'line_start' key"


def test_language_breakdown(project_id):
    r = _get(f"/projects/{project_id}/languages", timeout=10)
    assert r.status_code == 200
    langs = r.json()
    assert len(langs) > 0
    assert "language" in langs[0]
    assert "percent" in langs[0]


def test_graph_endpoint(project_id):
    r = _get(f"/projects/{project_id}/graph", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "edges" in data
    assert "cycles" in data
