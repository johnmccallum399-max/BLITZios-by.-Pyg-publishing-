"""Tests for tools: search fallbacks, JSON extraction, cost tracking."""

from src.tools.arxiv_tool import ArxivTool
from src.tools.model_router import CostTracker, ModelRouter, extract_json
from src.tools.web_search import WebSearchTool


class TestWebSearch:
    def test_mock_results_without_key(self):
        results = WebSearchTool(api_key="").search("anything")
        assert len(results) >= 1
        for item in results:
            assert item["mock"] is True
            assert item["source"] == "web"
            assert item["title"] and item["snippet"]


class TestArxiv:
    def test_offline_returns_empty(self):
        assert ArxivTool().search("transformers") == []

    def test_parse_atom_feed(self):
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/0000.0001</id>
            <title>Test Paper</title>
            <summary>A summary.</summary>
            <published>2025-01-01T00:00:00Z</published>
            <author><name>Jane Doe</name></author>
          </entry>
        </feed>"""
        results = ArxivTool()._parse(xml)
        assert len(results) == 1
        assert results[0]["title"] == "Test Paper"
        assert results[0]["source"] == "academic"
        assert results[0]["authors"] == ["Jane Doe"]


class TestModelRouter:
    def test_unavailable_offline(self):
        router = ModelRouter()
        assert router.available is False
        assert router.complete("sys", "prompt") is None
        assert router.complete_json("sys", "prompt") is None


class TestCostTracker:
    def test_budget_exhaustion(self):
        tracker = CostTracker(budget=0.10)
        assert not tracker.exhausted
        tracker.add(0.06)
        assert not tracker.exhausted
        tracker.add(0.05)
        assert tracker.exhausted
        assert tracker.calls == 2


class TestExtractJson:
    def test_plain_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_json_with_prose(self):
        assert extract_json('Here you go:\n[{"b": 2}]\nHope that helps!') == [{"b": 2}]

    def test_garbage_returns_none(self):
        assert extract_json("not json at all") is None
        assert extract_json("") is None
