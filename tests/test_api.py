"""API surface tests via FastAPI's test client."""

from fastapi.testclient import TestClient


def get_client(tmp_path):
    # Import late so conftest's offline env vars apply, and point the
    # module-level archive at a temp file.
    from src.api import routes

    routes.archive.filepath = str(tmp_path / "knowledge.jsonl")
    routes.archive._ensure_file_exists()
    routes.orchestrator.archive = routes.archive
    return TestClient(routes.app)


class TestAPI:
    def test_health(self, tmp_path):
        client = get_client(tmp_path)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_research_endpoint(self, tmp_path):
        client = get_client(tmp_path)
        resp = client.post(
            "/research",
            json={"query": "What is the outlook for solar energy?", "max_iterations": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["response"]
        assert data["doc_id"]
        assert isinstance(data["confidence"], float)

    def test_research_rejects_empty_query(self, tmp_path):
        client = get_client(tmp_path)
        resp = client.post("/research", json={"query": ""})
        assert resp.status_code == 422

    def test_search_and_stats(self, tmp_path):
        client = get_client(tmp_path)
        client.post("/research", json={"query": "Searchable geothermal query", "max_iterations": 1})

        found = client.get("/search/geothermal").json()
        assert found["total"] >= 1

        stats = client.get("/stats").json()
        assert stats["total_entries"] >= 1
