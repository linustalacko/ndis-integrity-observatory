# Crowd-sourced fraud registry — design

## Reduce before adding (the nav today has 10 tabs)

A user of a crowd-sourced fraud finder needs four things, in this order:
1. **See** the shared fraud everyone has found  → Registry
2. **Contribute** what they've found             → Report
3. **Check** a provider before dealing with them → Provider check
4. **Understand** the wider picture              → Overview / Signals

Everything else (Banned & back, Case dossiers, Register, Register diff,
Typologies, Fraud value) is *analyst* tooling — valuable but secondary, and
mostly overlapping ("explore the enforcement data"). Showing all ten flattens
the hierarchy and hides the product.

**Decision:** two groups in the sidebar.
- **Find fraud** (the product): Registry, Report fraud, Provider check
- **Intelligence** (investigate): Overview, Fraud signals, Banned & back, Register

Demoted from nav (routes kept, reachable contextually): Fraud value (folded into
Overview), Case dossiers (opened from Banned & back), Register diff + Typologies
(folded into Register later). Net: 10 → 7 visible, product foregrounded.

## The registry

A shared table of provider-level fraud reports. A report is created ONLY when the
screening engine flags a breach — you cannot post a clean batch. One submission
yields one entry per flagged provider, carrying everything about the place:

- provider name + ABN
- location (state, postcode, city if known)
- services (the support-item categories billed)
- $ billed, $ flagged at risk, % 
- the rules tripped (R1..R8) and the specific findings
- source (csv | image), reported timestamp
- register cross-check: is this provider already sanctioned?

Honesty: entries are user-submitted and rule-flagged, **unverified**. Names appear
because the data names them; framing is "reported, flagged by automated rules,
verify independently." Same guardrail as everywhere else.

## Low-friction upload

- **CSV** — the existing path.
- **Image** (invoice photo/screenshot/PDF page) — a vision model extracts the
  line items into the same Invoice schema, then the identical engine screens them.
  Drag-drop or pick; auto-detect type; no field mapping asked of the user.

## Tests (prove it works)

`tests/` with pytest:
- engine catches each seeded typology, dollar math correct
- gating: clean batch → cannot report; fraud batch → can
- registry: submit persists; provider/location/services correct; clean rejected
- signals: region/ring math returns sane shapes
- image: extraction mocked (no network in CI), schema mapping verified
