# Recursive Gap Review — BLITZ OS MVP

The system's own methodology (`find gaps → fix → re-review → repeat until
no actionable gaps`) applied to the MVP itself, focused on three questions:

1. Is the **user functionality** clear — can a new user tell what they can do?
2. Is setup a simple **1–3 step** path to using and tracking research?
3. Are **expectations** well-defined and clearly stated at every surface?

---

## Pass 1 — findings and resolutions

| # | Gap | Resolution |
|---|---|---|
| 1 | README led with architecture, not what the user can do | README rewritten: opens with a one-sentence value statement and a "What you can do with it" table; architecture moved below the fold |
| 2 | Setup wasn't framed as a guaranteed short path, and didn't say up front that zero keys works | "Setup — 3 steps" section: install → `--status` → run. Keys explicitly optional |
| 3 | No way to see the current capability mode or what quality to expect before running a query | New single source of truth `Config.capability_mode()` (5 modes, each with label, expectations, and upgrade hint), exposed as CLI `--status`, enriched `/health`, and a UI banner |
| 4 | Research reports didn't state their own expectations inline | Every report now opens with a mode banner: reasoning type, evidence type, upgrade hint |
| 5 | Tracking the knowledge base wasn't a first-class flow | "Tracking your knowledge base" README section; `--status` shows archive totals and spend; CLI prints tracking commands after every run |
| 6 | `run.py` crashed with a raw traceback if dependencies were missing | Dependency pre-check with the exact fix command; prints the capability mode before starting services |

## Pass 2 — re-review after fixes

| # | Gap | Resolution |
|---|---|---|
| 7 | After a query, the CLI didn't remind the user how to find it again | One-line tracking hint appended to every CLI run |
| 8 | `.env.example` listed keys without mapping them to capability modes | Comment block mapping key combinations → modes, pointing at `--status` |
| 9 | README referenced this review document before it existed | This file |

## Pass 3 — confirmation

- Full test suite passes (40 tests, offline, deterministic), including a new
  `tests/test_expectations.py` that pins the contract: **every surface (CLI,
  API, UI, report text) must state the capability mode and expectations** —
  all 5 modes covered.
- Manual walkthrough of the 3-step setup on a clean environment:
  `pip install` → `--status` → query — each step's output states the mode,
  what to expect, and the next step.
- No further actionable gaps at MVP scope.

## Known gaps deliberately left open (with reasoning)

These are marked, not resolved — consistent with the MVP rule
"mark contradictions, don't resolve them":

| Gap | Why deferred |
|---|---|
| Evidence quality depends on SerpAPI's free tier (100 queries/month) | Acceptable for MVP validation; add more sources (NewsAPI, GitHub, Wikipedia) in Phase 2 |
| Heuristic mode can't detect contradictions | Requires an LLM by nature; reports say "Not checked" rather than implying a clean bill |
| Archive search is substring-based, not semantic | JSONL + full-text is the MVP spec; vector embeddings (ChromaDB) are Phase 2 |
| Cost figures are estimates from published per-token prices | Exact billing requires provider-side reconciliation; estimates are conservative and the circuit breaker fires on the estimate |
| No multi-user support or auth on the API | Single-operator MVP by design; Phase 4 |

## The expectation contract (what the user is promised)

In **every** mode, a query returns: 3–5 decomposed tasks, a confidence score,
listed sources, identified gaps, and one follow-up question — bounded by
`MAX_ITERATIONS` (default 3) and `MAX_COST_PER_QUERY` (default $0.50).
Mock evidence can never present as strong: confidence is hard-capped at 40%
and every mock item is labelled `[MOCK]`. There are no silent downgrades:
mode is stated on the status command, the health endpoint, the UI banner,
and the report itself.
