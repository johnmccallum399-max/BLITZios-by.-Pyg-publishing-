"""FastAPI surface for BLITZ OS: /research, /search, /stats, /health."""

from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.core.config import Config
from src.core.orchestrator import BLITZOrchestrator
from src.core.state_manager import KnowledgeArchive

app = FastAPI(
    title="BLITZ Intelligence OS API",
    description="Strategic Research & Decision Intelligence Platform",
    version="0.1.0",
)

archive = KnowledgeArchive()
orchestrator = BLITZOrchestrator(archive=archive)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="The research question")
    max_iterations: Optional[int] = Field(
        default=None, ge=1, le=5, description="Override the research loop bound"
    )


class QueryResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    confidence: Optional[float] = None
    sources: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    follow_up: Optional[str] = None
    iterations: Optional[int] = None
    cost: Optional[float] = None
    elapsed_seconds: Optional[float] = None
    doc_id: Optional[str] = None
    error: Optional[str] = None


@app.post("/research", response_model=QueryResponse)
def research(request: QueryRequest):
    result = orchestrator.run(request.query, max_iterations=request.max_iterations)

    if not result["success"]:
        return QueryResponse(success=False, error=result.get("error", "Unknown error"))

    state = result["state"]
    return QueryResponse(
        success=True,
        response=state.get("response", ""),
        confidence=state.get("scores", {}).get("average_confidence", 0),
        sources=state.get("sources", []),
        gaps=state.get("gaps", []),
        follow_up=state.get("follow_up", ""),
        iterations=state.get("iteration", 0),
        cost=state.get("cost", 0.0),
        elapsed_seconds=result.get("elapsed_seconds"),
        doc_id=result.get("doc_id"),
    )


@app.get("/search/{query}")
def search_knowledge(query: str, limit: int = 10):
    results = archive.search(query, limit=limit)
    return {"total": len(results), "results": results}


@app.get("/stats")
def get_stats():
    return archive.get_stats()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "offline_mode": Config.OFFLINE_MODE,
        "llm_configured": bool(Config.OPENAI_API_KEY or Config.ANTHROPIC_API_KEY),
        "web_search_configured": bool(Config.SERPAPI_API_KEY),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
