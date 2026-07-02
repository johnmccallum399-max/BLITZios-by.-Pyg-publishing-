"""MODULE_D — Evidence Validation.

Scores every evidence item (source credibility, recency, strength) and
detects contradictions between sources. Contradiction detection uses the
LLM when available; otherwise contradictions are marked as unchecked.
"""

from datetime import datetime
from typing import Any, Dict, List

from src.agents import load_prompt
from src.tools.model_router import ModelRouter

DEFAULT_PROMPT = """Analyze these research snippets for factual contradictions:

{sources_text}

Return a JSON array (possibly empty). Each contradiction:
- source_1: index of first source
- source_2: index of second source
- contradiction: one sentence describing the conflict

Return only valid JSON, no prose."""

# Base credibility by source type (1.0 scale).
_SOURCE_CREDIBILITY = {
    "academic": 0.9,
    "news": 0.6,
    "web": 0.5,
}


class Validator:
    """Scores evidence quality and detects contradictions."""

    def __init__(self, router: ModelRouter | None = None):
        self.router = router or ModelRouter()
        self.prompt_template = load_prompt("validator_prompt", DEFAULT_PROMPT)

    def validate(self, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not evidence:
            return {
                "individual_scores": [],
                "average_confidence": 0.0,
                "contradictions": [],
                "contradiction_count": 0,
                "contradictions_checked": False,
            }

        scores = [self._score_evidence(item) for item in evidence]

        contradictions: List[Dict[str, str]] = []
        checked = False
        if len(evidence) > 1 and self.router.available:
            contradictions = self._detect_contradictions(evidence)
            checked = True

        avg = sum(s["overall_score"] for s in scores) / len(scores)

        # Mock evidence caps confidence: placeholder data must never look strong.
        if any(item.get("mock") for item in evidence):
            avg = min(avg, 0.4)

        return {
            "individual_scores": scores,
            "average_confidence": round(avg, 2),
            "contradictions": contradictions,
            "contradiction_count": len(contradictions),
            "contradictions_checked": checked,
        }

    def _score_evidence(self, item: Dict[str, Any]) -> Dict[str, Any]:
        source_type = item.get("source", "web")
        source_score = _SOURCE_CREDIBILITY.get(source_type, 0.5)

        recency_score = self._recency_score(item)

        # Evidence strength: does the snippet actually say something substantive?
        snippet = item.get("snippet", "") or ""
        strength_score = min(1.0, 0.3 + len(snippet) / 400)
        if item.get("mock"):
            strength_score = 0.2

        overall = round(
            source_score * 0.5 + recency_score * 0.2 + strength_score * 0.3, 2
        )
        return {
            "title": item.get("title", "")[:80],
            "source_score": source_score,
            "recency_score": recency_score,
            "strength_score": round(strength_score, 2),
            "overall_score": overall,
        }

    def _recency_score(self, item: Dict[str, Any]) -> float:
        published = item.get("published") or item.get("timestamp") or ""
        try:
            dt = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            age_days = (datetime.now(dt.tzinfo) - dt).days
        except (ValueError, TypeError):
            return 0.7  # unknown age: neutral score
        if age_days <= 90:
            return 1.0
        if age_days <= 365:
            return 0.8
        if age_days <= 3 * 365:
            return 0.6
        return 0.4

    def _detect_contradictions(
        self, evidence: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        sources_text = "\n".join(
            f"Source {i}: {item.get('snippet') or item.get('title', '')}"
            for i, item in enumerate(evidence[:5])
        )
        parsed = self.router.complete_json(
            system="You are a contradiction detection system.",
            prompt=self.prompt_template.format(sources_text=sources_text),
            temperature=0.1,
        )
        if not isinstance(parsed, list):
            return []
        return [
            {
                "source_1": str(c.get("source_1", "")),
                "source_2": str(c.get("source_2", "")),
                "contradiction": str(c.get("contradiction", "")),
            }
            for c in parsed
            if isinstance(c, dict) and c.get("contradiction")
        ]
