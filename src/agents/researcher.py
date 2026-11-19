"""MODULE_C — Research Execution.

Routes each task to data sources, runs tasks in parallel (bounded
workers), and returns raw evidence objects.

Sources and when they are used:
  * web (SerpAPI)            every task (mock placeholders without a key)
  * encyclopedia (Wikipedia) every task, for background and definitions
  * academic (ArXiv)         tasks that look academic/technical
  * code (GitHub)            tasks about software, tools, or open source
  * news (NewsAPI)           tasks about markets, trends, or recent events,
                             only when NEWSAPI_KEY is set

Each source can be switched off with BLITZ_SOURCES (see Config).
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from src.core.config import Config
from src.tools.arxiv_tool import ArxivTool
from src.tools.github_tool import GitHubTool
from src.tools.news_tool import NewsTool
from src.tools.web_search import WebSearchTool
from src.tools.wikipedia_tool import WikipediaTool

_ACADEMIC_HINTS = ("research", "paper", "study", "algorithm", "state of the art",
                   "benchmark", "survey", "technique")
_CODE_HINTS = ("open source", "open-source", "github", "library", "framework",
               "repository", "sdk", "implementation", "software", "tooling",
               "codebase", "developer", "database", "api")
_NEWS_HINTS = ("trend", "market", "news", "recent", "latest", "industry",
               "competitor", "funding", "launch", "regulation", "adoption",
               "2024", "2025", "2026")


def _hint_pattern(hints) -> "re.Pattern[str]":
    # Match at the start of a word ("trend" -> "trends", "paper" -> "papers")
    # but never inside one, so "api" doesn't match "capital" or "rapid".
    return re.compile(r"\b(?:" + "|".join(re.escape(h) for h in hints) + r")")


_ACADEMIC_RE = _hint_pattern(_ACADEMIC_HINTS)
_CODE_RE = _hint_pattern(_CODE_HINTS)
_NEWS_RE = _hint_pattern(_NEWS_HINTS)


class Researcher:
    """Executes research tasks using the available tools."""

    def __init__(self, web_search: WebSearchTool | None = None,
                 arxiv: ArxivTool | None = None,
                 wikipedia: WikipediaTool | None = None,
                 github: GitHubTool | None = None,
                 news: NewsTool | None = None):
        self.web_search = web_search or WebSearchTool()
        self.arxiv = arxiv or ArxivTool()
        self.wikipedia = wikipedia or WikipediaTool()
        self.github = github or GitHubTool()
        self.news = news or NewsTool()

    def route(self, task: Dict[str, Any]) -> List[str]:
        """Which source types this task should query, in order."""
        query = f"{task.get('title', '')} {task.get('description', '')}".lower()
        complex_task = task.get("complexity") == "Complex"
        wanted = ["web", "encyclopedia"]
        # Targeted sources only fire when the task calls for them, which keeps
        # latency and rate-limit use down and avoids irrelevant results.
        if _ACADEMIC_RE.search(query) or complex_task:
            wanted.append("academic")
        if _CODE_RE.search(query):
            wanted.append("code")
        if _NEWS_RE.search(query) and self.news.available:
            wanted.append("news")
        return [s for s in wanted if Config.source_enabled(s)]

    def research_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = f"{task.get('title', '')} {task.get('description', '')}".strip()
        searches = {
            "web": lambda: self.web_search.search(query),
            "encyclopedia": lambda: self.wikipedia.search(query, max_results=2),
            "academic": lambda: self.arxiv.search(query, max_results=3),
            "code": lambda: self.github.search(query, max_results=3),
            "news": lambda: self.news.search(query, max_results=3),
        }

        evidence: List[Dict[str, Any]] = []
        sources_tried = self.route(task)
        for source in sources_tried:
            try:
                evidence.extend(searches[source]())
            except Exception:
                continue  # one failing source must not sink the task

        for item in evidence:
            item["task_id"] = task.get("id", "")

        return {
            "task_id": task.get("id", ""),
            "task_title": task.get("title", ""),
            "evidence": evidence,
            "source_count": len(evidence),
            "sources_tried": sources_tried,
            "status": "completed",
        }

    def execute(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tasks:
            return []
        workers = min(Config.MAX_PARALLEL_WORKERS, len(tasks))
        results = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.research_task, t): t for t in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    results.append(future.result(timeout=Config.TASK_TIMEOUT_SECONDS))
                except Exception as exc:
                    results.append(
                        {
                            "task_id": task.get("id", ""),
                            "task_title": task.get("title", ""),
                            "evidence": [],
                            "source_count": 0,
                            "sources_tried": [],
                            "status": f"failed: {exc}",
                        }
                    )
        # Preserve original task order for readable reports.
        order = {t.get("id", ""): i for i, t in enumerate(tasks)}
        results.sort(key=lambda r: order.get(r.get("task_id", ""), 99))
        return results
