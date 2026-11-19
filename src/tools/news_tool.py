"""Recent news coverage via NewsAPI (needs NEWSAPI_KEY; skipped without one).

NewsAPI's free Developer plan allows 100 requests/day and is meant for
development use; see newsapi.org for production terms.
"""

from datetime import datetime
from typing import Any, Dict, List

import requests

from src.core.config import Config


class NewsTool:
    """Searches news articles. No key, offline, or failure -> empty list.

    Unlike web search there is no mock fallback: missing news is reported
    as a gap rather than papered over with placeholder data.
    """

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else Config.NEWSAPI_KEY

    @property
    def available(self) -> bool:
        return bool(self.api_key) and not Config.OFFLINE_MODE

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        if not self.available:
            return []
        try:
            resp = requests.get(
                self.BASE_URL,
                params={
                    "q": query,
                    "pageSize": max_results,
                    "sortBy": "relevancy",
                    "language": "en",
                },
                # Header auth keeps the key out of URLs and proxy logs.
                headers={"X-Api-Key": self.api_key},
                timeout=Config.TASK_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return self._parse(resp.json(), max_results)
        except Exception:
            return []

    def _parse(self, data: Dict[str, Any], max_results: int = 3) -> List[Dict[str, Any]]:
        if data.get("status") not in (None, "ok"):
            return []
        results = []
        for article in (data.get("articles") or [])[:max_results]:
            title = (article.get("title") or "").strip()
            # NewsAPI marks articles pulled after publication as "[Removed]".
            if not title or title == "[Removed]":
                continue
            outlet = ((article.get("source") or {}).get("name") or "").strip()
            snippet = (article.get("description") or article.get("content") or "").strip()
            results.append(
                {
                    "title": title,
                    "snippet": snippet[:300],
                    "link": article.get("url", ""),
                    "source": "news",
                    "outlet": outlet,
                    "published": article.get("publishedAt", ""),
                    "relevance_score": 0.65,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        return results
