# How to actually find NDIS fraud — research + plan

## What the research says (sources below)

- **Scale:** ~$2B+/yr (≈5–10% of outlays) lost to fraud/error; NDIA's own figure.
- **How the NDIA itself detects it:** data-matching + "fraud control data analytics
  profiles" that **assign risk scores to providers and flag high-risk claims**
  (ANAO, *NDIS Fraud Control Program*). This is population-level anomaly detection,
  not case-by-case.
- **The dominant network signature:** one investigated provider used **50 ABNs**
  to bill fake services; syndicates run through **multiple companies / shared
  bank accounts / shared addresses**. Fraud rings are an *entity-graph* problem.
- **The behavioural signatures** (red-flag literature): billing > hours delivered,
  group billed as 1:1, weekend up-rating, dual rates, **incentive/referral payments**
  (strong fraud correlate), ghost participants, claims on expired plans.
- **The hard truth:** the conduct-level proof lives in *claims data*, which is
  private. Everything findable from public data is **risk triage** — pointing an
  investigator at the regions, entities and rings most likely to harbour fraud.

So "find fraud" splits into three honest layers:

| Layer | What it finds | Data | Proof level |
|---|---|---|---|
| **A. Population anomalies** | regions/segments where the numbers don't add up | NDIA active-providers + market $ (public, quarterly) | risk signal |
| **B. Entity networks** | rings: many ABNs at one address, shared directors/names, phoenix | ABR + register (public) | strong lead |
| **C. Claims screening** | actual fraudulent invoices | plan-manager claims (private) | proof |

We already have C (Claims lab) and part of B (phoenix). This plan builds **A in
full, B properly, and a combined risk score** — the closest a public-data tool
gets to "here is where fraud is."

## The signals we will compute

**A. Region / market anomalies** (new data: 8 quarters of NDIA provider + payment)
1. **Provider-growth outliers** — service districts where active-provider count is
   growing far faster than the national rate. Ghost/phoenix provider farms show up
   as provider counts rising without matching demand.
2. **Spend-per-provider divergence** — districts where $ payment per provider is an
   outlier (very high = possible over-billing concentration; collapsing = churn/
   fragmentation).
3. **Concentration fragmentation** — falling top-10 payment share = a swarm of new
   small providers entering, a known phoenix/ghost pattern.
4. **Enforcement density** — sanctions per active provider, by state — where the
   regulator is already finding the most.

**B. Entity-network detection** (ABR data we hold)
5. **Shared-address rings** — addresses hosting many distinct ABNs linked to
   sanctioned/known entities (the "50 ABNs" signature).
6. **Shared-name / trading-name clusters** and **phoenix** (have).

**C. Combined risk score** — per region and per entity, blend the signals into one
ranked view: *where to look first.*

## Build steps

1. `market_ingest.py` — load provider counts (district × quarter) + payment bands +
   concentration into SQLite.
2. `region_risk.py` — compute signals 1–4, composite region score, time series.
3. `rings.py` — signal 5: cluster held ABR entities by address; rank multi-ABN
   addresses; pull the entities + their sanction status per cluster.
4. API endpoints + a **Fraud signals** page: region risk table/map, ring explorer,
   combined "highest-risk" leaderboard. Honest labelling throughout: *risk signal,
   not proof.*

## Honesty guardrails

- A growth outlier is not fraud; it can be legitimate demand. Label as "investigate".
- A shared address can be a serviced-office or accountant. Rings are leads to verify.
- The only "fraud found" claim the tool makes is in the Claims lab, on real invoices.

## Sources
- ANAO, *National Disability Insurance Scheme Fraud Control Program*.
- ANAO Report 48 (2024–25), claimant compliance.
- NDIA Fraud Fusion Taskforce / AFP releases (50-ABN case, syndicates).
- NDIS red-flag guidance (billing > hours, referral payments, ghosting).
- NDIA dataresearch: Active providers (quarterly), Market concentration.
