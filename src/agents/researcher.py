"""MODULE_C — Research Execution.

Routes each task to data sources (web search + ArXiv), runs them in
parallel (bounded workers), and returns raw evidence objects.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from src.core.config import Config
from src.tools.arxiv_tool import ArxivTool
from src.tools.web_search import WebSearchTool

_ACADEMIC_HINTS = ("research", "paper", "study", "algorithm", "state of the art",
                   "benchmark", "survey", "technique")


class Researcher:
    """Executes research tasks using the available tools."""

    def __init__(self, web_search: WebSearchTool | None = None,
                 arxiv: ArxivTool | None = None):
        self.web_search = web_search or WebSearchTool()
        self.arxiv = arxiv or ArxivTool()

    def research_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = f"{task.get('title', '')} {task.get('description', '')}".strip()
        evidence = list(self.web_search.search(query))

        # Only hit ArXiv when the task looks academic/technical — keeps
        # latency down and avoids irrelevant papers on market questions.
        lowered = query.lower()
        if any(hint in lowered for hint in _ACADEMIC_HINTS) or task.get("complexity") == "Complex":
            evidence.extend(self.arxiv.search(query, max_results=3))

        for item in evidence:
            item["task_id"] = task.get("id", "")

        return {
            "task_id": task.get("id", ""),
            "task_title": task.get("title", ""),
            "evidence": evidence,
            "source_count": len(evidence),
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
                            "status": f"failed: {exc}",
                        }
                    )
        # Preserve original task order for readable reports.
        order = {t.get("id", ""): i for i, t in enumerate(tasks)}
        results.sort(key=lambda r: order.get(r.get("task_id", ""), 99))
        return results
