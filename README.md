# NDIS Provider Integrity Observatory

A crowd-sourced NDIS fraud finder built on public data. Screen invoices (CSV or a
photo) against the price caps, fraud rules and the live enforcement register;
report anything flagged to a shared registry; and explore the population-level
and entity-network signals that point to where fraud is most likely.

Every figure links to its source. Inferences are leads for verification, not
allegations. Proof of fraud requires claims data — that's the Claims/Report path.

## Run locally

Two processes in dev (API on :8000, SvelteKit on :5173):

```bash
./run.sh
# API:      http://localhost:8000
# Frontend: http://localhost:5173
```

Single-service mode (what production runs — API serves the built SPA on one port):

```bash
cd frontend && npm run build && cd ..
uv run uvicorn api.server:app --port 8000
# everything on http://localhost:8000
```

Tests:

```bash
uv run python -m pytest tests/ -q
```

## Deploy to Render (one URL to share)

The repo ships a single-service Docker image (builds the SPA, serves it + the API)
and a prebuilt, pruned database (`data/ndis.db`, 8.7 MB).

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, point at the repo. It reads `render.yaml`
   and creates one Docker web service.
3. Set the env var **`OPENROUTER_API_KEY`** (Environment tab) to enable
   image-upload fraud detection. (Everything else works without it.)
4. Deploy. Render gives you a public URL; send it to anyone.

Notes:
- The registry/database is in the image. Render's disk is ephemeral, so reports
  submitted live reset on each redeploy (fine for a demo; add a Render persistent
  disk mounted at `/app/data` if you need them to persist).
- Health check: `/api/overview`.

## What's inside

| Area | Module | What it does |
|---|---|---|
| Register time machine | `app/ingest.py` | every NDIS Commission enforcement snapshot, deduped with history |
| Phoenix / banned-and-back | `app/abr.py`, `app/match.py`, `app/score.py` | ABR join + confidence-scored post-sanction ABNs |
| Typologies | `app/typology.py` | LLM conduct classification, quote-verified |
| Fraud value | `app/money.py` | charged amounts from AFP releases vs the NDIA estimate |
| Fraud signals | `app/region_risk.py`, `app/rings.py` | region growth/fragmentation anomalies + multi-ABN / family networks |
| Claims engine | `app/claims.py` | 8 deterministic rules + $-at-risk, vs Support Catalogue caps + register |
| Image extraction | `app/extract_image.py` | vision model reads an invoice photo into the engine |
| Registry | `app/registry.py` | crowd-sourced, gated on detection |
| API | `api/server.py` | JSON endpoints + serves the SPA |
| UI | `frontend/` | SvelteKit 5, monochrome design |

## Rebuilding the database from scratch

The committed DB is enough to run everything. To rebuild from source data:

```bash
uv run python -m app.ingest            # enforcement snapshots
# download ABR bulk extract into data/abr/ (≈1GB), then:
uv run python -m app.abr               # ABR subset
uv run python -m app.match             # phoenix matches + scores
uv run python -m app.typology          # LLM typologies (needs OPENROUTER_API_KEY)
uv run python -m app.market_ingest     # provider/market data into data/market/
uv run python -m app.enrich            # AFP media releases
uv run python -m app.rings             # entity networks
```
