"""The heart of BLITZ: a LangGraph state machine running the intelligence loop.

    Query → Intent → Plan → Research → Validate → Find Gaps
                       ▲                              │
                       └────────── (iterate) ─────────┘
                                                      │
                                            Respond → Archive

Safety rails (non-negotiable):
  * max_iterations bounds the loop
  * confidence target ends the loop early
  * the shared CostTracker aborts LLM spending past the per-query budget
"""

import time
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from src.agents.gap_finder import GapFinder
from src.agents.intent_engine import IntentEngine
from src.agents.planner import TaskPlanner
from src.agents.researcher import Researcher
from src.agents.validator import Validator
from src.core.config import Config
from src.core.state_manager import BLITZState, KnowledgeArchive, new_state
from src.tools.model_router import CostTracker, ModelRouter


class BLITZOrchestrator:
    """Main orchestrator for the BLITZ Intelligence OS."""

    def __init__(self, archive: KnowledgeArchive | None = None):
        # One cost tracker per run; reset in run(). All agents share it so
        # the circuit breaker sees total spend, not per-agent spend.
        self.cost_tracker = CostTracker()
        router = ModelRouter(self.cost_tracker)

        self.intent_engine = IntentEngine(router)
        self.planner = TaskPlanner(router)
        self.researcher = Researcher()
        self.validator = Validator(router)
        self.gap_finder = GapFinder(router)
        self.archive = archive or KnowledgeArchive()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(BLITZState)

        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("plan_tasks", self._plan_tasks)
        workflow.add_node("research", self._research)
        workflow.add_node("validate", self._validate)
        workflow.add_node("find_gaps", self._find_gaps)
        workflow.add_node("respond", self._respond)

        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "plan_tasks")
        workflow.add_edge("plan_tasks", "research")
        workflow.add_edge("research", "validate")
        workflow.add_edge("validate", "find_gaps")
        workflow.add_conditional_edges(
            "find_gaps",
            self._should_continue,
            {"continue": "plan_tasks", "end": "respond"},
        )
        workflow.add_edge("respond", END)

        return workflow.compile()

    # --- Nodes -----------------------------------------------------------

    def _classify_intent(self, state: BLITZState) -> BLITZState:
        state["intent"] = self.intent_engine.classify(state["query"])
        state["cost"] = self.cost_tracker.total
        return state

    def _plan_tasks(self, state: BLITZState) -> BLITZState:
        state["tasks"] = self.planner.decompose(
            state["query"],
            state["intent"],
            gaps=state["gaps"] if state["iteration"] > 0 else None,
            follow_up=state["follow_up"] if state["iteration"] > 0 else "",
            iteration=state["iteration"],
        )
        state["cost"] = self.cost_tracker.total
        return state

    def _research(self, state: BLITZState) -> BLITZState:
        results = self.researcher.execute(state["tasks"])
        fresh = [e for r in results for e in r.get("evidence", [])]

        # Accumulate across iterations, deduplicating by link/title.
        seen = {(e.get("link"), e.get("title")) for e in state["evidence"]}
        for item in fresh:
            key = (item.get("link"), item.get("title"))
            if key not in seen:
                seen.add(key)
                state["evidence"].append(item)

        state["sources"] = sorted(
            {e.get("source", "unknown") for e in state["evidence"]}
        )
        return state

    def _validate(self, state: BLITZState) -> BLITZState:
        scores = self.validator.validate(state["evidence"])
        state["scores"] = scores
        state["contradictions"] = scores.get("contradictions", [])
        state["cost"] = self.cost_tracker.total
        return state

    def _find_gaps(self, state: BLITZState) -> BLITZState:
        if not state["evidence"]:
            state["gaps"] = ["No evidence gathered"]
        else:
            gap_analysis = self.gap_finder.find_gaps(
                state["query"],
                state["intent"],
                state["tasks"],
                state["evidence"],
                state["scores"],
            )
            state["gaps"] = gap_analysis.get("gaps", [])
            state["follow_up"] = gap_analysis.get("follow_up_question", "")
        state["iteration"] += 1
        state["cost"] = self.cost_tracker.total
        return state

    def _should_continue(self, state: BLITZState) -> str:
        if state["iteration"] >= state["max_iterations"]:
            return "end"
        if self.cost_tracker.exhausted:
            return "end"  # circuit breaker: budget spent, return what we have
        if state["scores"].get("average_confidence", 0) >= Config.CONFIDENCE_TARGET:
            return "end"
        if state["gaps"]:
            return "continue"
        return "end"

    def _respond(self, state: BLITZState) -> BLITZState:
        """MODULE_F — synthesize everything into a human-readable report."""
        confidence = state["scores"].get("average_confidence", 0)
        mode = Config.capability_mode()

        sections = [
            f"## Research Results: {state['query']}",
            "",
            f"> **Mode: {mode['label']}** — reasoning: {mode['reasoning']}; "
            f"evidence: {mode['evidence']}."
            + (f" To upgrade: {mode['upgrade']}" if mode["upgrade"] else ""),
            "",
            "### Summary",
            f"Based on {len(state['evidence'])} evidence items from "
            f"{len(state['sources'])} source type(s):",
            "",
            self._format_evidence(state["evidence"]),
            "",
            f"### Confidence Score: {confidence * 100:.0f}%",
            "",
            "### Sources",
            ", ".join(state["sources"]) or "No sources available",
            "",
            "### Contradictions",
            self._format_contradictions(state),
            "",
            "### Gaps Identified",
            self._format_gaps(state.get("gaps", [])),
            "",
            "### Follow-up Question",
            state.get("follow_up") or "No follow-up question generated.",
            "",
            f"*Iterations: {state['iteration']} · "
            f"Estimated cost: ${self.cost_tracker.total:.4f} · "
            f"LLM calls: {self.cost_tracker.calls}*",
        ]
        state["response"] = "\n".join(sections)
        state["cost"] = self.cost_tracker.total
        return state

    # --- Formatting helpers ------------------------------------------------

    @staticmethod
    def _format_evidence(evidence) -> str:
        if not evidence:
            return "No evidence gathered."
        lines = []
        for i, item in enumerate(evidence[:5], 1):
            title = item.get("title", "Unknown source")
            snippet = (item.get("snippet", "") or "")[:150]
            link = item.get("link", "")
            lines.append(f"{i}. **{title}**\n   {snippet}\n   {link}")
        if len(evidence) > 5:
            lines.append(f"...and {len(evidence) - 5} more evidence items.")
        return "\n\n".join(lines)

    @staticmethod
    def _format_contradictions(state: BLITZState) -> str:
        if not state["scores"].get("contradictions_checked"):
            return "Not checked (no LLM available for cross-source analysis)."
        contradictions = state.get("contradictions", [])
        if not contradictions:
            return "None detected across sources."
        return "\n".join(
            f"- Sources {c.get('source_1')} vs {c.get('source_2')}: {c.get('contradiction')}"
            for c in contradictions
        )

    @staticmethod
    def _format_gaps(gaps) -> str:
        if not gaps:
            return "No significant gaps identified."
        return "\n".join(f"- {gap}" for gap in gaps)

    # --- Entry point -------------------------------------------------------

    def run(self, query: str, max_iterations: int | None = None) -> Dict[str, Any]:
        self.cost_tracker.total = 0.0
        self.cost_tracker.calls = 0

        initial_state = new_state(query, max_iterations)
        started = time.time()

        try:
            final_state = self.workflow.invoke(
                initial_state, config={"recursion_limit": 60}
            )
            doc_id = self.archive.store(final_state)
            return {
                "success": True,
                "state": final_state,
                "doc_id": doc_id,
                "elapsed_seconds": round(time.time() - started, 1),
                "stats": self.archive.get_stats(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "partial_state": initial_state,
                "elapsed_seconds": round(time.time() - started, 1),
            }
