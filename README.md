# Kairos — AI-Native Mini CRM

> An **autonomous-but-supervised growth marketer**. State a goal in plain language —
> *"Win back customers who haven't ordered in 60 days"* — and Kairos analyses your shoppers,
> builds an audience, recommends a channel, **predicts the outcome before sending**, waits for your
> approval, runs the campaign, and **calibrates** as real events come back.

<p align="center">
  <a href="https://xeno-sde-six.vercel.app"><b>▶ Live App</b></a> &nbsp;·&nbsp;
  <a href="https://kairos-crm-79em.onrender.com/docs"><b>API / OpenAPI</b></a> &nbsp;·&nbsp;
  <a href="BLUEPRINT.md"><b>Full Design (BLUEPRINT)</b></a>
</p>

> ⏳ The API is on a free Render tier and sleeps after ~15 min idle — the **first** request may
> cold-start for 30–60s, then it's instant. The agent runs on a live LLM against a live Neon
> Postgres with 200 seeded shoppers and 6 campaigns.

Built for the **Xeno Engineering Take-Home (2026)**.

---

## The bet

Most submissions build *"a CRM with a **Generate message** button."* Kairos is the other thing:
an agent that runs a continuous **Plan → Act → Learn loop**, keeps a human in the approval seat,
and *visibly gets smarter* every campaign.

### The three things to look at

1. **The glass-box agent** — type a goal and watch every reasoning step, tool call, and the
   *exact data it pulled* stream into the UI in real time (Server-Sent Events). No black box.
2. **The Segment DSL compiler** — the LLM **never writes SQL**. It emits a typed, validated JSON
   spec; a deterministic compiler turns it into **parameterized** SQL. Injection-safe by
   construction, auditable, and covered by 15 unit tests.
3. **The calibration chart** — predicted vs. actual ROAS converging over campaigns. Proof the
   system *learns*, not just *generates*.

---

## Architecture

```
  Next.js 16 (Vercel)                 FastAPI · CRM core (Render)             Neon Postgres
  ┌─────────────────────┐  HTTPS      ┌──────────────────────────────┐  asyncpg  ┌───────────┐
  │ Agent Console        │── SSE ────▶│ agent loop · tool-use LLM    │── SSL ──▶│ customers  │
  │ Campaigns + detail   │            │ Segment DSL → parameterized  │           │ orders     │
  │ Insights / ROI       │◀── JSON ───│ campaigns · analytics · events│          │ campaigns  │
  └─────────────────────┘            └──────────────┬───────────────┘           │ messages   │
                                                     │ HMAC-signed receipts       └───────────┘
                                                     ▼
                                      FastAPI · Channel Service (Render)
                                      delivery simulator + async event callbacks
```

**Layered & auditable:** `api → service → repository → model`. The LLM only ever emits
schema-validated DSL, so AI output is testable like any other code path.

---

## Monorepo layout

```
apps/
  crm/        FastAPI — CRM core: ingestion, Segment DSL, campaigns, agent loop, analytics
    app/
      agents/     the Plan→Act→Learn runtime + tools (build_segment, …)
      segments/   ⭐ the Segment DSL and its compiler — read this first
      api/        REST + the SSE agent endpoint
      events/     campaign event ingestion + state machine
      models/     SQLAlchemy models
    scripts/    seed generators (customers/orders, campaigns/stats/messages)
    tests/      38 unit tests (DSL compiler, state machine, agent runtime, models, API)
  channel/    FastAPI — stubbed Channel Service (delivery lifecycle + HMAC callbacks)
  web/        Next.js 16 — Agent Console, Campaign detail, Insights, OAuth login
render.yaml   Render Blueprint (both FastAPI services)   ·   DEPLOY.md — full walkthrough
```

**Start here:** [`apps/crm/app/segments/`](apps/crm/app/segments/) — the DSL and compiler. The
agent proposes a constrained spec; this module compiles it to safe SQL. That boundary is the
whole safety story.

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, Recharts |
| Backend | FastAPI × 2 (CRM core + Channel Service), SQLAlchemy (async) |
| Database | PostgreSQL (Neon, `ap-southeast-1`), asyncpg over SSL |
| AI | Frontier LLM via API — streamed tool-use loop; the model only ever emits validated DSL, never raw SQL |
| Auth | OAuth sign-in (Google / GitHub) with a one-tap demo entry |
| Deploy | Vercel (web) · Render (both APIs, Singapore) · Neon (DB) — all free tier |

---

## Run it locally (Windows / PowerShell)

Two servers against the same live Neon + LLM. Secrets live in `apps/crm/.env` (gitignored):
`DATABASE_URL` (Neon pooler string) and `ANTHROPIC_API_KEY`.

**1 — CRM API** → http://127.0.0.1:8000
```powershell
cd apps/crm
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py        # sets the Windows selector event loop + loads .env
# health: http://127.0.0.1:8000/health   ·   docs: http://127.0.0.1:8000/docs
```

**2 — Web** → http://localhost:3000
```powershell
cd apps/web
npm install
# apps/web/.env.local → NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

> Without `NEXT_PUBLIC_API_URL` the UI falls back to mock data — the Agent Console shows a
> **"live · AI"** vs **"demo data"** badge so you always know which you're looking at.

**Seed data** (first run only):
```powershell
cd apps/crm
.\.venv\Scripts\python.exe -m scripts.seed --customers 200 --wipe
.\.venv\Scripts\python.exe -m scripts.seed_campaigns --wipe
```

---

## Tests

```powershell
cd apps/crm
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q     # 38 passing
```

The 15 DSL-compiler tests are the ones that matter most — they prove the LLM's output can only
ever become safe, parameterized SQL.

---

## Deploying your own

See **[DEPLOY.md](DEPLOY.md)**. Render reads [`render.yaml`](render.yaml) as a Blueprint and
stands up both FastAPI services; Vercel deploys `apps/web` with `NEXT_PUBLIC_API_URL` pointed at
the CRM. CORS for `*.vercel.app` is already handled in `app/main.py`.

---

## Status

Live in production: the **agent loop** (real LLM, streamed), **campaigns**, **campaign detail**
(funnel · A/B variants · timeline), and **Insights** (channel ROI · calibration). The next
increment is wiring the live **send → receipt** loop end-to-end through the Channel Service;
today the converging calibration is demonstrated from seeded campaign events. The full design,
scalability plan (10k → 1M), and walkthrough script are in **[BLUEPRINT.md](BLUEPRINT.md)**.
