"""Tests for the Phase 2 research sources: Wikipedia, GitHub, NewsAPI.

No test touches the network. Live paths are exercised by replacing
requests.get with a fake that records the call and returns canned JSON.
"""

import pytest

from src.agents.researcher import Researcher
from src.agents.validator import Validator
from src.core.config import Config
from src.tools import github_tool, news_tool, wikipedia_tool
from src.tools.github_tool import GitHubTool
from src.tools.news_tool import NewsTool
from src.tools.wikipedia_tool import WikipediaTool


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def fake_get(payload, calls, status=200):
    def _get(url, params=None, headers=None, timeout=None):
        calls.append({"url": url, "params": params, "headers": headers or {}})
        return FakeResponse(payload, status)
    return _get


def exploding_get(*args, **kwargs):
    raise AssertionError("network must not be called")


@pytest.fixture
def online(monkeypatch):
    monkeypatch.setattr(Config, "OFFLINE_MODE", False)


WIKI_PAYLOAD = {
    "query": {
        "search": [
            {
                "title": "Legal technology",
                "snippet": 'Use of <span class="searchmatch">technology</span> &amp; software in law',
                "timestamp": "2025-06-01T12:00:00Z",
            },
            {"title": "", "snippet": "untitled entries are skipped"},
        ]
    }
}

GITHUB_PAYLOAD = {
    "items": [
        {
            "full_name": "acme/vectordb",
            "description": "A fast vector database",
            "stargazers_count": 12345,
            "language": "Rust",
            "html_url": "https://github.com/acme/vectordb",
            "pushed_at": "2025-10-01T00:00:00Z",
        }
    ]
}

NEWS_PAYLOAD = {
    "status": "ok",
    "articles": [
        {
            "title": "Legal AI startup raises funding",
            "description": "A round led by investors.",
            "url": "https://news.example/legal-ai",
            "publishedAt": "2025-09-15T08:00:00Z",
            "source": {"name": "Example Times"},
        },
        {"title": "[Removed]", "url": "https://news.example/removed"},
    ],
}


class TestWikipedia:
    def test_offline_returns_empty_without_network(self, monkeypatch):
        monkeypatch.setattr(wikipedia_tool.requests, "get", exploding_get)
        assert WikipediaTool().search("legal tech") == []

    def test_live_search_parses_and_cleans(self, online, monkeypatch):
        calls = []
        monkeypatch.setattr(wikipedia_tool.requests, "get", fake_get(WIKI_PAYLOAD, calls))
        results = WikipediaTool().search("legal tech", max_results=2)

        assert len(results) == 1
        item = results[0]
        assert item["source"] == "encyclopedia"
        assert item["snippet"] == "Use of technology & software in law"
        assert item["link"] == "https://en.wikipedia.org/wiki/Legal_technology"
        assert item["published"] == "2025-06-01T12:00:00Z"
        assert "mock" not in item
        assert calls[0]["params"]["srsearch"] == "legal tech"
        assert "BLITZ" in calls[0]["headers"]["User-Agent"]

    def test_http_error_degrades_to_empty(self, online, monkeypatch):
        monkeypatch.setattr(wikipedia_tool.requests, "get", fake_get({}, [], status=503))
        assert WikipediaTool().search("anything") == []


class TestGitHub:
    def test_offline_returns_empty_without_network(self, monkeypatch):
        monkeypatch.setattr(github_tool.requests, "get", exploding_get)
        assert GitHubTool().search("vector database") == []

    def test_live_search_parses(self, online, monkeypatch):
        calls = []
        monkeypatch.setattr(github_tool.requests, "get", fake_get(GITHUB_PAYLOAD, calls))
        results = GitHubTool(token="").search("vector database")

        assert len(results) == 1
        item = results[0]
        assert item["source"] == "code"
        assert item["title"] == "GitHub: acme/vectordb"
        assert "12,345 stars" in item["snippet"]
        assert item["link"] == "https://github.com/acme/vectordb"
        assert "Authorization" not in calls[0]["headers"]

    def test_token_sent_as_header(self, online, monkeypatch):
        calls = []
        monkeypatch.setattr(github_tool.requests, "get", fake_get(GITHUB_PAYLOAD, calls))
        GitHubTool(token="ghp_test").search("x")
        assert calls[0]["headers"]["Authorization"] == "Bearer ghp_test"

    def test_rate_limited_degrades_to_empty(self, online, monkeypatch):
        monkeypatch.setattr(github_tool.requests, "get", fake_get({}, [], status=403))
        assert GitHubTool(token="").search("x") == []


