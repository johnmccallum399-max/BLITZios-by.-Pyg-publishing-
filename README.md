# 🧠 BLITZ Intelligence OS

## Strategic Research & Decision Intelligence Platform

BLITZ OS transforms research questions into evidence-based answers through the core intelligence loop:

```
Query → Intent Detection → Task Decomposition →
Multi-Source Research → Evidence Validation →
Gap Detection → (Iterate) → Response → Knowledge Archive
```

Every completed run is archived as reusable intellectual capital: the question, the detected intent, the task graph, the evidence, the confidence scores, the contradictions, the gaps, and the follow-up question.

## Features

- 🎯 **Intent Detection** — classifies any query into Market / Technical / Financial / Strategic / Mixed with entities, timeframe, scope, and assumptions
- 📋 **Task Planning** — decomposes the question into a 3–5 task DAG (parallel + sequential)
- 🔍 **Multi-Source Research** — web search (SerpAPI) + academic papers (ArXiv), executed in parallel
- ✅ **Evidence Validation** — per-item credibility, recency, and strength scoring; cross-source contradiction detection
- 🔎 **Gap Detection** — identifies missing perspectives and generates one follow-up question per run
- 🔁 **Bounded Recursion** — gaps feed back into planning, hard-capped by `MAX_ITERATIONS` and a per-query cost circuit breaker
- 📚 **Knowledge Archive** — everything stored as searchable JSONL, no database required
- 🖥️ **Web UI** (Streamlit) and 🔌 **REST API** (FastAPI)

## Degradation by design

BLITZ runs at whatever capability level your keys allow — it never hard-fails on a missing key:

| Configured | Behavior |
|---|---|
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | LLM-powered intent, planning, contradiction detection, gap analysis |
| No LLM key | Deterministic heuristic agents (keyword classification, template task graphs) |
| `SERPAPI_API_KEY` | Real web evidence |
| No search key | Clearly-labelled mock evidence (confidence capped at 40%) |
| `BLITZ_OFFLINE=1` | Zero network calls — for tests and demos |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (optional — works without keys)
cp .env.example .env
# Edit .env with your API keys

# 3. Start API + UI together
python run.py
# UI:  http://localhost:8501
# API: http://localhost:8000 (docs at /docs)
```

### CLI (no server needed)

```bash
python -m src.cli "What are the top 3 trends in AI-powered legal tech for 2025?"
python -m src.cli --search "legal tech"   # search the knowledge archive
python -m src.cli --stats                 # archive statistics
```

### Docker

```bash
docker compose up --build
```

### Tests

```bash
pytest        # fully offline, no API keys or network needed
```

## Architecture

```
User Input
    │
Intent Engine (MODULE_A)          src/agents/intent_engine.py
    │
Task Planner (MODULE_B)           src/agents/planner.py
    │
Researcher (MODULE_C)             src/agents/researcher.py
    │        ├─ WebSearchTool     src/tools/web_search.py
    │        └─ ArxivTool         src/tools/arxiv_tool.py
    │
Validator (MODULE_D)              src/agents/validator.py
    │
Gap Finder (MODULE_E)             src/agents/gap_finder.py
    │
    ├── gaps + budget remaining? ──► back to Task Planner
    │
Response Generator (MODULE_F)     src/core/orchestrator.py
    │
Knowledge Archive (MODULE_G)      src/core/state_manager.py  (JSONL)
```

The loop is a **LangGraph state machine** (`src/core/orchestrator.py`) with three independent kill switches:

1. `MAX_ITERATIONS` (default 3) bounds the recursion
2. `CONFIDENCE_TARGET` (default 0.7) ends the loop early when evidence is strong
3. `MAX_COST_PER_QUERY` (default $0.50) — a shared cost tracker aborts all LLM spending past budget and returns partial results

## Tech Stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph |
| LLMs | OpenAI GPT-4o-mini (primary), Anthropic Claude Haiku (fallback), heuristics (offline) |
| Research | SerpAPI, ArXiv Atom API |
| Storage | JSONL (append-only, greppable) |
| API | FastAPI |
| UI | Streamlit |

## Demo Queries

See `demo_queries.json`:

1. *Market*: "What are the top 3 trends in AI-powered legal tech for 2025?"
2. *Technical*: "What's the best open-source vector database for production use in 2025?"
3. *Financial*: "What's the projected CAGR for the generative AI market through 2028?"

## License

MIT
