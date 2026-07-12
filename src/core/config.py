"""Central configuration for BLITZ OS.

Every knob lives here so cost controls and model choices can be tuned
from the environment without touching code.
"""

import os
from typing import Dict

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Central configuration for BLITZ OS."""

    # --- API Keys (all optional; missing keys trigger offline fallbacks) ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

    # Force offline mode: no network calls at all (mock evidence, heuristic agents).
    # Useful for tests, demos, and development without burning API quota.
    OFFLINE_MODE = _env_bool("BLITZ_OFFLINE", False)

    # --- Cost Controls (non-negotiable circuit breakers) ---
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
    MAX_COST_PER_QUERY = float(os.getenv("MAX_COST_PER_QUERY", "0.50"))
    MAX_TOKENS_PER_CALL = int(os.getenv("MAX_TOKENS_PER_CALL", "2000"))
    TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "30"))
    MAX_PARALLEL_WORKERS = int(os.getenv("MAX_PARALLEL_WORKERS", "4"))

    # Confidence above this ends the research loop early.
    CONFIDENCE_TARGET = float(os.getenv("CONFIDENCE_TARGET", "0.7"))

    # --- Model Configuration ---
    DEFAULT_MODEL = os.getenv("BLITZ_DEFAULT_MODEL", "gpt-4o-mini")
    FALLBACK_MODEL = os.getenv("BLITZ_FALLBACK_MODEL", "claude-haiku-4-5-20251001")

    # Model costs in USD per 1K tokens, used by the cost circuit breaker.
    MODEL_COSTS: Dict[str, Dict[str, float]] = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
        "gpt-4-turbo": {"input": 0.010, "output": 0.030},
        "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    }

    # --- File Paths ---
    DATA_DIR = os.getenv("BLITZ_DATA_DIR", "data")
    PROMPTS_DIR = os.getenv("BLITZ_PROMPTS_DIR", "prompts")

    @classmethod
    def knowledge_file(cls) -> str:
        return os.path.join(cls.DATA_DIR, "knowledge.jsonl")

    @classmethod
    def get_model_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = cls.MODEL_COSTS.get(model)
        if not costs:
            return 0.0
        return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000

    @classmethod
    def capability_mode(cls) -> Dict[str, str]:
        """Single source of truth for 'what will this system do for me right now'.

        Every surface (CLI --status, /health, UI banner, report footer) reads
        this so the user always knows the mode and what to expect from it.
        """
        llm = bool(cls.OPENAI_API_KEY or cls.ANTHROPIC_API_KEY) and not cls.OFFLINE_MODE
        web = bool(cls.SERPAPI_API_KEY) and not cls.OFFLINE_MODE

        if cls.OFFLINE_MODE:
            return {
                "mode": "offline",
                "label": "Offline demo",
                "reasoning": "heuristic (deterministic rules)",
                "evidence": "mock placeholders",
                "expect": (
                    "Instant, free, zero network. Output shows the workflow, "
                    "not real research. Confidence is capped at 40%."
                ),
                "upgrade": "Unset BLITZ_OFFLINE and add API keys in .env for real research.",
            }
        if llm and web:
            return {
                "mode": "full",
                "label": "Full intelligence",
                "reasoning": "LLM-powered",
                "evidence": "real web + academic sources",
                "expect": (
                    "Real research: ~30s-3min per query, up to $0.50 "
                    "(circuit-breaker enforced). Cited sources, contradiction "
                    "checks, LLM gap analysis."
                ),
                "upgrade": "",
            }
        if llm:
            return {
                "mode": "llm_only",
                "label": "LLM reasoning, mock evidence",
                "reasoning": "LLM-powered",
                "evidence": "mock placeholders (no SERPAPI_API_KEY)",
                "expect": (
                    "Smart intent/planning/gap analysis, but evidence is "
                    "placeholder data. Confidence is capped at 40%. Do not act "
                    "on findings."
                ),
                "upgrade": "Add SERPAPI_API_KEY in .env for real web evidence.",
            }
        if web:
            return {
                "mode": "search_only",
                "label": "Real evidence, heuristic reasoning",
                "reasoning": "heuristic (deterministic rules)",
                "evidence": "real web + academic sources",
                "expect": (
                    "Real sources gathered and scored, but planning and gap "
                    "analysis use fixed rules; contradictions are not checked."
                ),
                "upgrade": "Add OPENAI_API_KEY or ANTHROPIC_API_KEY in .env for LLM reasoning.",
            }
        return {
            "mode": "heuristic",
            "label": "Heuristic demo (no API keys)",
            "reasoning": "heuristic (deterministic rules)",
            "evidence": "mock placeholders",
            "expect": (
                "Free and instant. Demonstrates the full workflow with "
                "placeholder evidence. Confidence is capped at 40%. Do not act "
                "on findings."
            ),
            "upgrade": (
                "Copy .env.example to .env and add OPENAI_API_KEY (reasoning) "
                "and SERPAPI_API_KEY (evidence)."
            ),
        }
