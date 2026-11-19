"""Encyclopedic background via the public MediaWiki search API (no key)."""

import html
import re
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import quote

import requests

from src.core.config import Config
from src.tools.http import USER_AGENT

_TAG_RE = re.compile(r"<[^>]+>")


class WikipediaTool:
    """Searches Wikipedia articles. Failures degrade to an empty list."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"
    ARTICLE_URL = "https://en.wikipedia.org/wiki/"

    def search(self, query: str, max_results: int = 2) -> List[Dict[str, Any]]:
        if Config.OFFLINE_MODE:
            return []
        try:
            resp = requests.get(
                self.BASE_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": max_results,
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=Config.TASK_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return self._parse(resp.json(), max_results)
        except Exception:
            return []

    def _parse(self, data: Dict[str, Any], max_results: int = 2) -> List[Dict[str, Any]]:
        results = []
        for item in (data.get("query", {}) or {}).get("search", [])[:max_results]:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            # Search snippets carry <span class="searchmatch"> markup and entities.
            snippet = html.unescape(_TAG_RE.sub("", item.get("snippet", "") or "")).strip()
            results.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "link": self.ARTICLE_URL + quote(title.replace(" ", "_")),
                    "source": "encyclopedia",
                    # Last revision time: how current the article is, not when
                    # the underlying facts happened.
                    "published": item.get("timestamp", ""),
                    "relevance_score": 0.6,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        return results
