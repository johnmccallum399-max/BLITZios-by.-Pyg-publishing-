"""Open-source landscape via the GitHub repository search API.

Works without a key (GitHub allows ~10 searches/minute unauthenticated);
set GITHUB_TOKEN for the higher authenticated limit.
"""

from datetime import datetime
from typing import Any, Dict, List

import requests

from src.core.config import Config
from src.tools.http import USER_AGENT


class GitHubTool:
    """Searches public repositories. Failures degrade to an empty list."""

    BASE_URL = "https://api.github.com/search/repositories"

    def __init__(self, token: str | None = None):
        self.token = token if token is not None else Config.GITHUB_TOKEN

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        if Config.OFFLINE_MODE:
            return []
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            resp = requests.get(
                self.BASE_URL,
                params={"q": query, "sort": "stars", "order": "desc", "per_page": max_results},
                headers=headers,
                timeout=Config.TASK_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return self._parse(resp.json(), max_results)
        except Exception:
            return []

    def _parse(self, data: Dict[str, Any], max_results: int = 3) -> List[Dict[str, Any]]:
        results = []
        for repo in (data.get("items") or [])[:max_results]:
            name = repo.get("full_name") or ""
            if not name:
                continue
            description = (repo.get("description") or "No description.").strip()
            stars = repo.get("stargazers_count", 0) or 0
            language = repo.get("language") or "unknown language"
            results.append(
                {
                    "title": f"GitHub: {name}",
                    "snippet": f"{description} ({stars:,} stars, {language})",
                    "link": repo.get("html_url", ""),
                    "source": "code",
                    "stars": stars,
                    # Last push: a signal of whether the project is maintained.
                    "published": repo.get("pushed_at", ""),
                    "relevance_score": 0.6,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        return results
