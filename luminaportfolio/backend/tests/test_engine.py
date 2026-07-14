"""Scoring-engine tests using synthetic images, so no fixtures are needed."""

import cv2
import numpy as np
import pytest

from app.scoring.engine import (
    DEFAULT_WEIGHTS,
    ScoringError,
    normalize_weights,
    score_bytes,
    score_image,
)


def make_detailed_image(size: int = 1200) -> np.ndarray:
    """A high-frequency checkerboard with noise: sharp, high contrast."""
    rng = np.random.default_rng(42)
    tile = np.array([[0, 255], [255, 0]], dtype=np.uint8)
    board = np.tile(tile, (size // 2, size // 2))
    noise = rng.integers(0, 30, board.shape, dtype=np.uint8)
    gray = cv2.subtract(board, noise)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def test_sharp_image_outscores_blurred_copy():
    sharp = make_detailed_image()
    blurred = cv2.GaussianBlur(sharp, (31, 31), 0)

    sharp_scores = score_image(sharp)
    blurred_scores = score_image(blurred)

    assert sharp_scores.sharpness > blurred_scores.sharpness
    assert sharp_scores.overall > blurred_scores.overall


def test_scores_are_bounded():
    scores = score_image(make_detailed_image())
    for value in (scores.sharpness, scores.lighting, scores.contrast,
                  scores.composition, scores.resolution, scores.overall):
        assert 0.0 <= value <= 100.0


def test_high_resolution_beats_thumbnail():
    large = make_detailed_image(2000)
    small = cv2.resize(large, (200, 200))
    assert score_image(large).resolution > score_image(small).resolution


def test_weight_overrides_change_overall():
    image = make_detailed_image()
    default = score_image(image)
    sharpness_only = score_image(image, weights={"sharpness": 1.0, "lighting": 0,
                                                 "contrast": 0, "composition": 0,
                                                 "resolution": 0})
    assert sharpness_only.overall == pytest.approx(default.sharpness, abs=0.01)


def test_normalize_weights_rejects_unknown_criterion():
    with pytest.raises(ScoringError):
        normalize_weights({"vibes": 1.0})


def test_normalize_weights_defaults_sum_to_one():
    assert sum(normalize_weights(None).values()) == pytest.approx(1.0)
    assert set(normalize_weights(None)) == set(DEFAULT_WEIGHTS)


def test_score_bytes_roundtrip():
    image = make_detailed_image(400)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    breakdown = score_bytes(encoded.tobytes())
    assert breakdown.verdict in {"portfolio-ready", "strong", "usable", "cull"}


def test_score_bytes_rejects_garbage():
    with pytest.raises(ScoringError):
        score_bytes(b"definitely not an image")
