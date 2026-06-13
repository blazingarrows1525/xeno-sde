# Kairos — Web

The Next.js front end for **Kairos**, an AI-native CRM. It renders the glass-box **agent console**
(live reasoning over SSE), **campaigns**, **campaign detail**, **insights/calibration**, and the OAuth /
demo **login gate**.

> Part of a monorepo. For the full picture see the [root README](../../README.md) and
> [BLUEPRINT.md](../../BLUEPRINT.md). The backend lives in [`../crm`](../crm) and [`../channel`](../channel).

## Stack

| | |
|---|---|
| Framework | Next.js 16 (App Router), React 19, TypeScript 5 |
| Styling / motion | Tailwind CSS v4 + a small custom CSS spring system |
| Data | TanStack Query 5 (server state), Recharts 3 (funnel & calibration charts) |
| Auth | HMAC-signed cookie sessions (Web Crypto — runs in Edge + Node) + Google / GitHub OAuth + one-tap demo |

## Run locally

```bash
npm install
# .env.local → NEXT_PUBLIC_API_URL=http://127.0.0.1:8000   (unset → the UI serves bundled mock data)
npm run dev          # http://localhost:3000
```

The app talks to the CRM API at `NEXT_PUBLIC_API_URL`. Start that first (see [`../crm`](../crm)); without
it, the UI falls back to bundled mock data so it still renders.

| Variable | Required | Purpose |
|----------|:--------:|---------|
| `NEXT_PUBLIC_API_URL` | recommended | CRM base URL; unset → bundled mock data |
| `NEXT_PUBLIC_BASE_URL` | prod | This app's public URL (used to build OAuth callbacks) |
| `AUTH_SECRET` | prod | Signs the session cookie (any long random string) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | optional | Lights up the Google button |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | optional | Lights up the GitHub button |

## Structure

```
app/          App-Router routes (console, campaigns/[id], insights) + /api/auth handlers
components/    design system, charts, reasoning trace, app shell
lib/           typed API client · auth (HMAC cookie) · types · mock fallback
```

## Scripts

| Command | Does |
|---------|------|
| `npm run dev` | Start the dev server (Turbopack) |
| `npm run build` | Production build — **don't run while `dev` is live** (shared `.next` cache can corrupt) |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint |
