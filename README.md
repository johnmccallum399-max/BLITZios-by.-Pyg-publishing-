# 🧠 BLITZ Intelligence OS

**Ask a research question. Get an evidence-scored answer, the gaps in it, and the next question to ask — and keep every run in a searchable knowledge base.**

## What you can do with it

| You want to... | Do this |
|---|---|
| **Ask** a research question | `python -m src.cli "your question"` — or use the web UI |
| **Trust** the answer appropriately | Every answer includes a confidence score, its sources, detected contradictions, and its capability mode |
| **See what's missing** | Every answer lists the gaps found and one follow-up question worth asking next |
| **Track** everything you've researched | `python -m src.cli --search "term"` and `--stats`; also in the UI sidebar and via the API |
| **Check** what the system can do right now | `python -m src.cli --status` |

## Setup — 3 steps

```bash
# Step 1 — install (one command)
pip install -r requirements.txt

# Step 2 — check your mode (works immediately, no keys required)
python -m src.cli --status

# Step 3 — run
python run.py                     # web UI at http://localhost:8501
# or, without any server:
python -m src.cli "What are the top 3 trends in AI-powered legal tech for 2025?"
```

**API keys are optional.** Without them, BLITZ runs a free demo mode that exercises the full workflow on placeholder evidence. To do real research, copy `.env.example` to `.env` and add keys (see next section) — no code changes needed.

## What to expect — by mode

`--status` (CLI), `/health` (API), the UI banner, and every report footer tell you which mode you're in. There are no silent downgrades.

| Mode | You have | Speed / cost per query | What the output means |
|---|---|---|---|
| **Full intelligence** | LLM key + `SERPAPI_API_KEY` | ~30s–3min, ≤ $0.50 (hard-enforced) | Real research: cited web + academic sources, LLM planning, contradiction checks |
| **LLM reasoning, mock evidence** | LLM key only | seconds, ≤ $0.50 | Smart analysis of placeholder data — confidence capped at 40%, don't act on it |
| **Real evidence, heuristic reasoning** | `SERPAPI_API_KEY` only | ~10–60s, $0 | Real sources gathered and scored; planning/gap analysis uses fixed rules |
| **Heuristic demo** | no keys | ~1s, $0 | Full workflow on placeholder data — confidence capped at 40%, don't act on it |

LLM key = `OPENAI_API_KEY` (preferred) or `ANTHROPIC_API_KEY` in `.env`.

**Guarantees in every mode:**

- Each query is decomposed into 3–5 research tasks and answered with a confidence score, sources, gaps, and a follow-up question
- Recursion is bounded: at most `MAX_ITERATIONS` (default 3) research passes per query
- Spend is bounded: a circuit breaker aborts LLM calls past `MAX_COST_PER_QUERY` (default $0.50) and returns partial results
- Every run is archived to `data/knowledge.jsonl` — plain, greppable JSONL you own

## Tracking your knowledge base

Every completed query becomes reusable intellectual capital — question, intent, task graph, evidence, scores, contradictions, gaps, follow-up — stored append-only in `data/knowledge.jsonl`.

```bash
python -m src.cli --status              # mode + archive totals + spend to date
python -m src.cli --stats               # archive totals as JSON
python -m src.cli --search "legal tech" # full-text search of past research
```

Same data over HTTP: `GET /stats`, `GET /search/{term}`. The web UI shows totals and archive search in the sidebar.

## How the loop works

```
Query → Intent Detection → Task Decomposition (3–5 task DAG) →
Parallel Research (SerpAPI web + ArXiv academic) →
Evidence Validation (credibility · recency · strength · contradictions) →
Gap Detection → iterate if gaps remain (bounded) →
Report → Knowledge Archive (JSONL)
```

Implemented as a LangGraph state machine in `src/core/orchestrator.py`; each module lives in `src/agents/` and is independently upgradable. Prompts are plain text files in `prompts/` — edit them without touching code.

## Other ways to run

```bash
# API only (docs at http://localhost:8000/docs)
uvicorn src.api.routes:app --port 8000

# Docker (API + UI)
docker compose up --build

# Tests — fully offline, no keys or network needed
pytest
```

## Project layout

```
src/core/       config, state + JSONL archive, LangGraph orchestrator
src/agents/     intent_engine, planner, researcher, validator, gap_finder
src/tools/      model_router (LLM + cost tracking), web_search, arxiv_tool
src/api/        FastAPI routes
src/ui/         Streamlit dashboard
prompts/        editable prompt templates
tests/          offline, deterministic test suite
data/           knowledge.jsonl (your archive; gitignored)
```

See `IMPLEMENTATION_PLAN.md` for what's deliberately deferred (knowledge graph, self-improving prompts, investor-report rendering) and `GAP_REVIEW.md` for the recursive gap review of this MVP.

## License

MIT
