# NDIS Provider Integrity Observatory

**An open-source, crowd-sourced fraud finder for Australia's National Disability
Insurance Scheme — built entirely from public government data.**

The NDIS pays out ~$48B a year. The agency's own estimate is that **6–10% of
payments are non-compliant, incorrect or fraudulent** — roughly **$2.5–4.2B
annually** ([ANAO Report 48, 2024–25](https://www.anao.gov.au/work/performance-audit/ndia-management-of-claimant-compliance-with-ndis-claim-requirements)).
Yet the data that would expose it is scattered across a search-only enforcement
register, a 10 GB business-register dump, quarterly market spreadsheets and police
media releases. **Nobody had assembled it.** This does.

It does four things:

1. **See** — every enforcement action ever published, joined and analysed.
2. **Spot** — the operators, families and regions most likely to be running fraud.
3. **Screen** — invoice books (or a photo of an invoice) against the rules, live.
4. **Share** — anything flagged goes to a public registry everyone can see.

> **It points at where fraud is — it does not prove it.** Everything built from
> public data is a *lead to investigate*. Proof requires claims data. Read the
> [Ethics & limitations](#ethics--limitations) before using any of it.

---

## How it works

The system has two halves: **intelligence** (find leads from public data) and the
**claims engine** (catch fraud in actual invoices).

### 1. The enforcement register, as a dataset with memory

The NDIS Commission publishes its banning orders, revocations and compliance
notices as a *search box* — you can look up a name you already suspect, but you
can't analyse the whole thing, and it shows only today's state. The Commission
also quietly drops the full register as a CSV on data.gov.au every ~fortnight.

`app/ingest.py` ingests **every snapshot** into SQLite and dedupes them into a
single history with `first_seen`/`last_seen` dates. That gives you what the
official site can't: the full register as data, change-over-time, and **what was
silently removed** between snapshots (expiries, successful appeals, quiet
deletions). Today: **3,265 enforcement actions** across 7 snapshots.

### 2. "Banned & back" — the phoenix detector

The strongest forward-looking signal in public data: a person the regulator
**permanently banned** who then **registers a new active business**.

- `app/abr.py` streams the **ABN Bulk Extract** (every ABN in Australia, ~10 GB
  of XML) and keeps the rows that match an enforcement entity by name or ABN.
- `app/match.py` links sanctioned people to ABNs (exact-ABN, exact-name, fuzzy).
- `app/score.py` is the crucial part: a **confidence model** so common-name
  collisions don't drown the signal. It scores each link on **name rarity** (how
  many namesakes exist in the ABR), **geography** (same postcode > same state >
  interstate), and match type. "Muhammad Ali → 219 ABNs" scores near zero;
  "Krista Vegter, 1 namesake, same postcode, ABN activated 11 months after her
  ban" scores 99.

Result: ~300 raw matches collapse to **33 high-confidence leads**.

### 3. Entity networks — syndicate signatures

NDIS prosecutions repeatedly involve *networks*: one case used **50 ABNs** for
fake services; others run through families and associates. `app/rings.py` surfaces
the two network patterns visible in public data:

- **Multi-ABN operators** — one sanctioned person linked to several active ABNs
  (confidence-filtered, so it's real, not name noise).
- **Family / associate clusters** — two or more different people sharing a
  **surname and a postcode** where at least one is banned (e.g. two brothers both
  permanently banned at one address).

### 4. Region anomalies — where the numbers don't add up

`app/market_ingest.py` loads **7 quarters of NDIA active-provider counts and
market-concentration data**. `app/region_risk.py` scores every service district
on **provider-growth above the national rate**, **market fragmentation** (a
falling top-10 payment share — a swarm of new small providers is a ghost-provider
signature), and **spend per provider**. This is the same population-level
risk-scoring approach the NDIA itself uses internally.

### 5. What the conduct actually was — typologies

Banning orders mostly cite the *section*, not the *conduct*. `app/typology.py`
uses an LLM to classify each action's free text into a conduct typology, and only
counts a classification if its supporting quote appears **verbatim** in the
register text (a hallucination guard). 91% quote-verified across 3,264 actions.
The headline finding: most published bans **don't say what the person did**.

### 6. The dollar gap — fraud value

`app/money.py` extracts the **charged amounts** from Fraud Fusion Taskforce / AFP
media releases (NDIS-filtered) and sets them against the NDIA's systemic estimate.
The story is the gap: **less than 5% of one year's estimated leakage has ever been
charged.**

### 7. The claims engine — catching fraud in real invoices

This is the only part that detects *new* fraud rather than re-surfacing known
fraud. `app/claims.py` screens invoice lines against the **NDIS Support Catalogue
2025-26 price caps** and the NDIA's own fraud typologies, with a dollar-at-risk on
every finding:

| Rule | Catches |
|---|---|
| R1 | price-cap breach (rate above the catalogue limit for the item/state) |
| R2 | invalid support item (code not in the catalogue) |
| R3 | duplicate claim |
| R4 | impossible day (one worker billing >24h) |
| R5 | claim against an expired plan |
| R6 | weekend-loaded item delivered on a weekday |
| R7 | provider is on the enforcement register |
| R8 | advance claiming (service dated after the claim) |

### 8. Low-friction reporting — CSV or a photo

`app/extract_image.py` lets you **photograph an invoice**: a vision model reads
the line items into the same schema, then the identical engine screens them. CSV
upload works too. If anything is flagged, one tap submits it to the registry.

### 9. The crowd-sourced registry

`app/registry.py` is the shared database. A report is created **only when the
engine flags a breach** — you can't post a clean batch. Each entry is
provider-level and carries everything about the place: name, ABN, location,
services billed, $ billed, $ flagged, the rules tripped, and whether the provider
is already on the enforcement register.

---

## Data sources (all public)

| Data | Source | Format |
|---|---|---|
| Enforcement register (banning orders, revocations, notices) | NDIS Commission via [data.gov.au](https://data.gov.au/data/dataset) | CSV, ~fortnightly |
| Every ABN (names, status, location, ASIC no.) | [ABN Bulk Extract](https://data.gov.au/data/dataset/abn-bulk-extract) (ABR) | XML, weekly |
| Active providers & market concentration | [dataresearch.ndis.gov.au](https://dataresearch.ndis.gov.au/datasets/provider-datasets) | CSV, quarterly |
| Support item price caps | [NDIS Support Catalogue](https://www.ndis.gov.au/providers/pricing-and-payments) | XLSX |
| Prosecutions / charged amounts | AFP / Fraud Fusion Taskforce media releases | scraped |

---

## Ethics & limitations

Please read this before relying on anything here.

- **Leads, not allegations.** Phoenix links, family clusters and region scores are
  *statistical signals* derived from public data. A shared surname can be
  coincidence; a fast-growing region can be legitimate demand; a name can collide.
  Every such view is labelled "verify independently" and must be treated that way.
- **It does not prove fraud.** The only component that detects actual fraudulent
  billing is the claims engine, and only on real invoice data you provide.
- **Real people are named** because the source register names them. Republishing
  and cross-referencing public data amplifies it; that is a deliberate transparency
  trade-off, but it carries defamation and privacy responsibilities. Do not present
  a lead as a finding.
- **The data is a snapshot.** Registrations, sanctions and prices change; always
  check the live source before acting.
- **Charged amounts** are *alleged/charged* figures from press releases, not
  court-proven totals, and reflect only what the AFP has publicised.

This project exists to make oversight of public money possible, in the open. Use
it to ask better questions, not to accuse.

---

## Run it

```bash
# dev: API on :8000, SvelteKit on :5173
./run.sh

# tests
uv run python -m pytest tests/ -q

# production / single-service: API serves the built SPA on one port
cd frontend && npm run build && cd ..
uv run uvicorn api.server:app --port 8000   # → http://localhost:8000
```

LLM features (typology classification, invoice-photo extraction) need an
[OpenRouter](https://openrouter.ai) key in a `.env` file:
`OPENROUTER_API_KEY=sk-or-...`. Everything else runs without it.

## Deploy (one URL to share)

Ships as a single Docker image (builds the SPA, serves it + the API) with a
prebuilt 8.7 MB database, plus a `render.yaml` blueprint.

1. On [Render](https://render.com): **New → Blueprint**, select this repo.
2. Set `OPENROUTER_API_KEY` in the service's Environment tab (for image upload).
3. Deploy. Render returns a public URL.

The database is baked into the image; Render's disk is ephemeral, so live registry
submissions reset on redeploy (add a persistent disk at `/app/data` to keep them).

## Architecture

```
app/        Python intelligence + engine (one module per capability)
api/        FastAPI JSON layer; also serves the built SPA in production
frontend/   SvelteKit 5 (runes), monochrome design system
data/       prebuilt ndis.db, Support Catalogue, synthetic invoice batch
tests/      pytest: engine typologies, dollar math, gating, registry, signals
```

Rebuild the database from source data with the commands in
[`PLAN-FRAUD.md`](PLAN-FRAUD.md); the committed DB is enough to run everything.

## Contributing

Issues and PRs welcome — especially: postcode→service-district mapping to combine
region risk with enforcement density; additional councils/snapshots; tighter
identity resolution (ASIC director data) to turn name-links into confirmed
networks; and more claims-engine rules. Keep the honesty guardrails intact.

## License

MIT — see [LICENSE](LICENSE). Built with public data; not affiliated with the NDIA
or the NDIS Quality and Safeguards Commission.
