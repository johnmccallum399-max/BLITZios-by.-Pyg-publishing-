"""LuminaPortfolio scoring engine.

Scores a photograph on five aesthetic/technical criteria, each normalized
to 0-100, and combines them into a weighted overall score. The weights are
caller-adjustable to support the Pro-tier "interactive sliders" feature.

Criteria (per the LuminaPortfolio System Design Document):
  - sharpness:   variance of the Laplacian; threshold 150 marks a photo
                 as acceptably sharp (tune per camera class)
  - lighting:    mean brightness vs. ideal midtone, penalized for clipped
                 shadows/highlights
  - contrast:    RMS contrast (std-dev of grayscale intensity)
  - composition: rule-of-thirds proximity of the subject (largest face if
                 one is found, else the edge-density centroid)
  - resolution:  megapixels vs. a 12 MP full-score target
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import cv2
import numpy as np

# Laplacian variance at/above which a photo earns a passing (50) sharpness
# score; twice this earns 100. Calibrate against real portraits: high-end
# sensors trend higher, smartphone shots with heavy denoising trend lower.
DEFAULT_SHARPNESS_THRESHOLD = 150.0

# Grayscale std-dev that earns full contrast marks.
CONTRAST_FULL_SCORE_STD = 55.0

# Ideal mean brightness for a well-exposed midtone.
IDEAL_BRIGHTNESS = 125.0

# Fraction of clipped pixels tolerated before the lighting score is penalized.
CLIPPING_TOLERANCE = 0.05

# Megapixels that earn full resolution marks.
FULL_SCORE_MEGAPIXELS = 12.0

DEFAULT_WEIGHTS: dict[str, float] = {
    "sharpness": 0.30,
    "lighting": 0.20,
    "contrast": 0.15,
    "composition": 0.15,
    "resolution": 0.20,
}


@dataclass
class ScoreBreakdown:
    sharpness: float
    lighting: float
    contrast: float
    composition: float
    resolution: float
    overall: float
    verdict: str

    def to_dict(self) -> dict:
        return asdict(self)


class ScoringError(ValueError):
    """Raised when an image cannot be decoded or scored."""


def _clamp(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def score_sharpness(gray: np.ndarray, threshold: float = DEFAULT_SHARPNESS_THRESHOLD) -> float:
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return _clamp(variance / threshold * 50.0)


def score_contrast(gray: np.ndarray) -> float:
    return _clamp(float(gray.std()) / CONTRAST_FULL_SCORE_STD * 100.0)


def score_lighting(gray: np.ndarray) -> float:
    mean = float(gray.mean())
    base = 100.0 - abs(mean - IDEAL_BRIGHTNESS) / IDEAL_BRIGHTNESS * 100.0

    clipped = float(np.count_nonzero(gray < 10) + np.count_nonzero(gray > 245))
    clipped_fraction = clipped / gray.size
    penalty = max(0.0, clipped_fraction - CLIPPING_TOLERANCE) * 200.0

    return _clamp(base - penalty)


def _detect_face(gray: np.ndarray) -> tuple[float, float] | None:
    """Center of the largest detected face, or None. Haar cascades were
    removed in OpenCV 5, so this degrades to None on builds without them."""
    if not hasattr(cv2, "CascadeClassifier"):
        return None
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if cascade.empty():
        return None
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return (x + w / 2.0, y + h / 2.0)


def _subject_point(gray: np.ndarray) -> tuple[float, float]:
    """Locate the photo's subject: largest detected face when the OpenCV
    build supports it, else the centroid of the edge map (a proxy for where
    the visual detail concentrates)."""
    face = _detect_face(gray)
    if face is not None:
        return face

    edges = cv2.Canny(gray, 100, 200)
    ys, xs = np.nonzero(edges)
    if len(xs) == 0:
        h, w = gray.shape
        return (w / 2.0, h / 2.0)
    return (float(xs.mean()), float(ys.mean()))


def score_composition(gray: np.ndarray) -> float:
    h, w = gray.shape
    sx, sy = _subject_point(gray)

    thirds = [(w / 3.0, h / 3.0), (2 * w / 3.0, h / 3.0),
              (w / 3.0, 2 * h / 3.0), (2 * w / 3.0, 2 * h / 3.0)]
    nearest = min(np.hypot(sx - tx, sy - ty) for tx, ty in thirds)

    # A subject sitting exactly on a thirds intersection scores 100; the
    # score falls off linearly and reaches 0 at one-third of the diagonal.
    diagonal = float(np.hypot(w, h))
    return _clamp(100.0 * (1.0 - nearest / (diagonal / 3.0)))


def score_resolution(image: np.ndarray) -> float:
    megapixels = (image.shape[0] * image.shape[1]) / 1_000_000.0
    return _clamp(megapixels / FULL_SCORE_MEGAPIXELS * 100.0)


def _verdict(overall: float) -> str:
    if overall >= 80:
        return "portfolio-ready"
    if overall >= 60:
        return "strong"
    if overall >= 40:
        return "usable"
    return "cull"


def normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    """Merge caller-supplied weights over the defaults and renormalize so
    they sum to 1. Unknown criteria are rejected."""
    if not weights:
        return dict(DEFAULT_WEIGHTS)
    unknown = set(weights) - set(DEFAULT_WEIGHTS)
    if unknown:
        raise ScoringError(f"Unknown scoring criteria: {sorted(unknown)}")
    merged = {**DEFAULT_WEIGHTS, **{k: float(v) for k, v in weights.items()}}
    total = sum(merged.values())
    if total <= 0:
        raise ScoringError("Scoring weights must sum to a positive value")
    return {k: v / total for k, v in merged.items()}


def score_image(
    image: np.ndarray,
    weights: dict[str, float] | None = None,
    sharpness_threshold: float = DEFAULT_SHARPNESS_THRESHOLD,
) -> ScoreBreakdown:
    """Score a decoded BGR (or grayscale) image array."""
    if image is None or image.size == 0:
        raise ScoringError("Empty image")

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    scores = {
        "sharpness": score_sharpness(gray, sharpness_threshold),
        "lighting": score_lighting(gray),
        "contrast": score_contrast(gray),
        "composition": score_composition(gray),
        "resolution": score_resolution(image),
    }
    w = normalize_weights(weights)
    overall = _clamp(sum(scores[k] * w[k] for k in scores))

    return ScoreBreakdown(**scores, overall=round(overall, 2), verdict=_verdict(overall))


def score_bytes(
    data: bytes,
    weights: dict[str, float] | None = None,
    sharpness_threshold: float = DEFAULT_SHARPNESS_THRESHOLD,
) -> ScoreBreakdown:
    """Decode raw image bytes (JPEG/PNG/WebP...) and score them."""
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ScoringError("Could not decode image bytes (unsupported or corrupt format)")
    return score_image(image, weights=weights, sharpness_threshold=sharpness_threshold)
