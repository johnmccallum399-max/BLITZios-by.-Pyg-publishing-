"""MODULE_E — Gap Detection.

Compares gathered evidence against what an ideal evidence set would look
like, identifies missing perspectives, and generates one follow-up question.
"""

from typing import Any, Dict, List

from src.agents import load_prompt
from src.tools.model_router import ModelRouter

DEFAULT_PROMPT = """Analyze this research run and identify knowledge gaps.

Query: {query}
Intent: {intent}
Tasks executed: {task_titles}
Evidence count: {evidence_count}
Source types used: {source_types}
Average confidence: {confidence}

Consider:
1. What perspectives are missing?
2. What assumptions have not been tested?
3. What would cause conclusions based on this evidence to fail?
4. What adjacent topics could change the answer?

Return JSON with:
- gaps: list of at most 4 short gap descriptions
- follow_up_question: the single most valuable next question (string)
- priority: "High" | "Medium" | "Low"
- reasoning: one sentence

Return only valid JSON, no prose."""


class GapFinder:
    """Identifies missing information and generates follow-up questions."""

    def __init__(self, router: ModelRouter | None = None):
        self.router = router or ModelRouter()
        self.prompt_template = load_prompt("gap_finder_prompt", DEFAULT_PROMPT)

    def find_gaps(
        self,
        query: str,
        intent: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        scores: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_types = sorted({e.get("source", "unknown") for e in evidence})
        parsed = self.router.complete_json(
            system="You are a research gap analysis system.",
            prompt=self.prompt_template.format(
                query=query,
                intent=intent.get("objective", ""),
                task_titles=", ".join(t.get("title", "") for t in tasks),
                evidence_count=len(evidence),
                source_types=", ".join(source_types) or "none",
                confidence=scores.get("average_confidence", 0),
            ),
            temperature=0.3,
        )
        if isinstance(parsed, dict) and parsed.get("follow_up_question"):
            gaps = parsed.get("gaps", [])
            return {
                "gaps": [str(g) for g in gaps][:4] if isinstance(gaps, list) else [],
                "follow_up_question": str(parsed["follow_up_question"]),
                "priority": parsed.get("priority", "Medium"),
                "reasoning": parsed.get("reasoning", ""),
                "method": "llm",
            }
        return self._heuristic_gaps(query, intent, tasks, evidence, scores)

    def _heuristic_gaps(
        self,
        query: str,
        intent: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        scores: Dict[str, Any],
    ) -> Dict[str, Any]:
        gaps: List[str] = []

        source_types = {e.get("source", "unknown") for e in evidence}
        if len(source_types) < 2:
            gaps.append(
                f"Evidence comes from a single source type ({', '.join(source_types) or 'none'}); "
                "corroboration from a second source type is missing"
            )

        covered = {e.get("task_id") for e in evidence if e.get("task_id")}
        for task in tasks:
            if task.get("id") not in covered:
                gaps.append(f"No evidence gathered for task: {task.get('title', task.get('id'))}")

        confidence = scores.get("average_confidence", 0)
        if confidence < 0.5:
            gaps.append("Overall evidence confidence is low; stronger primary sources needed")

        if any(e.get("mock") for e in evidence):
            gaps.append("Results include placeholder data; configure search API keys for real evidence")

        if not scores.get("contradictions_checked"):
            gaps.append("Sources were not cross-checked for contradictions")

        assumptions = intent.get("assumptions", [])
        follow_up = (
            f"What evidence would confirm or refute the assumption that "
            f"'{assumptions[0]}'?"
            if assumptions
            else f"What is the strongest argument against the current findings on: {query[:100]}?"
        )

        return {
            "gaps": gaps[:4],
            "follow_up_question": follow_up,
            "priority": "High" if confidence < 0.5 else "Medium",
            "reasoning": "Heuristic gap analysis based on source diversity, task coverage, and confidence",
            "method": "heuristic",
        }
