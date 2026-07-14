"""API tests via FastAPI's TestClient (no network access required)."""

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def encoded_test_image() -> bytes:
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, (600, 800, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_upload_returns_score_breakdown():
    response = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("test.png", encoded_test_image(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    for key in ("sharpness", "lighting", "contrast", "composition",
                "resolution", "overall", "verdict"):
        assert key in body


def test_analyze_upload_rejects_non_image():
    response = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 422


def test_analyze_rejects_invalid_url():
    response = client.post("/api/v1/analyze", json={"image_url": "not-a-url"})
    assert response.status_code == 422


def test_google_login_unconfigured_returns_503():
    response = client.get("/api/v1/google/login", follow_redirects=False)
    assert response.status_code == 503
