"""MODULE_B — Task Decomposition.

Breaks an intent into 3-5 sub-tasks forming a small DAG (dependencies mark
sequential steps; tasks without dependencies can run in parallel).
On refinement iterations, plans new tasks from the identified gaps instead.
"""

import json
from typing import Any, Dict, List

from src.agents import load_prompt
from src.tools.model_router import ModelRouter

DEFAULT_PROMPT = """Break this research query into 3-5 specific research tasks.

Query: {query}
Intent: {intent}
{gap_context}

Return a JSON array where each task has:
- id: short identifier like "task_1"
- title: short task name
- description: one-sentence research instruction
- priority: "High" | "Medium" | "Low"
- complexity: "Simple" | "Moderate" | "Complex"
- dependencies: list of task ids that must complete first (empty = parallel)

Return only valid JSON, no prose."""

# Domain-specific task templates for the heuristic fallback.
_DOMAIN_TEMPLATES = {
    "Market": [
        ("Market Overview", "Research the current state and size of the market for"),
        ("Key Players", "Identify major companies and stakeholders relevant to"),
        ("Trends and Projections", "Analyze emerging trends and forecasts around"),
    ],
    "Technical": [
        ("Technology Landscape", "Survey the current technical options for"),
        ("Comparative Analysis", "Compare the leading solutions relevant to"),
        ("Adoption and Maturity", "Assess production readiness and community health of"),
    ],
    "Financial": [
        ("Financial Baseline", "Establish current financial figures related to"),
        ("Growth Projections", "Gather forecasts and growth rates concerning"),
        ("Risk Factors", "Identify financial risks and sensitivities affecting"),
    ],
    "Strategic": [
        ("Situation Analysis", "Map the strategic landscape surrounding"),
        ("Opportunities and Threats", "Identify opportunities and threats related to"),
        ("Options Assessment", "Evaluate strategic options available for"),
    ],
}
_DEFAULT_TEMPLATE = [
    ("Overview", "Research the current state of"),
    ("Key Players", "Identify major stakeholders relevant to"),
    ("Trends and Projections", "Analyze emerging trends around"),
]


class TaskPlanner:
    """Decomposes research into parallel/sequential tasks (a small DAG)."""

    def __init__(self, router: ModelRouter | None = None):
        self.router = router or ModelRouter()
        self.prompt_template = load_prompt("planner_prompt", DEFAULT_PROMPT)

    def decompose(
        self,
        query: str,
        intent: Dict[str, Any],
        gaps: List[str] | None = None,
        follow_up: str = "",
        iteration: int = 0,
    ) -> List[Dict[str, Any]]:
        gap_context = ""
        if gaps:
            gap_context = (
                "This is a refinement pass. Plan tasks that close these gaps:\n- "
                + "\n- ".join(gaps[:5])
            )
            if follow_up:
                gap_context += f"\nPriority follow-up question: {follow_up}"

        parsed = self.router.complete_json(
            system="You are a research planner. You output task graphs as JSON.",
            prompt=self.prompt_template.format(
                query=query,
                intent=json.dumps(intent, default=str),
                gap_context=gap_context,
            ),
            temperature=0.2,
        )
        tasks = self._normalize(parsed, iteration)
        if tasks:
            return tasks
        return self._heuristic_decompose(query, intent, gaps, follow_up, iteration)

    def _normalize(self, parsed: Any, iteration: int) -> List[Dict[str, Any]]:
        if not isinstance(parsed, list):
            return []
        tasks = []
        for i, item in enumerate(parsed[:5], 1):
            if not isinstance(item, dict) or not item.get("description"):
                continue
            tasks.append(
                {
                    "id": item.get("id") or f"task_{iteration}_{i}",
                    "title": item.get("title", f"Task {i}"),
                    "description": str(item["description"]),
                    "priority": item.get("priority", "Medium"),
                    "complexity": item.get("complexity", "Moderate"),
                    "dependencies": item.get("dependencies", []),
                    "iteration": iteration,
                }
            )
        return tasks if len(tasks) >= 2 else []

    def _heuristic_decompose(
        self,
        query: str,
        intent: Dict[str, Any],
        gaps: List[str] | None,
        follow_up: str,
        iteration: int,
    ) -> List[Dict[str, Any]]:
        # Refinement pass: turn each gap into a research task.
        if gaps:
            tasks = []
            questions = ([follow_up] if follow_up else []) + list(gaps)
            for i, gap in enumerate(questions[:3], 1):
                tasks.append(
                    {
                        "id": f"task_{iteration}_{i}",
                        "title": f"Close gap {i}",
                        "description": gap,
                        "priority": "High" if i == 1 else "Medium",
                        "complexity": "Moderate",
                        "dependencies": [],
                        "iteration": iteration,
                    }
                )
            return tasks

        subject = query.strip().rstrip("?")
        template = _DOMAIN_TEMPLATES.get(intent.get("domain", ""), _DEFAULT_TEMPLATE)
        tasks = []
        for i, (title, stem) in enumerate(template, 1):
            tasks.append(
                {
                    "id": f"task_{iteration}_{i}",
                    "title": title,
                    "description": f"{stem} {subject[:120]}",
                    "priority": "High" if i <= 2 else "Medium",
                    "complexity": "Moderate",
                    "dependencies": [] if i == 1 else [f"task_{iteration}_1"],
                    "iteration": iteration,
                }
            )
        return tasks
