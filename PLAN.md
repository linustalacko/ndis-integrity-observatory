# NDIS Fraud Intelligence — Research Findings & Build Plan

**Date:** 12 June 2026 · **Goal:** software that *shows* NDIS fraud, as the wedge into the provider-compliance product described in the opportunity brief.

---

## 1. Research findings

### 1.1 The fraud, quantified

- NDIA's own estimate: **6–10% of ~$42B in outlays is non-compliant, incorrect or fraudulent (~$2.5–4.2B/yr)**; ANAO Report 48 (2024–25) rated the agency's claim-compliance management "partly effective" and found the scheme ran for a decade **without basic prevention controls** (no robust identity verification or pre-payment validation until the "Crack Down on Fraud" program began Feb 2024).
- When the NDIA *does* review claims pre-payment, **over 50% by dollar value get cancelled** — the base rate of non-compliance in risk-targeted claims is staggering.
- Fraud Fusion Taskforce (16 agencies): **660 investigations underway, 59 people referred to court, ~200 banned, 2,500+ providers "disrupted"**. Recent ops: $3.5M single-provider fraud (Op Honeycomb), $1M+ phantom cleaning invoices across 13 participants' plans.
- Data-matching teaser from the Minister's office: of 900 plan-manager ABNs matched against ATO records, **343 would have failed a statement of tax record**. Nobody has built the public version of this kind of cross-reference.

### 1.2 The fraud typologies (NDIA's own list)

1. Ghost participants / illegitimate participant identities
2. Claiming against **expired plans**
3. Claiming for participants who are **in hospital, incarcerated, or overseas**
4. Claiming for services **outside the plan**
5. Claiming for services **never provided** (phantom billing — the dominant prosecuted type)
6. **Advance claiming** before delivery
7. **Overcharging / duplicate charging / overstating** services (price-limit breaches)
8. **Double-dipping** across government programs
9. Conflicted intermediaries (plan managers / support coordinators steering to related-party providers)
10. Phoenixing: banned operator reappears behind a new ABN/entity

### 1.3 The regulatory forcing function (why now)

- **Integrity and Safeguarding Act (passed April 2026)**: mandatory electronic claims, and a new NDIA power to **demand evidence before paying a claim** (expanded s45). Every provider in the country now needs claims-evidence discipline they don't have.
- **Securing the NDIS for Future Generations Bill 2026** (tabled): new civil penalties + expanded NDIA monitoring/investigation powers.
- Support at Home (aged care, from 1 Nov 2025) resets compliance for the whole aged-care sector — same motion, second market.

### 1.4 The data landscape (what's public, verified hands-on)

| Data | Source | Access | Verified |
|---|---|---|---|
| **Compliance & enforcement register** — 3,203 records: banning orders (760), compliance notices (2,015), revocations (330), refusals, suspensions; fields: Name, ABN, City/State/Postcode, action type, dates, **free-text reasons** | NDIS Commission via data.gov.au, dated CSV snapshots (≈fortnightly) | Free CSV | ✅ downloaded & profiled |
| ABN Bulk Extract — every ABN: legal name, entity type, status + dates, GST, location | data.gov.au (ABR) | Free bulk XML, weekly | endpoint confirmed |
| Registered provider register (Part 1) | NDIS Commission searchable register + Provider Finder | Scrape | search UI confirmed |
| NDIS Support Catalogue (every billable item + **price caps**) | ndis.gov.au | Free XLSX, versioned | confirmed |
| Quarterly report data: participants, payments by support category/region, plan-management uptake (65% of participants), market concentration | dataresearch.ndis.gov.au | Free CSV/XLSX (aggregate only) | confirmed |
| FFT/Commission media releases, court lists, ART decisions | various | Scrape | confirmed |
| **Provider-level payment data** | NDIA | **NOT public** (aggregates only) | confirmed |
| **Claims/invoice-level data** | NDIA portal, **plan managers** (65% of participants), participants (their own statements) | Private — this is the moat layer | n/a |

Key structural fact: **the only people outside government who see claims at scale are plan managers.** They are also legally on the hook (payment-integrity audits) and are private companies that buy software quickly.

### 1.5 Competitive scan

- Plan-management/claims software exists (Kismet, My Plan Manager, quickclaim, Entiprius, Caresquare) — invoice *processing* automation, with fraud mentioned in marketing but no evidence of a serious detection layer or any public intelligence product.
- Nobody — government included — publishes a provider risk graph, a phoenixing tracker, or a typology breakdown of the enforcement register. The Commission's own register is point-in-time snapshots with no analysis layer.

---

## 2. Product thesis

**"Show the fraud" with public data first; sell detection where the claims data lives second.**

The McIntyre lesson applies directly: a cold pitch ("we detect NDIS fraud") becomes warm when you can show a working artifact built from public data that nobody else has assembled. The artifact then doubles as the distribution engine (press, parliament, plan managers, the NDIA itself all want it).

