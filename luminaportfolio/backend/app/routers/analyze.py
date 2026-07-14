"""Image analysis endpoints: score by URL, by upload, or in batch."""

import asyncio

import httpx
from fastapi import APIRouter, HTTPException, UploadFile

from ..config import settings
from ..schemas import (
    AnalyzeRequest,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    BatchItemResult,
    ScoreResponse,
)
from ..scoring.engine import ScoringError, score_bytes

router = APIRouter(prefix="/api/v1", tags=["analyze"])


async def _fetch_image(client: httpx.AsyncClient, url: str) -> bytes:
    response = await client.get(url, timeout=settings.fetch_timeout_seconds)
    response.raise_for_status()
    if len(response.content) > settings.max_image_bytes:
        raise ScoringError(
            f"Image exceeds the {settings.max_image_bytes // (1024 * 1024)} MB limit"
        )
    return response.content


def _score(data: bytes, weights_model) -> ScoreResponse:
    weights = weights_model.as_dict() if weights_model else None
    breakdown = score_bytes(
        data, weights=weights, sharpness_threshold=settings.sharpness_threshold
    )
    return ScoreResponse(**breakdown.to_dict())


@router.post("/analyze", response_model=ScoreResponse)
async def analyze_url(request: AnalyzeRequest) -> ScoreResponse:
    """Fetch a single image by URL and return its score breakdown."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            data = await _fetch_image(client, str(request.image_url))
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=422, detail=f"Could not fetch image: {exc}")
    try:
        return _score(data, request.weights)
    except ScoringError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/analyze/upload", response_model=ScoreResponse)
async def analyze_upload(file: UploadFile) -> ScoreResponse:
    """Score a directly uploaded image file."""
    data = await file.read()
    if len(data) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file too large")
    try:
        return _score(data, None)
    except ScoringError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/analyze/batch", response_model=BatchAnalyzeResponse)
async def analyze_batch(request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
    """Score up to 50 images by URL concurrently. Individual failures are
    reported per item so one bad URL doesn't fail the whole batch — this is
    the endpoint behind the B2B batch-culling workflow."""

    async with httpx.AsyncClient(follow_redirects=True) as client:

        async def process(url) -> BatchItemResult:
            try:
                data = await _fetch_image(client, str(url))
                return BatchItemResult(image_url=url, scores=_score(data, request.weights))
            except (httpx.HTTPError, ScoringError) as exc:
                return BatchItemResult(image_url=url, error=str(exc))

        results = await asyncio.gather(*(process(url) for url in request.image_urls))

    return BatchAnalyzeResponse(results=list(results))
