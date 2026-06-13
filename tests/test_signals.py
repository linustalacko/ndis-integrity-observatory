"""Signal modules return sane shapes on the live DB (skips if not ingested)."""
import pytest

from app.db import connect


@pytest.fixture(scope="module")
def conn():
    return connect(check_same_thread=False)


def test_region_risk_shape(conn):
    if not conn.execute("SELECT 1 FROM provider_counts LIMIT 1").fetchone():
        pytest.skip("market data not ingested")
    from app.region_risk import compute
    rows = compute(conn)
    assert rows, "expected scored districts"
    top = rows[0]
    assert top["risk"] >= rows[-1]["risk"]          # sorted desc
    assert "Other" not in {r["district"] for r in rows}  # catch-all excluded
    for r in rows:
        assert 0 <= r["risk"] <= 100


def test_rings_multi_abn_filtered(conn):
    if not conn.execute("SELECT 1 FROM matches WHERE tier IS NOT NULL LIMIT 1").fetchone():
        pytest.skip("matches not scored")
    from app.rings import multi_abn_operators
    ops = multi_abn_operators(conn, 3)
    # tier filter must exclude the common-name mega-collisions (no 100+ ABN entries)
    assert all(o["n_abns"] < 50 for o in ops)


def test_family_clusters_distinct_people(conn):
    if not conn.execute("SELECT 1 FROM actions LIMIT 1").fetchone():
        pytest.skip("no actions")
    from app.rings import family_clusters
    fam = family_clusters(conn)
    for c in fam:
        assert c["n_people"] >= 2
        assert c["n_sanctioned"] >= 1
        assert len(c["people"]) == len(set(c["people"]))  # deduped
