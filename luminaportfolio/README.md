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

## Frontend

```bash
cd frontend
npm install
npm run dev   # → http://localhost:3000
```

The frontend proxies `/api/v1/*` to the backend, so both must be running
locally. In production set `NEXT_PUBLIC_API_URL` to your deployed backend URL.

## Tests

```bash
cd backend
pytest
```

Tests use synthetic images (sharp vs. blurred, large vs. thumbnail) so no
fixtures or network access are required.

## Deployment

### Backend → Render.com (free tier)

1. Push this repo to GitHub (already done).
2. Go to [render.com](https://render.com) → **New → Web Service**.
3. Connect the repo, set **Root Directory** to `luminaportfolio/backend`.
4. Render auto-detects `render.yaml` — confirm the settings and deploy.
5. In the Render dashboard → **Environment**, add:
   - `LUMINA_CORS_ORIGINS` → `["https://your-app.vercel.app"]`
   - `LUMINA_PUBLIC_URL` → `https://luminaportfolio-api.onrender.com`
   - `LUMINA_GOOGLE_CLIENT_ID` / `LUMINA_GOOGLE_CLIENT_SECRET` (Phase 2)
   - `LUMINA_GOOGLE_REDIRECT_URI` → `https://luminaportfolio-api.onrender.com/api/v1/google/callback`

> **Free tier note:** the service sleeps after 15 minutes of inactivity and
> takes ~30 s to wake. Upgrade to Starter ($7/mo) to stay live.

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**.
2. Import this GitHub repo, set **Root Directory** to `luminaportfolio/frontend`.
3. Vercel reads `vercel.json` automatically.
4. Update the `destination` URL in `vercel.json` to your actual Render URL,
   or set `NEXT_PUBLIC_API_URL` in **Vercel → Settings → Environment Variables**.
5. Deploy — Vercel rebuilds on every push to `main`.

### Alternative: Railway / Heroku

A `Procfile` is included in `backend/` for Railway and Heroku compatibility:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Calibrating the sharpness threshold

The default threshold of 150 works well for full-frame DSLR / mirrorless
portraits. Smartphone shots with heavy denoising typically score lower; studio
medium-format shots score higher. Use the bundled calibration utility:

```bash
cd backend
python calibrate.py \
  --sharp  /path/to/your/keepers/ \
  --blurry /path/to/your/rejects/ \
  --plot   # optional histogram (requires matplotlib)
```

It prints the Laplacian variance for each image, reports class means, and
suggests a threshold. Set the result as:

```bash
export LUMINA_SHARPNESS_THRESHOLD=220   # example
```

or add it to `backend/.env` for local use, or to your Render environment
variables for production.

## Roadmap position

- [x] Scoring engine (sharpness / lighting / contrast / composition / resolution)
- [x] FastAPI wrapper with URL, upload, and batch endpoints
- [x] Adjustable score weights
- [x] Google Photos OAuth flow (Phase 2 scaffolding, Testing-status ready)
- [x] React/Next.js frontend
- [x] Deployment configs (Render + Vercel + Procfile)
- [x] Sharpness calibration utility
- [ ] Calibrate threshold against real portraits and set `LUMINA_SHARPNESS_THRESHOLD`
- [ ] Phase 3: OAuth verification (privacy policy, ToS, demo video for Google review)
