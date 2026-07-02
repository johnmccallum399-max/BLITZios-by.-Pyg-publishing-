"""Model router: sends prompts to the best available LLM and tracks cost.

Provider priority:
  1. OpenAI (gpt-4o-mini) when OPENAI_API_KEY is set
  2. Anthropic (claude haiku) when ANTHROPIC_API_KEY is set
  3. None — agents fall back to deterministic heuristics

Every call returns the text plus its estimated dollar cost so the
orchestrator's circuit breaker can abort runaway loops.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests

from src.core.config import Config


@dataclass
class LLMResult:
    text: str
    cost: float
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class CostTracker:
    """Accumulates spend across a single query run (circuit breaker input)."""

    total: float = 0.0
    calls: int = 0
    budget: float = field(default_factory=lambda: Config.MAX_COST_PER_QUERY)

    def add(self, cost: float):
        self.total += cost
        self.calls += 1

    @property
    def exhausted(self) -> bool:
        return self.total >= self.budget


class ModelRouter:
    """Chooses and calls the best available model, with graceful degradation."""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.cost_tracker = cost_tracker or CostTracker()

    @property
    def available(self) -> bool:
        if Config.OFFLINE_MODE:
            return False
        return bool(Config.OPENAI_API_KEY or Config.ANTHROPIC_API_KEY)

    def complete(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> Optional[LLMResult]:
        """Return an LLM completion, or None when no provider is usable.

        Callers must treat None as 'use your heuristic fallback'.
        """
        if not self.available:
            return None
        if self.cost_tracker.exhausted:
            return None  # circuit breaker: stop spending

        max_tokens = min(max_tokens or Config.MAX_TOKENS_PER_CALL, Config.MAX_TOKENS_PER_CALL)

        if Config.OPENAI_API_KEY:
            result = self._call_openai(system, prompt, temperature, max_tokens)
            if result:
                return result
        if Config.ANTHROPIC_API_KEY:
            result = self._call_anthropic(system, prompt, temperature, max_tokens)
            if result:
                return result
        return None

    def complete_json(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.1,
    ) -> Optional[Any]:
        """Complete and parse a JSON payload out of the response, or None."""
        result = self.complete(system, prompt, temperature)
        if result is None:
            return None
        return extract_json(result.text)

    # --- Providers -------------------------------------------------------

    def _call_openai(self, system, prompt, temperature, max_tokens) -> Optional[LLMResult]:
        model = Config.DEFAULT_MODEL
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {Config.OPENAI_API_KEY}"},
                json={
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=Config.TASK_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            cost = Config.get_model_cost(
                model,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
            )
            self.cost_tracker.add(cost)
            return LLMResult(
                text=data["choices"][0]["message"]["content"],
                cost=cost,
                model=model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )
        except Exception:
            return None

    def _call_anthropic(self, system, prompt, temperature, max_tokens) -> Optional[LLMResult]:
        model = Config.FALLBACK_MODEL
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": Config.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=Config.TASK_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            cost = Config.get_model_cost(
                model,
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )
            self.cost_tracker.add(cost)
            text = "".join(
                block.get("text", "") for block in data.get("content", [])
            )
            return LLMResult(
                text=text,
                cost=cost,
                model=model,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )
        except Exception:
            return None


def extract_json(text: str) -> Optional[Any]:
    """Pull a JSON object/array out of an LLM response, tolerating fences."""
    if not text:
        return None
    # Strip markdown code fences if present
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Last resort: find the outermost JSON-looking span, trying whichever
    # bracket type appears first (so arrays aren't shadowed by inner objects).
    obj_start = text.find("{")
    arr_start = text.find("[")
    pairs = [("{", "}"), ("[", "]")]
    if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
        pairs.reverse()
    for opener, closer in pairs:
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None
