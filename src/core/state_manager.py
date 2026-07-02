"""BLITZ state schema and the JSONL knowledge archive (MODULE_G).

Everything the pipeline learns is appended to a JSONL file so the archive
is human-readable, greppable, and versionable — no database required.
"""

import hashlib
import json
import os
from typing import Any, Dict, List, TypedDict

from src.core.config import Config


class BLITZState(TypedDict):
    query: str
    intent: Dict[str, Any]
    tasks: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    scores: Dict[str, Any]
    gaps: List[str]
    response: str
    iteration: int
    max_iterations: int  # CRITICAL: prevents infinite recursion
    cost: float
    timestamp: str
    sources: List[str]
    contradictions: List[Dict[str, str]]
    follow_up: str


def new_state(query: str, max_iterations: int | None = None) -> BLITZState:
    from datetime import datetime

    return BLITZState(
        query=query,
        intent={},
        tasks=[],
        evidence=[],
        scores={},
        gaps=[],
        response="",
        iteration=0,
        max_iterations=max_iterations or Config.MAX_ITERATIONS,
        cost=0.0,
        timestamp=datetime.now().isoformat(),
        sources=[],
        contradictions=[],
        follow_up="",
    )


class KnowledgeArchive:
    """Append-only JSONL persistence of every research run."""

    def __init__(self, filepath: str | None = None):
        self.filepath = filepath or Config.knowledge_file()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        dirname = os.path.dirname(self.filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        if not os.path.exists(self.filepath):
            open(self.filepath, "w").close()

    def store(self, state: BLITZState) -> str:
        doc_id = hashlib.md5(
            f"{state['query']}{state['timestamp']}".encode()
        ).hexdigest()

        record = {
            "id": doc_id,
            "query": state["query"],
            "intent": state["intent"],
            "tasks": state["tasks"],
            "evidence": state["evidence"],
            "scores": state["scores"],
            "gaps": state["gaps"],
            "response": state["response"],
            "iteration": state["iteration"],
            "cost": state["cost"],
            "timestamp": state["timestamp"],
            "sources": state.get("sources", []),
            "contradictions": state.get("contradictions", []),
            "follow_up": state.get("follow_up", ""),
        }

        with open(self.filepath, "a") as f:
            f.write(json.dumps(record) + "\n")

        return doc_id

    def _iter_records(self):
        try:
            with open(self.filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            return

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Full-text search across the whole record, not just the query field."""
        needle = query.lower()
        results = []
        for record in self._iter_records():
            haystack = json.dumps(record).lower()
            if needle in haystack:
                results.append(record)
                if len(results) >= limit:
                    break
        return results

    def get(self, doc_id: str) -> Dict | None:
        for record in self._iter_records():
            if record.get("id") == doc_id:
                return record
        return None

    def get_stats(self) -> Dict[str, Any]:
        count = 0
        total_cost = 0.0
        total_evidence = 0
        for record in self._iter_records():
            count += 1
            total_cost += record.get("cost", 0.0)
            total_evidence += len(record.get("evidence", []))
        return {
            "total_entries": count,
            "total_cost": round(total_cost, 4),
            "total_evidence_items": total_evidence,
        }
