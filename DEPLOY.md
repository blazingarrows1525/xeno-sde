# Deploying Kairos

Three pieces: **Neon** (Postgres, already provisioned), two **FastAPI** services on **Render**,
and the **Next.js** app on **Vercel**. The deployed CRM connects to the *same* Neon database
that's already migrated and seeded, so there's no migration step at deploy time.

```
 Vercel (web)  ──HTTPS──>  Render: kairos-crm  ──asyncpg/SSL──>  Neon Postgres
                                   │
                                   └──>  Render: kairos-channel   (delivery simulator)
```

## 1. Backend — Render (Blueprint)

1. Push to GitHub (done): `github.com/blazingarrows1525/xeno-sde`.
2. Render → **New > Blueprint** → pick this repo. Render reads [`render.yaml`](render.yaml) and
   proposes **kairos-crm** and **kairos-channel**.
3. On **kairos-crm**, set the three secrets:
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | your Neon **pooler** connection string (`postgresql://…?sslmode=require`) |
   | `ANTHROPIC_API_KEY` | `sk-ant-…` |
   | `CORS_ORIGINS` | leave as `http://localhost:3000` — `app/main.py` already admits any `*.vercel.app` origin via regex, so a Vercel frontend works without touching this |

   `RECEIPT_HMAC_SECRET` (CRM) and `HMAC_SECRET` (channel) are auto-generated. `kairos-channel`
   needs no manual config.
4. **Apply** → both build from their Dockerfiles. When live, copy the CRM URL
   (e.g. `https://kairos-crm.onrender.com`) and verify `GET /health` returns `{"status":"ok"}`.

> Free-tier services sleep after ~15 min idle; the first request cold-starts in ~30–60 s.

## 2. Frontend — Vercel

1. Vercel → **Add New > Project** → import the same repo.
2. Set **Root Directory** to `apps/web` (Next.js is auto-detected).
3. Add environment variables (only the first is required):
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | your CRM URL from step 1, e.g. `https://kairos-crm.onrender.com` |
   | `NEXT_PUBLIC_BASE_URL` | your Vercel URL (used for OAuth callbacks), e.g. `https://kairos-web.vercel.app` |
   | `AUTH_SECRET` | any long random string (signs the session cookie) |
4. **Deploy**. Copy the resulting URL.

### Login / OAuth

The app is gated by a sign-in screen. It always offers a **one-tap demo workspace** (no
account, no config), so the live deployment is reviewable out of the box. To enable real OAuth,
set a provider's credentials and register its callback URL:

| Provider | Vercel env vars | Callback URL to register |
|----------|-----------------|--------------------------|
| Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | `<base>/api/auth/callback/google` |
| GitHub | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | `<base>/api/auth/callback/github` |

(`<base>` = your `NEXT_PUBLIC_BASE_URL`.) A provider's button only appears wired when its
credentials are present; otherwise users continue with the demo workspace.

## 3. Close the loop

The web app's **"live · AI"** badge confirms it's talking to the backend. CORS already works
out of the box for `*.vercel.app` (regex in `app/main.py`). Only if you serve the frontend from a
**custom domain** do you need to add it to the CRM's `CORS_ORIGINS` (comma-separated) and redeploy.

## Run the containers locally (optional)

```bash
docker build -t kairos-crm apps/crm && \
  docker run -p 8000:8000 --env-file apps/crm/.env kairos-crm

docker build -t kairos-channel apps/channel && \
  docker run -p 8001:8001 kairos-channel
```

## The two-service send loop

Approving a campaign dispatches it to the **separate Channel Service**, which simulates each
delivery lifecycle and calls back into the CRM's `/v1/receipts` with HMAC-signed events. To run
this live in production, set three things on **kairos-crm**:

- `CHANNEL_SERVICE_URL` → the channel's public URL (e.g. `https://kairos-channel.onrender.com`)
- `CRM_PUBLIC_URL` → the CRM's own public URL (the channel calls this back)
- `RECEIPT_HMAC_SECRET` → generated on the CRM; `render.yaml` copies it into the channel's
  `HMAC_SECRET` automatically (`fromService`), so the signatures verify on both ends.

If `CHANNEL_SERVICE_URL` is unset or the channel is asleep (free-tier cold start), approval
**falls back** to a deterministic in-process simulation that writes the same events/stats tables —
so a launch never stalls. Locally, run the channel on `:8001` and the CRM with
`CHANNEL_SERVICE_URL=http://localhost:8001 CRM_PUBLIC_URL=http://localhost:8000` (both HMAC secrets
default to the same dev value, so the loop just works).

## Notes

- The deployed CRM reads config from environment variables (no `.env` file needed in the container).