### Phase 1 — The NDIS Provider Integrity Observatory (public data, build now)

A continuously-updated intelligence layer over every public signal:

1. **Enforcement time machine** — ingest *all* dated snapshots of the compliance register → a longitudinal database the Commission itself doesn't publish: time-to-ban after first notice, recidivism, geographic clustering, action velocity.
2. **Entity graph** — resolve people/companies across: enforcement register ↔ ABN extract ↔ registered-provider register ↔ court/media. Surfaces:
   - **Phoenix alerts**: banned person's name/address matches a newly-registered ABN or still-active provider (the registry's ABN field is only populated on 207/760 bans — name+location matching is the work, and the value).
   - Banned-while-registered: enforcement actions against entities still appearing on the provider register.
   - Cluster addresses: one suburb office tower hosting N enforcement actions.
3. **Typology engine** — LLM-classify the 3,203 free-text enforcement reasons into the NDIA's own typology list → the first public breakdown of *what kind* of fraud is being policed, by state, by quarter. (Same grounded-quote verification pattern as the DA copilot: every classification carries a verbatim quote.)
4. **Market anomaly monitor** — quarterly aggregates: provider-count surges by registration group/region vs participant growth; plan-management fee growth; concentration shifts.
5. **The weekly diff** — new bans/notices/revocations published as a feed (site + newsletter + API). Journalists, plan managers, and providers' compliance teams all subscribe. This is the audience engine.

**Demo moment:** load the graph, click a banned director, watch it light up two more active ABNs registered the month after the ban, with the registry text and ABR records side by side. Every edge cited to a government source.

### Phase 2 — Claims Integrity Engine (sold to plan managers, then providers)

The Observatory's "Provider Check" API (is this ABN banned / noticed / phoenix-risk / unregistered-for-this-support?) is the free hook into plan managers. The paid product screens every invoice **before it's claimed**:

- price-cap validation against the Support Catalogue (item × region × time)
- duplicate / overlap / impossible-day detection (one worker billing >24h, same support twice)
- plan-budget and plan-period checks (expired plans = typology #2)
- banned/risk-flagged provider screening (live from Phase 1)
- evidence-pack generation for the new s45 pre-payment evidence demands — the regulatory forcing function with an April 2026 date on it

The "ambient capture → compliant artifact" engine from the original brief plugs in here: progress notes captured at point of care become the claims evidence the NDIA now has the power to demand.

### Phase 3 — The evidence standard (the Flock pattern)

Once enough plan managers/providers run claims through the engine, the dataset of *verified* service delivery becomes what the NDIA rents: pre-validated claims with evidence attached clear faster than raw ones. Private network, government rents the output.

---

## 3. Build plan (milestones, acceptance-tested)

**M0 — Register time machine (1 day).** Ingest every compliance-actions snapshot from data.gov.au CKAN (112+ datasets) into SQLite; dedupe into entity-action records with first-seen/last-seen. *Accept: query any provider name → full enforcement history + which snapshot each fact came from.*

**M1 — ABN join + phoenix detector (2–3 days).** Load ABN Bulk Extract; exact + fuzzy (name, postcode) matching against enforcement entities; flag active ABNs linked to banned persons and post-ban registrations. *Accept: ≥1 documented phoenix case found and verified by hand against ABR + register text (this is the headline demo).*

**M2 — Typology engine + dashboards (2 days).** LLM classification of all free-text reasons with verbatim-quote verification; enforcement analytics (by type/state/quarter/registration group); market anomaly charts from quarterly data. *Accept: typology table where every row's quotes check out; 3 charts a journalist would screenshot.*

**M3 — The Observatory site + weekly diff (2–3 days).** Public site: searchable register-with-history, entity graph view, typology dashboard, weekly-diff feed + subscribe. Defamation-safe framing (verbatim register facts; inferences labelled "requires verification"). *Accept: a stranger can search any provider and understand its history in 30 seconds.*

**M4 — Claims engine prototype (1 week).** Support Catalogue price-cap validator + duplicate/expired-plan/impossible-day checks over a synthetic (or volunteered) invoice set; Provider Check API; one-page risk report per invoice batch. *Accept: seeded synthetic fraud (all 10 typologies) → engine catches every numeric/deterministic one with cited rules.*

Then: 5 plan-manager design-partner conversations, with the Observatory as the door-opener.

## 4. Risks

- **Defamation/PR**: publishing risk inferences about named businesses. Mitigate: verbatim register facts only on the public surface; inferences ("possible phoenix") framed as questions, gated, human-verified before publication.
- **Registry data quality**: ABN missing on 73% of banning orders → fuzzy matching false positives. Mitigate: confidence tiers, manual review queue for anything published.
- **No claims data until a plan manager signs**: Phase 2 detection quality unproven until then. Mitigate: synthetic eval harness + recruit one design partner early.
- **NDIA could build it**: PACE ($135M blowout) and ANAO findings suggest velocity advantage is real and durable.
