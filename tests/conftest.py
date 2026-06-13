import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.claims import Invoice, catalogue_index, fetch_catalogue  # noqa: E402
from app.db import SCHEMA  # noqa: E402


@pytest.fixture(scope="session")
def catalogue():
    return catalogue_index(fetch_catalogue())


@pytest.fixture(scope="session")
def cap(catalogue):
    """A real item code + its NSW cap for building test invoices."""
    for code, v in catalogue.items():
        c = v["caps"].get("NSW")
        if c and 20 < c < 400:
            return code, c
    raise RuntimeError("no priced item found")


@pytest.fixture
def mem_db():
    """Isolated in-memory DB with the full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def inv(line, code, price, cap_state="NSW", **kw):
    base = dict(line=line, participant=f"P{line}", provider_name="Test Co",
                provider_abn="11111111111", item_code=code, service_date="2026-05-04",
                claim_date="2026-05-06", qty=1, unit_price=price, state=cap_state,
                plan_start="2026-01-01", plan_end="2026-12-31", worker_id="", hours=0)
    base.update(kw)
    return Invoice(**base)
