# LuminaPortfolio

Aesthetic photo-scoring service for portfolio curation. Models, creators,
and talent agencies submit photos (directly, by URL, or from Google
Photos), and the engine scores each image 0–100 on five criteria and
returns a weighted overall score with a verdict — so the strongest shots
surface automatically.

## Scoring criteria

| Criterion | Method | Default weight |
|---|---|---|
| Sharpness | Variance of the Laplacian (threshold 150) | 0.30 |
| Lighting | Mean brightness vs. ideal midtone + clipping penalty | 0.20 |
| Resolution | Megapixels vs. 12 MP target | 0.20 |
| Contrast | RMS contrast (grayscale std-dev) | 0.15 |
| Composition | Rule-of-thirds proximity of the subject (face detection, edge-centroid fallback) | 0.15 |

Weights are adjustable per request (the Pro-tier "sliders"): pass a
`weights` object and the server renormalizes.

## Quick start

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs: <http://localhost:8000/docs>

Score an image:

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"image_url": "https://example.com/headshot.jpg",
       "weights": {"sharpness": 0.5, "lighting": 0.3}}'
```

Or upload directly:

```bash
curl -X POST http://localhost:8000/api/v1/analyze/upload \
  -F file=@portrait.jpg
```

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `POST /api/v1/analyze` | Score one image by URL |
| `POST /api/v1/analyze/upload` | Score an uploaded file |
| `POST /api/v1/analyze/batch` | Score up to 50 URLs concurrently (B2B culling) |
| `GET /api/v1/google/login` | Start Google Photos OAuth (read-only scope) |
| `GET /api/v1/google/callback` | OAuth code → token exchange |
| `GET /api/v1/google/photos` | List the user's media items |

Google Photos endpoints need OAuth credentials — follow
[docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md) to create them
(about 25 minutes, free).

## Tests

```bash
cd backend
pytest
```

Tests use synthetic images (sharp vs. blurred, large vs. thumbnail) so no
fixtures or network access are required.

## Roadmap position

This is the **Phase 1 MVP backend** from the LuminaPortfolio roadmap:

- [x] Scoring engine (sharpness / lighting / contrast / composition / resolution)
- [x] FastAPI wrapper with URL, upload, and batch endpoints
- [x] Adjustable score weights
- [x] Google Photos OAuth flow (Phase 2 scaffolding, Testing-status ready)
- [ ] Calibrate thresholds against real portraits (`LUMINA_SHARPNESS_THRESHOLD`)
- [ ] React/Next.js frontend
- [ ] Deploy API (Render / Heroku / AWS Lambda)
- [ ] Phase 3: OAuth verification (privacy policy, ToS, demo video)
