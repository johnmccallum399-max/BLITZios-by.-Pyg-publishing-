"""LuminaPortfolio API entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import analyze, google_photos

app = FastAPI(
    title="LuminaPortfolio API",
    description=(
        "Aesthetic scoring engine for portfolio curation: submit image URLs "
        "or uploads, receive per-criterion scores (sharpness, lighting, "
        "contrast, composition, resolution) and a weighted overall score."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(google_photos.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "service": "luminaportfolio-api", "version": app.version}
