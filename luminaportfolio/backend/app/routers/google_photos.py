"""Google Photos Library API integration (Phase 2).

Implements the standard OAuth 2.0 authorization-code flow with the
read-only Photos scope, then lists media items so the frontend can submit
their baseUrls to /api/v1/analyze.

Requires LUMINA_GOOGLE_CLIENT_ID / LUMINA_GOOGLE_CLIENT_SECRET in the
environment — see docs/GOOGLE_CLOUD_SETUP.md for how to obtain them.

Note: while the OAuth consent screen is in "Testing" status, only the
(up to 100) test users added in the Google Cloud Console can log in.
"""

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..config import settings

router = APIRouter(prefix="/api/v1/google", tags=["google-photos"])

SCOPE = "https://www.googleapis.com/auth/photoslibrary.readonly"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
PHOTOS_API = "https://photoslibrary.googleapis.com/v1"


def _require_credentials() -> None:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                "Google OAuth is not configured. Set LUMINA_GOOGLE_CLIENT_ID and "
                "LUMINA_GOOGLE_CLIENT_SECRET (see docs/GOOGLE_CLOUD_SETUP.md)."
            ),
        )


@router.get("/login")
async def login() -> RedirectResponse:
    """Redirect the user to Google's consent screen."""
    _require_credentials()
    params = httpx.QueryParams(
        client_id=settings.google_client_id,
        redirect_uri=settings.google_redirect_uri,
        response_type="code",
        scope=SCOPE,
        access_type="offline",
        prompt="consent",
    )
    return RedirectResponse(f"{AUTH_ENDPOINT}?{params}")


@router.get("/callback")
async def callback(code: str) -> dict:
    """Exchange the authorization code for tokens.

    MVP behavior: the token payload is returned to the caller so the client
    can hold the access token. Before public beta, switch to server-side
    session storage — do not ship token-to-client in production.
    """
    _require_credentials()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {response.text}")
    return response.json()


@router.get("/photos")
async def list_photos(
    access_token: str = Query(..., description="OAuth access token from /callback"),
    page_size: int = Query(default=50, ge=1, le=100),
    page_token: str | None = None,
) -> dict:
    """List the user's media items. Each item's baseUrl (append e.g. `=d`
    for the original bytes) can be fed straight into /api/v1/analyze."""
    params: dict = {"pageSize": page_size}
    if page_token:
        params["pageToken"] = page_token
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PHOTOS_API}/mediaItems",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Photos API error: {response.text}")
    return response.json()
