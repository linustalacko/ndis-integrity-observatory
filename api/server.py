"""JSON API over the NDIS integrity database. Thin wrapper around app/* logic.

Run: uv run uvicorn api.server:app --port 8000
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from fastapi import FastAPI, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.check import check as provider_check  # noqa: E402
from app.db import connect  # noqa: E402
from app.dossier import build as build_dossier  # noqa: E402

app = FastAPI(title="NDIS Integrity Observatory API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


def db():
    return connect(check_same_thread=False)


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


@app.get("/api/overview")
def overview():
    c = db()
    types = {r["type"]: r["c"] for r in c.execute(
        "SELECT type, COUNT(*) c FROM actions GROUP BY type")}
    snap = c.execute("SELECT MIN(snapshot_date) a, MAX(snapshot_date) b, "
                     "COUNT(*) n FROM snapshots").fetchone()
    phoenix_high = c.execute("SELECT COUNT(DISTINCT action_id) c FROM matches "
                             "WHERE post_ban_registration=1 AND tier='high'").fetchone()["c"]
    monthly = rows(c.execute(
        "SELECT substr(date_from,1,7) month, type, COUNT(*) n FROM actions "
        "WHERE date_from >= '2022-01' GROUP BY month, type ORDER BY month"))
    by_state = rows(c.execute(
        "SELECT state, COUNT(*) n FROM actions WHERE state != '' "
        "GROUP BY state ORDER BY n DESC"))
    hotspots = [
        {"location": f"{r['postcode']} {(r['city'] or '').title()}".strip(), "n": r["n"]}
        for r in c.execute(
            "SELECT postcode, MAX(city) city, COUNT(*) n FROM actions "
            "WHERE postcode != '' GROUP BY postcode ORDER BY n DESC LIMIT 12")]
    return {
        "totals": {
            "actions": sum(types.values()),
            "banning_orders": types.get("ER - Banning Order", 0),
            "compliance_notices": types.get("ER - Compliance notice", 0),
            "revocations": types.get("ER - Revocation of registration", 0),
            "phoenix_high": phoenix_high,
        },
        "snapshots": {"from": snap["a"], "to": snap["b"], "count": snap["n"]},
        "by_type": types, "monthly": monthly, "by_state": by_state,
        "hotspots": hotspots,
    }


@app.get("/api/register")
def register(q: str = Query(..., min_length=2)):
    c = db()
    res = rows(c.execute(
        "SELECT action_id, type, name, abn, city, state, postcode, date_from, "
        "date_to, first_seen, last_seen, detail FROM actions "
        "WHERE name LIKE ? OR abn LIKE ? ORDER BY date_from DESC LIMIT 100",
        (f"%{q}%", f"%{q}%")))
    return {"count": len(res), "actions": res}


@app.get("/api/phoenix")
def phoenix(tier: str = "high"):
    c = db()
    tiers = {"high": ("high",), "medium": ("high", "medium"),
             "all": ("high", "medium", "low")}.get(tier, ("high",))
    ph = ",".join("?" * len(tiers))
    res = rows(c.execute(f"""
        SELECT m.confidence, m.tier, a.name, a.type, a.date_from sanction_date,
               a.state act_state, m.abn, m.name_freq namesakes, m.geo,
               m.match_type, m.note
        FROM matches m JOIN actions a USING(action_id)
        WHERE m.post_ban_registration=1 AND m.tier IN ({ph})
        ORDER BY m.confidence DESC, a.date_from DESC""", tiers))
    counts = {r["tier"]: r["n"] for r in c.execute(
        "SELECT tier, COUNT(*) n FROM matches WHERE post_ban_registration=1 "
        "AND tier IS NOT NULL GROUP BY tier")}
    return {"counts": counts, "leads": res}


@app.get("/api/check")
def check(q: str = Query(..., min_length=2)):
    return provider_check(q)


@app.get("/api/dossier")
def dossier(name: str = Query(..., min_length=2)):
    c = db()
    return {"markdown": build_dossier(c, name)}


@app.get("/api/dossier-list")
def dossier_list():
    c = db()
    return {"leads": rows(c.execute("""
        SELECT DISTINCT a.name, m.confidence FROM matches m JOIN actions a USING(action_id)
        WHERE m.post_ban_registration=1 AND m.tier='high'
        ORDER BY m.confidence DESC"""))}


@app.get("/api/typologies")
def typologies():
    c = db()
    dist = rows(c.execute("""
        SELECT typology, COUNT(*) n FROM typologies WHERE quote_verified=1
        GROUP BY typology ORDER BY n DESC"""))
    n = c.execute("SELECT COUNT(*) c FROM typologies").fetchone()["c"]
    v = c.execute("SELECT COUNT(*) c FROM typologies WHERE quote_verified=1").fetchone()["c"]
    return {"classified": n, "verified": v, "distribution": dist}


@app.get("/api/typology-samples")
def typology_samples(typology: str):
    c = db()
    return {"samples": rows(c.execute("""
        SELECT a.name, a.type, a.date_from, t.quote FROM typologies t
        JOIN actions a USING(action_id)
        WHERE t.typology=? AND t.quote_verified=1 ORDER BY a.date_from DESC LIMIT 12""",
        (typology,)))}


@app.get("/api/snapshots")
def snapshots():
    c = db()
    return {"snapshots": [r["snapshot_date"] for r in
                          c.execute("SELECT snapshot_date FROM snapshots ORDER BY 1")]}


@app.get("/api/diff")
def diff(a: str, b: str):
    c = db()
    new = rows(c.execute(
        "SELECT type, name, state, date_from FROM actions WHERE first_seen > ? "
        "AND first_seen <= ? ORDER BY date_from DESC", (a, b)))
    gone = rows(c.execute(
        "SELECT type, name, state, date_from, last_seen FROM actions "
        "WHERE last_seen >= ? AND last_seen < ? ORDER BY last_seen DESC", (a, b)))
    return {"new": new, "gone": gone}


@app.get("/api/money")
def money():
    from app.money import summary
    return summary()


@app.get("/api/claims-demo")
def claims_demo():
    return _screen(ROOT / "data" / "synthetic_invoices.csv")


@app.post("/api/claims")
async def claims(file: UploadFile):
    content = await file.read()
    return _screen(io.BytesIO(content))


def _screen(src) -> dict:
    from app.claims import (catalogue_index, fetch_catalogue, load_invoices,
                            sanctioned_providers, screen)
    import pandas as pd
    invoices = load_invoices(src)
    cat = catalogue_index(fetch_catalogue())
    findings = screen(invoices, cat, sanctioned_providers(db()))
    df = pd.read_csv(src if not hasattr(src, "seek") else (src.seek(0) or src))
    return {
        "lines": len(invoices),
        "breaches": sum(1 for f in findings if f.severity == "breach"),
        "warnings": sum(1 for f in findings if f.severity == "warning"),
        "findings": [{"line": f.invoice_line, "rule": f.rule, "severity": f.severity,
                      "detail": f.detail, "citation": f.citation} for f in findings],
        "invoices": df.fillna("").astype(str).to_dict(orient="records"),
    }
