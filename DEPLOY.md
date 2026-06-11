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
   | `CORS_ORIGINS` | your Vercel URL (fill in after step 2, e.g. `https://kairos-web.vercel.app`) |

   `RECEIPT_HMAC_SECRET` (CRM) and `HMAC_SECRET` (channel) are auto-generated. `kairos-channel`
   needs no manual config.
4. **Apply** → both build from their Dockerfiles. When live, copy the CRM URL
   (e.g. `https://kairos-crm.onrender.com`) and verify `GET /health` returns `{"status":"ok"}`.

> Free-tier services sleep after ~15 min idle; the first request cold-starts in ~30–60 s.

## 2. Frontend — Vercel

1. Vercel → **Add New > Project** → import the same repo.
2. Set **Root Directory** to `apps/web` (Next.js is auto-detected).
3. Add an environment variable:
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | your CRM URL from step 1, e.g. `https://kairos-crm.onrender.com` |
4. **Deploy**. Copy the resulting URL.

## 3. Close the loop

Set the CRM's `CORS_ORIGINS` (Render → kairos-crm → Environment) to your Vercel URL and let it
redeploy. The web app's "live · Claude" badge confirms it's talking to the backend.

## Run the containers locally (optional)

```bash
docker build -t kairos-crm apps/crm && \
  docker run -p 8000:8000 --env-file apps/crm/.env kairos-crm

docker build -t kairos-channel apps/channel && \
  docker run -p 8001:8001 kairos-channel
```

## Notes

- The deployed CRM reads config from environment variables (no `.env` file needed in the container).
- Wiring the live send→receipt loop later: point the CRM's `CHANNEL_SERVICE_URL` at the channel
  service, the channel's `CRM_RECEIPTS_URL` back at the CRM, and set both HMAC secrets equal.
