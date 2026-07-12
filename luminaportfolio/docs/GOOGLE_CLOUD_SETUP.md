# Google Cloud Console Setup Guide — LuminaPortfolio

This walks you through everything needed for Phase 2 of the roadmap:
creating the Google Cloud project, enabling the Photos Library API,
configuring the OAuth consent screen in **Testing** status, and generating
the Client ID / Client Secret the backend needs.

Time required: about 20–30 minutes. Cost: free (no billing account needed
for this API at MVP scale).

---

## 1. Create the Google Cloud project

1. Go to <https://console.cloud.google.com/> and sign in with the Google
   account you want to own the app (this does not have to be the account
   whose photos you'll test with).
2. Click the **project selector** in the top bar → **New Project**.
3. Name it `luminaportfolio` (project IDs are permanent — keep it clean).
4. Leave *Organization* as **No organization** unless you have a Workspace.
5. Click **Create**, then make sure the new project is selected in the top
   bar before continuing.

## 2. Enable the Photos Library API

1. In the left menu: **APIs & Services → Library**.
2. Search for **Photos Library API**.
3. Open it and click **Enable**.

> Note: Google has been migrating Photos access to the newer **Google
> Photos Picker API** for third-party apps. If "Photos Library API" shows a
> deprecation banner for the scopes you need, enable the Picker API as well
> — the OAuth setup below is identical, and the backend only needs the
> media item `baseUrl`s either way.

## 3. Configure the OAuth consent screen (Testing status)

1. **APIs & Services → OAuth consent screen**.
2. Choose **External** (Internal is only available for Workspace orgs) →
   **Create**.
3. Fill in the required fields:
   - **App name**: `LuminaPortfolio`
   - **User support email**: your email
   - **Developer contact email**: your email
   - Logo, app domain, privacy policy: **leave blank for now** — they're
     only required when you apply for verification in Phase 3.
4. **Scopes** step: click **Add or Remove Scopes**, filter for
   `photoslibrary`, and check:
   ```
   https://www.googleapis.com/auth/photoslibrary.readonly
   ```
   (It appears under "sensitive scopes" — that's expected. Testing status
   lets you use it without verification.)
5. **Test users** step: add the Google account emails that will be allowed
   to log in during development — yours plus any teammates/pilot testers.
   You can add up to **100** test users; anyone not on this list will get
   an "access blocked" error at login.
6. Finish and confirm the **Publishing status** shows **Testing**.

## 4. Create the OAuth Client ID and Secret

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. **Application type**: Web application.
3. **Name**: `luminaportfolio-backend`.
4. **Authorized redirect URIs** — add:
   ```
   http://localhost:8000/api/v1/google/callback
   ```
   (Add your deployed API's callback URL here too once you host it, e.g.
   `https://api.yourdomain.com/api/v1/google/callback`.)
5. Click **Create**. Copy the **Client ID** and **Client Secret** from the
   dialog (you can re-view them later under Credentials).

## 5. Wire the credentials into the backend

In `backend/`, copy `.env.example` to `.env` and paste the values:

```
LUMINA_GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
LUMINA_GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxx
LUMINA_GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/google/callback
```

Never commit `.env` — it's already covered by `.gitignore`.

## 6. Verify the flow end-to-end

1. Start the API: `uvicorn app.main:app --reload` (from `backend/`).
2. Open <http://localhost:8000/api/v1/google/login> in a browser while
   signed in as one of your **test users**.
3. Approve the consent screen (it will warn the app is unverified — that's
   the Testing-status warning, click *Continue*).
4. The callback returns a JSON payload with an `access_token`.
5. Call `GET /api/v1/google/photos?access_token=...` — you should see your
   media items. Feed any item's `baseUrl` (with `=d` appended for full
   resolution) into `POST /api/v1/analyze`.

## 7. What to expect at Phase 3 (verification)

When you're ready to leave Testing status, Google's verification for the
sensitive `photoslibrary.readonly` scope will require:

- A public domain hosting your **Privacy Policy** and **Terms of Service**,
  linked on the consent screen.
- A short **YouTube demo video** showing login → Photos access → analysis.
- A written justification for the scope, e.g. *"High-resolution download
  via the baseUrl is necessary to run focus/sharpness edge detection and
  resolution calculations."*

Until then, the 100-test-user limit is the working boundary for the closed
beta.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Access blocked: app not verified" at login | The signing-in account isn't in the Test users list (step 3.5). |
| `redirect_uri_mismatch` error | The URI in step 4.4 must match `LUMINA_GOOGLE_REDIRECT_URI` **exactly**, including scheme, port, and path. |
| `403 PERMISSION_DENIED` calling the Photos API | The API isn't enabled on this project (step 2), or the token was issued without the `photoslibrary.readonly` scope. |
| Backend returns 503 on `/google/login` | `.env` is missing or the `LUMINA_` variables aren't set. |