class TestNews:
    def test_no_key_means_unavailable_and_no_network(self, online, monkeypatch):
        monkeypatch.setattr(news_tool.requests, "get", exploding_get)
        tool = NewsTool(api_key="")
        assert tool.available is False
        assert tool.search("legal ai funding") == []

    def test_offline_even_with_key_makes_no_call(self, monkeypatch):
        monkeypatch.setattr(news_tool.requests, "get", exploding_get)
        tool = NewsTool(api_key="news-key")
        assert tool.available is False
        assert tool.search("anything") == []

    def test_live_search_parses_and_skips_removed(self, online, monkeypatch):
        calls = []
        monkeypatch.setattr(news_tool.requests, "get", fake_get(NEWS_PAYLOAD, calls))
        results = NewsTool(api_key="news-key").search("legal ai")

        assert len(results) == 1
        item = results[0]
        assert item["source"] == "news"
        assert item["outlet"] == "Example Times"
        assert item["published"] == "2025-09-15T08:00:00Z"
        # Key goes in a header, never the query string.
        assert calls[0]["headers"]["X-Api-Key"] == "news-key"
        assert "apiKey" not in calls[0]["params"]

    def test_error_status_payload_returns_empty(self, online, monkeypatch):
        payload = {"status": "error", "code": "rateLimited"}
        monkeypatch.setattr(news_tool.requests, "get", fake_get(payload, []))
        assert NewsTool(api_key="k").search("x") == []


class StubTool:
    """Records queries and returns one labelled evidence item."""

    def __init__(self, source, available=True):
        self.source = source
        self.available = available
        self.queries = []

    def search(self, query, *args, **kwargs):
        self.queries.append(query)
        return [{"title": f"{self.source} hit", "snippet": "s", "link": f"https://{self.source}",
                 "source": self.source}]


class FailingTool(StubTool):
    def search(self, query, *args, **kwargs):
        raise RuntimeError("source down")


def make_researcher(news_available=True, **overrides):
    tools = {
        "web_search": StubTool("web"),
        "arxiv": StubTool("academic"),
        "wikipedia": StubTool("encyclopedia"),
        "github": StubTool("code"),
        "news": StubTool("news", available=news_available),
    }
    tools.update(overrides)
    return Researcher(**tools), tools


