"""Request/response models for the LuminaPortfolio API."""

from pydantic import BaseModel, Field, HttpUrl


class ScoreWeights(BaseModel):
    """Optional per-request overrides for the scoring weights (the Pro-tier
    "sliders"). Omitted criteria keep their default weight; the server
    renormalizes so the weights sum to 1."""

    sharpness: float | None = Field(default=None, ge=0)
    lighting: float | None = Field(default=None, ge=0)
    contrast: float | None = Field(default=None, ge=0)
    composition: float | None = Field(default=None, ge=0)
    resolution: float | None = Field(default=None, ge=0)

    def as_dict(self) -> dict[str, float]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class AnalyzeRequest(BaseModel):
    image_url: HttpUrl
    weights: ScoreWeights | None = None


class BatchAnalyzeRequest(BaseModel):
    image_urls: list[HttpUrl] = Field(min_length=1, max_length=50)
    weights: ScoreWeights | None = None


class ScoreResponse(BaseModel):
    sharpness: float
    lighting: float
    contrast: float
    composition: float
    resolution: float
    overall: float
    verdict: str


class BatchItemResult(BaseModel):
    image_url: HttpUrl
    scores: ScoreResponse | None = None
    error: str | None = None


class BatchAnalyzeResponse(BaseModel):
    results: list[BatchItemResult]
