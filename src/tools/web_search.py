"""Web search via SerpAPI, with a deterministic mock when no key is set."""

import os
from datetime import datetime
from typing import Any, Dict, List

import requests

from src.core.config import Config


class WebSearchTool:
    """Executes web searches via SerpAPI (free tier: 100 queries/month)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or Config.SERPAPI_API_KEY or os.getenv("SERPAPI_API_KEY", "")
        self.base_url = "https://serpapi.com/search"

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        if Config.OFFLINE_MODE or not self.api_key:
            return self._mock_search(query)

        try:
            resp = requests.get(
                self.base_url,
                params={
                    "q": query,
                    "api_key": self.api_key,
                    "num": num_results,
                    "engine": "google",
                },
                timeout=Config.TASK_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return self._mock_search(query)

        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "source": "web",
                    "relevance_score": 0.7,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        return results or self._mock_search(query)

    def _mock_search(self, query: str) -> List[Dict[str, Any]]:
        """Deterministic placeholder evidence, clearly labelled as mock."""
        now = datetime.now().isoformat()
        return [
            {
                "title": f"[MOCK] Overview: {query[:60]}",
                "snippet": (
                    f"Placeholder evidence for '{query[:80]}'. Set SERPAPI_API_KEY "
                    "in .env to fetch real web results."
                ),
                "link": "https://example.com/mock-web-result",
                "source": "web",
                "relevance_score": 0.5,
                "timestamp": now,
                "mock": True,
            },
            {
                "title": f"[MOCK] Analysis: {query[:60]}",
                "snippet": (
                    f"Second placeholder source discussing '{query[:80]}' from an "
                    "analytical angle."
                ),
                "link": "https://example.com/mock-web-analysis",
                "source": "web",
                "relevance_score": 0.5,
                "timestamp": now,
                "mock": True,
            },
        ]