class TestRouting:
    def test_generic_task_uses_web_and_encyclopedia_only(self):
        researcher, _ = make_researcher()
        task = {"id": "t1", "title": "Define the problem space", "description": "Scope it"}
        assert researcher.route(task) == ["web", "encyclopedia"]

    def test_code_task_adds_github(self):
        researcher, _ = make_researcher()
        task = {"id": "t1", "title": "Compare open-source vector databases"}
        assert "code" in researcher.route(task)

    def test_market_task_adds_news_only_when_available(self):
        task = {"id": "t1", "title": "Market trends in legal tech"}
        with_news, _ = make_researcher(news_available=True)
        without_news, _ = make_researcher(news_available=False)
        assert "news" in with_news.route(task)
        assert "news" not in without_news.route(task)

    def test_academic_task_adds_arxiv(self):
        researcher, _ = make_researcher()
        task = {"id": "t1", "title": "Survey of retrieval papers"}
        assert "academic" in researcher.route(task)

    def test_hints_match_whole_word_starts_only(self):
        researcher, _ = make_researcher()
        # "capital" contains "api"; "rapidly" contains "api" too. Neither is code.
        task = {"id": "t1", "title": "Venture capital moves rapidly"}
        assert "code" not in researcher.route(task)

    def test_disabled_source_is_skipped(self, monkeypatch):
        monkeypatch.setattr(Config, "ENABLED_SOURCES", frozenset({"web", "academic"}))
        researcher, tools = make_researcher()
        task = {"id": "t1", "title": "Open-source library survey"}
        assert researcher.route(task) == ["web", "academic"]
        researcher.research_task(task)
        assert tools["wikipedia"].queries == []
        assert tools["github"].queries == []

    def test_research_task_collects_all_routed_sources(self):
        researcher, _ = make_researcher()
        task = {"id": "t7", "title": "Latest open-source framework trends research"}
        result = researcher.research_task(task)
        types = {e["source"] for e in result["evidence"]}
        assert types == {"web", "encyclopedia", "academic", "code", "news"}
        assert all(e["task_id"] == "t7" for e in result["evidence"])
        assert result["sources_tried"] == ["web", "encyclopedia", "academic", "code", "news"]

    def test_one_failing_source_does_not_sink_the_task(self):
        researcher, _ = make_researcher(wikipedia=FailingTool("encyclopedia"))
        result = researcher.research_task({"id": "t1", "title": "Anything"})
        assert result["status"] == "completed"
        assert [e["source"] for e in result["evidence"]] == ["web"]


class TestValidatorCredibility:
    def test_new_source_types_are_ranked(self):
        validator = Validator()
        def score(source):
            return validator._score_evidence({"title": "x", "snippet": "y" * 100, "source": source})["source_score"]
        assert score("academic") > score("encyclopedia") > score("news") > score("code") > score("web")


class TestModeEvidenceLabel:
    @pytest.fixture
    def keys(self, monkeypatch):
        def _set(serp="", news="", llm=""):
            monkeypatch.setattr(Config, "OFFLINE_MODE", False)
            monkeypatch.setattr(Config, "SERPAPI_API_KEY", serp)
            monkeypatch.setattr(Config, "NEWSAPI_KEY", news)
            monkeypatch.setattr(Config, "OPENAI_API_KEY", llm)
            monkeypatch.setattr(Config, "ANTHROPIC_API_KEY", "")
            return Config.capability_mode()
        return _set

    def test_no_keys_lists_keyless_sources_and_admits_mock_web(self, keys):
        mode = keys()
        assert mode["mode"] == "heuristic"
        assert "Wikipedia" in mode["evidence"] and "GitHub" in mode["evidence"]
        assert "mock" in mode["evidence"]
        assert "40%" in mode["expect"]

    def test_full_keys_list_web_and_news_with_no_mock(self, keys):
        mode = keys(serp="s", news="n", llm="sk")
        assert mode["mode"] == "full"
        assert "web" in mode["evidence"] and "news" in mode["evidence"]
        assert "mock" not in mode["evidence"]

    def test_news_omitted_without_key(self, keys):
        assert "news" not in keys(serp="s")["evidence"]

    def test_offline_lists_no_live_sources(self):
        # conftest forces offline
        assert Config.live_sources() == []
        assert Config.capability_mode()["evidence"] == "mock placeholders"


class TestReportOrdering:
    def test_real_evidence_listed_before_mock(self):
        from src.core.orchestrator import BLITZOrchestrator

        evidence = [
            {"title": f"[MOCK] m{i}", "snippet": "", "link": "", "source": "web", "mock": True}
            for i in range(5)
        ] + [{"title": "Real article", "snippet": "", "link": "https://x", "source": "encyclopedia"}]
        text = BLITZOrchestrator._format_evidence(evidence)
        assert text.startswith("1. **Real article** (encyclopedia)")
        assert "...and 1 more evidence items." in text
