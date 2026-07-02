"""MODULE_A — Intent Detection Engine.

Classifies any text input into a structured intent object:
domain, entities, timeframe, geographic scope, urgency, objective, assumptions.
"""

import re
from typing import Any, Dict

from src.agents import load_prompt
from src.tools.model_router import ModelRouter

DEFAULT_PROMPT = """Analyze this research query and return JSON with exactly these keys:
- domain: one of ["Market", "Technical", "Financial", "Strategic", "Mixed"]
- entities: list of key people, companies, technologies mentioned
- timeframe: one of ["Immediate", "Short-term", "Medium-term", "Long-term"]
- geographic_scope: one of ["Global", "Regional", "Local"]
- urgency: one of ["High", "Medium", "Low"]
- objective: one sentence describing what the user really wants to know
- assumptions: list of things the query assumes to be true

Query: {query}

Return only valid JSON, no prose."""

# Keyword heuristics used when no LLM is available.
_DOMAIN_KEYWORDS = {
    "Market": ["market", "trend", "competitor", "customer", "demand", "industry", "adoption"],
    "Technical": ["technology", "software", "database", "architecture", "open-source",
                  "api", "framework", "code", "engineering", "algorithm"],
    "Financial": ["revenue", "cagr", "funding", "valuation", "cost", "price", "profit",
                  "investment", "roi", "budget", "financial"],
    "Strategic": ["strategy", "roadmap", "plan", "risk", "advantage", "positioning",
                  "expansion", "partnership"],
}

_TIMEFRAME_PATTERNS = [
    (r"\b(today|now|current|immediate)\b", "Immediate"),
    (r"\b20(2[5-7])\b", "Short-term"),
    (r"\b20(2[8-9]|3\d)\b", "Long-term"),
    (r"\b(next (decade|10 years)|long[- ]term)\b", "Long-term"),
]


class IntentEngine:
    """Detects user intent and extracts structured information."""

    def __init__(self, router: ModelRouter | None = None):
        self.router = router or ModelRouter()
        self.prompt_template = load_prompt("intent_prompt", DEFAULT_PROMPT)

    def classify(self, query: str) -> Dict[str, Any]:
        parsed = self.router.complete_json(
            system="You are an intent classification system for a research platform.",
            prompt=self.prompt_template.format(query=query),
            temperature=0.1,
        )
        if isinstance(parsed, dict) and "domain" in parsed:
            parsed.setdefault("entities", [])
            parsed.setdefault("assumptions", [])
            parsed["method"] = "llm"
            return parsed
        return self._heuristic_classify(query)

    def _heuristic_classify(self, query: str) -> Dict[str, Any]:
        lowered = query.lower()

        domain_hits = {
            domain: sum(1 for kw in kws if kw in lowered)
            for domain, kws in _DOMAIN_KEYWORDS.items()
        }
        matched = [d for d, hits in domain_hits.items() if hits > 0]
        if len(matched) == 0:
            domain = "Mixed"
        elif len(matched) == 1:
            domain = matched[0]
        else:
            best = max(domain_hits.values())
            leaders = [d for d, h in domain_hits.items() if h == best]
            domain = leaders[0] if len(leaders) == 1 else "Mixed"

        timeframe = "Medium-term"
        for pattern, label in _TIMEFRAME_PATTERNS:
            if re.search(pattern, lowered):
                timeframe = label
                break

        # Capitalized multi-word phrases and known tech terms serve as entities.
        entities = list(dict.fromkeys(
            re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*\b", query)
        ))[:8]

        geographic = "Global"
        if re.search(r"\b(local|city|regional|state|country|us|eu|asia)\b", lowered):
            geographic = "Regional"

        return {
            "domain": domain,
            "entities": entities,
            "timeframe": timeframe,
            "geographic_scope": geographic,
            "urgency": "Medium",
            "objective": f"Understand: {query[:120]}",
            "assumptions": ["Relevant information is publicly available"],
            "method": "heuristic",
        }
