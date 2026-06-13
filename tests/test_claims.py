"""The screening engine catches each seeded typology and gets the dollar math right."""
from app.claims import provider_summary, screen
from conftest import inv


def rules(findings):
    return {f.rule.split(" ", 1)[0] for f in findings}


def test_clean_batch_no_findings(catalogue, cap):
    code, c = cap
    invoices = [inv(i, code, round(c * 0.9, 2)) for i in range(1, 6)]
    findings = screen(invoices, catalogue, {})
    assert findings == []


def test_price_cap_breach(catalogue, cap):
    code, c = cap
    f = screen([inv(1, code, round(c * 1.3, 2), qty=2)], catalogue, {})
    assert "R1" in rules(f)
    r1 = next(x for x in f if x.rule.startswith("R1"))
    # at risk = (price - cap) * qty
    assert abs(r1.at_risk - (round(c * 1.3, 2) - c) * 2) < 0.05


def test_invalid_item(catalogue, cap):
    f = screen([inv(1, "99_999_9999_9_9", 100, qty=1)], catalogue, {})
    assert "R2" in rules(f)
    assert next(x for x in f if x.rule.startswith("R2")).at_risk == 100


def test_duplicate(catalogue, cap):
    code, c = cap
    a = inv(1, code, round(c * 0.9, 2), qty=3, participant="P9")
    b = inv(2, code, round(c * 0.9, 2), qty=3, participant="P9")  # same participant/item/date/qty
    f = screen([a, b], catalogue, {})
    assert "R3" in rules(f)


def test_impossible_day(catalogue, cap):
    code, c = cap
    invoices = [inv(i, code, round(c * 0.9, 2), worker_id="W1", hours=9,
                    participant=f"P{i}") for i in range(1, 4)]  # 27h same worker/day
    f = screen(invoices, catalogue, {})
    assert "R4" in rules(f)


def test_expired_plan(catalogue, cap):
    code, c = cap
    f = screen([inv(1, code, round(c * 0.9, 2), plan_start="2024-01-01",
                    plan_end="2024-12-31")], catalogue, {})
    assert "R5" in rules(f)


def test_advance_claim(catalogue, cap):
    code, c = cap
    f = screen([inv(1, code, round(c * 0.9, 2), service_date="2026-08-15",
                    claim_date="2026-05-01")], catalogue, {})
    assert "R8" in rules(f)


def test_sanctioned_provider(catalogue, cap):
    code, c = cap
    sanctions = {"11111111111": "Banning Order effective 2026-01-01 (Bad Co)"}
    f = screen([inv(1, code, round(c * 0.9, 2))], catalogue, sanctions)
    assert "R7" in rules(f)


def test_provider_summary_groups_and_ranks(catalogue, cap):
    code, c = cap
    invoices = [
        inv(1, code, round(c * 1.5, 2), provider_name="A", qty=2),
        inv(2, "99_999_9999_9_9", 500, provider_name="B"),
    ]
    f = screen(invoices, catalogue, {})
    summ = provider_summary(f)
    assert summ[0]["at_risk"] >= summ[-1]["at_risk"]  # sorted desc
    assert {s["provider"] for s in summ} == {"A", "B"}
