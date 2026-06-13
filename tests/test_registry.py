"""Registry gating + persistence: only flagged providers are recorded; clean is rejected."""
from app.claims import screen
from app.registry import build_reports, listing, submit
from conftest import inv


def test_clean_batch_yields_no_reports(catalogue, cap):
    code, c = cap
    invoices = [inv(i, code, round(c * 0.9, 2)) for i in range(1, 5)]
    findings = screen(invoices, catalogue, {})
    reports = build_reports(invoices, findings, {})
    assert reports == []


def test_fraud_batch_yields_provider_report(catalogue, cap):
    code, c = cap
    invoices = [
        inv(1, code, round(c * 1.4, 2), provider_name="Dodgy Co", qty=2),
        inv(2, code, round(c * 0.9, 2), provider_name="Clean Co"),
    ]
    findings = screen(invoices, catalogue, {})
    reports = build_reports(invoices, findings, {})
    provs = {r["provider_name"] for r in reports}
    assert "Dodgy Co" in provs          # flagged
    assert "Clean Co" not in provs       # not flagged -> not reported
    r = reports[0]
    assert r["at_risk"] > 0
    assert "R1" in r["rules"]
    assert r["services"] != ""


def test_submit_and_list(catalogue, cap, mem_db):
    code, c = cap
    invoices = [inv(1, code, round(c * 1.4, 2), provider_name="Dodgy Co", qty=2)]
    findings = screen(invoices, catalogue, {})
    reports = build_reports(invoices, findings, {})
    n = submit(mem_db, reports)
    assert n == 1
    out = listing(mem_db)
    assert out["count"] == 1
    assert out["total_at_risk"] > 0
    assert out["reports"][0]["provider_name"] == "Dodgy Co"


def test_sanctioned_flag_carried(catalogue, cap, mem_db):
    code, c = cap
    sanctions = {"11111111111": "Banning Order effective 2026-01-01 (Bad Co)"}
    invoices = [inv(1, code, round(c * 1.4, 2), provider_name="Bad Co", qty=2)]
    findings = screen(invoices, catalogue, sanctions)
    reports = build_reports(invoices, findings, sanctions)
    submit(mem_db, reports)
    assert listing(mem_db)["sanctioned"] == 1
