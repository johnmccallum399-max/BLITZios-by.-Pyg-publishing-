"""Integration tests: the full intelligence loop, offline and deterministic."""

import json

from src.core.orchestrator import BLITZOrchestrator
from src.core.state_manager import KnowledgeArchive


class TestBLITZOrchestrator:
    def test_orchestrator_initialization(self, archive):
        orchestrator = BLITZOrchestrator(archive=archive)
        assert orchestrator.workflow is not None

    def test_full_loop_market_query(self, archive):
        orchestrator = BLITZOrchestrator(archive=archive)
        result = orchestrator.run(
            "What are the top 3 trends in AI-powered legal tech for 2025?"
        )
        assert result["success"] is True
        state = result["state"]

        # MODULE_A: intent
        assert state["intent"]["domain"] in (
            "Market", "Technical", "Financial", "Strategic", "Mixed",
        )
        # MODULE_B: 3-5 tasks
        assert 2 <= len(state["tasks"]) <= 5
        # MODULE_C: evidence gathered
        assert len(state["evidence"]) >= 2
        # MODULE_D: scored
        assert "average_confidence" in state["scores"]
        # MODULE_E: gaps + follow-up
        assert isinstance(state["gaps"], list)
        assert state["follow_up"]
        # MODULE_F: human-readable response with confidence and sources
        assert "Confidence Score" in state["response"]
        assert "Follow-up Question" in state["response"]

    def test_iteration_is_bounded(self, archive):
        orchestrator = BLITZOrchestrator(archive=archive)
        result = orchestrator.run("Anything with permanent gaps", max_iterations=2)
        assert result["success"] is True
        # In offline mode gaps always exist (mock data), so the loop must
        # run exactly to the bound and stop — never beyond.
        assert result["state"]["iteration"] == 2

    def test_cost_is_zero_offline(self, archive):
        orchestrator = BLITZOrchestrator(archive=archive)
        result = orchestrator.run("Cheap question")
        assert result["state"]["cost"] == 0.0

    def test_persists_to_archive(self, archive):
        orchestrator = BLITZOrchestrator(archive=archive)
        result = orchestrator.run("Persistence check query about quantum computing")
        assert result["doc_id"]

        stored = archive.get(result["doc_id"])
        assert stored is not None
        assert stored["query"] == "Persistence check query about quantum computing"

        # Full-text search finds it by a word that only appears in the query.
        hits = archive.search("quantum")
        assert any(r["id"] == result["doc_id"] for r in hits)

    def test_evidence_deduplicated_across_iterations(self, archive):
        orchestrator = BLITZOrchestrator(archive=archive)
        result = orchestrator.run("Dedup check", max_iterations=3)
        evidence = result["state"]["evidence"]
        keys = [(e.get("link"), e.get("title")) for e in evidence]
        assert len(keys) == len(set(keys))


class TestKnowledgeArchive:
    def test_stats_accumulate(self, archive):
        orchestrator = BLITZOrchestrator(archive=archive)
        orchestrator.run("First query")
        orchestrator.run("Second query")
        stats = archive.get_stats()
        assert stats["total_entries"] == 2

    def test_jsonl_is_valid(self, archive):
        BLITZOrchestrator(archive=archive).run("JSONL validity check")
        with open(archive.filepath) as f:
            for line in f:
                record = json.loads(line)  # must not raise
                assert "id" in record and "response" in record
