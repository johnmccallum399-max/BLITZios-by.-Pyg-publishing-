# BLITZ OS — Implementation Plan

## Phase 1: Core MVP (this repository) ✅

- [x] MODULE_A Intent detection (LLM + keyword-heuristic fallback)
- [x] MODULE_B Task decomposition into a 3–5 task DAG
- [x] MODULE_C Multi-source research (SerpAPI web + ArXiv academic, parallel workers)
- [x] MODULE_D Evidence validation (credibility / recency / strength scoring, contradiction detection)
- [x] MODULE_E Gap detection + one follow-up question per run
- [x] MODULE_F Response generation (markdown report with scores, sources, contradictions)
- [x] MODULE_G Knowledge persistence (append-only JSONL, full-text search)
- [x] Bounded recursion via LangGraph conditional edges
- [x] Cost circuit breaker (shared CostTracker, aborts at $0.50/query)
- [x] REST API (FastAPI) + Web UI (Streamlit) + CLI
- [x] Offline mode for deterministic tests and free demos
- [x] Test suite (agents, tools, orchestrator integration, API)

## Success Metrics (MVP targets)

| Target | Status |
|---|---|
| < 3 minutes per query | ✅ seconds in offline mode; bounded by task timeouts online |
| < $0.50 per query | ✅ enforced by the CostTracker circuit breaker |
| 3+ tasks per query | ✅ planner guarantees 3–5 |
| 2+ source types | ✅ web + academic (gap-flagged when only one) |
| Confidence scoring with explanation | ✅ per-item and aggregate scores |
| Gap identification + follow-up | ✅ every run |
| Searchable storage | ✅ JSONL full-text search via API/CLI/UI |

## Architecture Decisions

### Why LangGraph?
- Native state management with typed state (`BLITZState`)
- Conditional edges give us the recursive loop with built-in safety
- Each node is independently upgradable

### Why JSONL storage?
- No database dependency, human-readable, greppable
- Perfect for the MVP; a graph DB is deliberately deferred

### Why heuristic fallbacks in every agent?
- The system must be demoable at $0 cost and testable without network
- Treats LLMs as "highly intelligent interns": every LLM output is
  parsed defensively and a deterministic path always exists

## Intentionally excluded from the MVP

- 📌 Knowledge graph (JSONL now; evolve relational → graph later)
- 📌 Self-improving prompts (prompts are editable files in `prompts/`)
- 📌 Investor-ready report rendering (markdown now)
- 📌 Multi-user support and collaboration
- 📌 Advanced contradiction *resolution* (we mark, we don't resolve)

## Next Phases

1. **Phase 2 — Research Engine**: more sources (NewsAPI, GitHub, Wikipedia),
   vector-embedding search over the archive (ChromaDB), dashboard analytics
2. **Phase 3 — Intelligent System**: knowledge graph, advanced validation,
   automated follow-up execution, investor-ready report generation
3. **Phase 4 — Enterprise Platform**: multi-project management, team
   collaboration, production hardening
