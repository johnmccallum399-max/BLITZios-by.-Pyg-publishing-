"""Unit tests for each agent module (offline / heuristic mode)."""

from src.agents.gap_finder import GapFinder
from src.agents.intent_engine import IntentEngine
from src.agents.planner import TaskPlanner
from src.agents.researcher import Researcher
from src.agents.validator import Validator


class TestIntentEngine:
    def test_market_query(self):
        intent = IntentEngine().classify(
            "What are the top 3 trends in the AI legal tech market for 2025?"
        )
        assert intent["domain"] == "Market"
        assert "objective" in intent
        assert isinstance(intent["entities"], list)
        assert isinstance(intent["assumptions"], list)

    def test_technical_query(self):
        intent = IntentEngine().classify(
            "What's the best open-source vector database for production use?"
        )
        assert intent["domain"] == "Technical"

    def test_financial_query(self):
        intent = IntentEngine().classify(
            "What's the projected CAGR for the generative AI market through 2028?"
        )
        # 'CAGR' + 'market' hit both Financial and Market keywords
        assert intent["domain"] in ("Financial", "Market", "Mixed")

    def test_unknown_query_defaults_to_mixed(self):
        intent = IntentEngine().classify("Tell me about ducks")
        assert intent["domain"] == "Mixed"


class TestTaskPlanner:
    def test_decomposes_into_3_to_5_tasks(self):
        tasks = TaskPlanner().decompose(
            "State of the electric vehicle market", {"domain": "Market"}
        )
        assert 3 <= len(tasks) <= 5
        for task in tasks:
            assert task["id"]
            assert task["description"]
            assert task["priority"] in ("High", "Medium", "Low")
            assert isinstance(task["dependencies"], list)

    def test_dag_dependencies_reference_real_tasks(self):
        tasks = TaskPlanner().decompose("Anything at all", {"domain": "Technical"})
        ids = {t["id"] for t in tasks}
        for task in tasks:
            for dep in task["dependencies"]:
                assert dep in ids

    def test_refinement_pass_plans_from_gaps(self):
        tasks = TaskPlanner().decompose(
            "EV market",
            {"domain": "Market"},
            gaps=["Missing competitor pricing data", "No regulatory analysis"],
            follow_up="What do regulators require?",
            iteration=1,
        )
        assert len(tasks) >= 2
        descriptions = " ".join(t["description"] for t in tasks)
        assert "regulator" in descriptions.lower() or "competitor" in descriptions.lower()


class TestResearcher:
    def test_gathers_evidence_per_task(self):
        tasks = [
            {"id": "t1", "title": "Overview", "description": "EV market state"},
            {"id": "t2", "title": "Players", "description": "EV manufacturers"},
        ]
        results = Researcher().execute(tasks)
        assert len(results) == 2
        for result in results:
            assert result["status"] == "completed"
            assert result["source_count"] >= 1
            for item in result["evidence"]:
                assert item["task_id"] == result["task_id"]

    def test_empty_task_list(self):
        assert Researcher().execute([]) == []


class TestValidator:
    def test_scores_evidence(self):
        evidence = [
            {"title": "A", "snippet": "x" * 200, "source": "academic", "task_id": "t1"},
            {"title": "B", "snippet": "y" * 50, "source": "web", "task_id": "t1"},
        ]
        scores = Validator().validate(evidence)
        assert len(scores["individual_scores"]) == 2
        assert 0 <= scores["average_confidence"] <= 1
        # Academic sources must outscore generic web sources.
        academic, web = scores["individual_scores"]
        assert academic["overall_score"] > web["overall_score"]

    def test_mock_evidence_caps_confidence(self):
        evidence = [
            {"title": "M", "snippet": "z" * 300, "source": "academic", "mock": True}
        ]
        scores = Validator().validate(evidence)
        assert scores["average_confidence"] <= 0.4

    def test_empty_evidence(self):
        scores = Validator().validate([])
        assert scores["average_confidence"] == 0.0
        assert scores["contradictions"] == []


class TestGapFinder:
    def test_finds_gaps_and_follow_up(self):
        result = GapFinder().find_gaps(
            query="EV market outlook",
            intent={"objective": "understand EV market", "assumptions": ["EVs keep growing"]},
            tasks=[{"id": "t1", "title": "Overview"}, {"id": "t2", "title": "Uncovered"}],
            evidence=[{"title": "A", "source": "web", "task_id": "t1", "mock": True}],
            scores={"average_confidence": 0.3, "contradictions_checked": False},
        )
        assert result["gaps"], "low-confidence single-source run must produce gaps"
        assert result["follow_up_question"]
        # Task t2 had no evidence: that gap must be flagged.
        assert any("Uncovered" in g for g in result["gaps"])
