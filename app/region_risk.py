"""Region risk model — population-level fraud-risk signals by service district.

For each district (ALL support class), over the available quarters:
  growth     provider-count growth vs the national rate (ghost-provider farms
             grow provider numbers faster than genuine demand)
  frag       fall in the top-10 payment share (a swarm of new small providers —
             a phoenix / ghost signature)
  spend_pp   $ payment per provider relative to the national median (extreme
             highs concentrate billing; collapses signal churn)
  enf        enforcement actions per active provider (state-level), where the
             regulator is already finding the most

These are RISK SIGNALS, not proof. A growth outlier can be legitimate demand.

CLI: python -m app.region_risk
"""
from __future__ import annotations

from .db import connect


def _mid(lo, hi):
    if lo and hi:
        return (lo + hi) / 2
    return lo or hi or None


def compute(conn) -> list[dict]:
    quarters = [r["quarter"] for r in conn.execute(
        "SELECT DISTINCT quarter FROM provider_counts ORDER BY 1")]
    if len(quarters) < 2:
        return []
    first, last = quarters[0], quarters[-1]

    # national growth baseline
    nat = {q: r for q in quarters for r in [conn.execute(
        "SELECT provider_count c FROM provider_counts WHERE quarter=? AND state='ALL' "
        "AND district='ALL' AND support_class='ALL'", (q,)).fetchone()] if r}
    nat_growth = (nat[last]["c"] / nat[first]["c"] - 1) if nat.get(first) and nat.get(last) else 0

    # state-level enforcement density
    enf = {r["state"]: r["c"] for r in conn.execute(
        "SELECT state, COUNT(*) c FROM actions WHERE state != '' GROUP BY state")}
    state_prov = {r["state"]: r["provider_count"] for r in conn.execute(
        "SELECT state, provider_count FROM provider_counts WHERE district='ALL' "
        "AND support_class='ALL' AND quarter=?", (last,))}

    # real districts only — exclude catch-all / missing buckets and state rollups
    rows = []
    for r in conn.execute(
            "SELECT DISTINCT state, district FROM provider_counts "
            "WHERE district != 'ALL' AND district != 'Other' "
            "AND district NOT LIKE '%Missing%' AND support_class='ALL' "
            "AND state NOT IN ('ALL','OT','State_Missing')"):
        state, dist = r["state"], r["district"]
        c0 = conn.execute("SELECT provider_count c FROM provider_counts WHERE quarter=? "
                          "AND state=? AND district=? AND support_class='ALL'",
                          (first, state, dist)).fetchone()
        c1 = conn.execute("SELECT provider_count c FROM provider_counts WHERE quarter=? "
                          "AND state=? AND district=? AND support_class='ALL'",
                          (last, state, dist)).fetchone()
        if not c0 or not c1 or not c0["c"]:
            continue
        growth = c1["c"] / c0["c"] - 1
        excess = growth - nat_growth  # growth above national

        sh0 = conn.execute("SELECT top10_share s FROM market_concentration WHERE quarter=? "
                           "AND state=? AND district=? AND support_class='ALL'",
                           (first, state, dist)).fetchone()
        sh1 = conn.execute("SELECT top10_share s FROM market_concentration WHERE quarter=? "
                           "AND state=? AND district=? AND support_class='ALL'",
                           (last, state, dist)).fetchone()
        frag = (sh0["s"] - sh1["s"]) if sh0 and sh1 and sh0["s"] and sh1["s"] else None

        pay = conn.execute("SELECT payment_low lo, payment_high hi FROM market_concentration "
                           "WHERE quarter=? AND state=? AND district=? AND support_class='ALL'",
                           (last, state, dist)).fetchone()
        spend = _mid(pay["lo"], pay["hi"]) if pay else None
        spend_pp = (spend / c1["c"]) if spend and c1["c"] else None

        rows.append({
            "state": state, "district": dist,
            "providers_first": c0["c"], "providers_last": c1["c"],
            "growth": round(growth, 3), "excess_growth": round(excess, 3),
            "frag": round(frag, 3) if frag is not None else None,
            "spend": spend, "spend_per_provider": round(spend_pp) if spend_pp else None,
        })

    # normalise signals into 0..1 and build composite
    def vals(key):
        return [r[key] for r in rows if r.get(key) is not None]
    g = vals("excess_growth")
    gmax = max(g) if g else 1
    fr = vals("frag")
    frmax = max([x for x in fr if x > 0] or [1])
    sp = vals("spend_per_provider")
    spmax = max(sp) if sp else 1

    for r in rows:
        s_growth = max(0, r["excess_growth"]) / gmax if gmax else 0
        s_frag = (max(0, r["frag"]) / frmax) if r.get("frag") is not None and frmax else 0
        s_spend = (r["spend_per_provider"] / spmax) if r.get("spend_per_provider") and spmax else 0
        dens = (enf.get(r["state"], 0) / state_prov[r["state"]]) if state_prov.get(r["state"]) else 0
        r["enf_density"] = round(dens, 3)
        # weighted composite (growth and fragmentation are the strongest signals)
        r["risk"] = round(100 * (0.45 * s_growth + 0.30 * s_frag + 0.15 * s_spend
                                 + 0.10 * min(1, dens * 5)), 1)
    return sorted(rows, key=lambda r: -r["risk"])


def main() -> int:
    conn = connect()
    rows = compute(conn)
    print(f"{len(rows)} districts scored. Top 15 by risk:\n")
    print(f"{'risk':>5}  {'growth':>7} {'excess':>7} {'frag':>6}  {'$/prov':>9}  district")
    for r in rows[:15]:
        print(f"{r['risk']:5.1f}  {r['growth']*100:6.0f}% {r['excess_growth']*100:6.0f}% "
              f"{(r['frag'] or 0)*100:5.0f}%  "
              f"{('$'+format(r['spend_per_provider'],',')) if r['spend_per_provider'] else '—':>9}  "
              f"{r['state']} · {r['district']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
