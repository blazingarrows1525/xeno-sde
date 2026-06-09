# Kairos — AI-Native Mini CRM

> An autonomous-but-supervised growth marketer. Give it a goal in plain language; it analyses
> your shoppers, builds an audience, recommends a channel, drafts the message, **predicts the
> outcome**, and — after you approve — runs the campaign through a stubbed channel service and
> **learns** from the events that come back.

Built for the Xeno Engineering Take-Home (2026). Full design in **[BLUEPRINT.md](BLUEPRINT.md)**.

## Monorepo layout

```
apps/
  crm/        FastAPI — CRM core (ingestion, segments, campaigns, agent, analytics)
  channel/    FastAPI — stubbed Channel Service (lifecycle simulation + callbacks)   [coming]
  web/        Next.js 14 — UI (agent console, campaign detail, insights)             [coming]
scripts/      seed data generator                                                    [coming]
```

## The thing to read first

`apps/crm/app/segments/` — the **Segment DSL** and its **compiler**. The LLM never writes SQL;
it emits a typed, validated DSL document that this module compiles to *parameterized* SQL.
Injection-safe by construction, fully unit-tested.

## Run the CRM tests (Windows / PowerShell)

```powershell
cd apps/crm
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Run the CRM API locally

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/health
# → http://localhost:8000/docs   (OpenAPI; try POST /v1/segments/preview)
```
