"""ArXiv academic search using the public Atom API (no key, no extra deps)."""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List

import requests

from src.core.config import Config

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivTool:
    """Searches academic papers on ArXiv. Failures degrade to an empty list."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if Config.OFFLINE_MODE:
            return []
        try:
            resp = requests.get(
                self.BASE_URL,
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                },
                timeout=Config.TASK_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return self._parse(resp.text)
        except Exception:
            return []

    def _parse(self, xml_text: str) -> List[Dict[str, Any]]:
        results = []
        root = ET.fromstring(xml_text)
        for entry in root.findall("atom:entry", _ATOM_NS):
            title = (entry.findtext("atom:title", "", _ATOM_NS) or "").strip()
            summary = (entry.findtext("atom:summary", "", _ATOM_NS) or "").strip()
            link = entry.findtext("atom:id", "", _ATOM_NS) or ""
            published = entry.findtext("atom:published", "", _ATOM_NS) or ""
            authors = [
                (a.findtext("atom:name", "", _ATOM_NS) or "").strip()
                for a in entry.findall("atom:author", _ATOM_NS)
            ]
            if not title:
                continue
            results.append(
                {
                    "title": title,
                    "snippet": summary[:200] + ("..." if len(summary) > 200 else ""),
                    "link": link,
                    "source": "academic",
                    "authors": authors,
                    "published": published,
                    "relevance_score": 0.6,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        return results
