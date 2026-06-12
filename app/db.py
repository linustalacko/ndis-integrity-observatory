"""SQLite schema and connection for the NDIS integrity database."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ndis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_date TEXT PRIMARY KEY,      -- ISO date parsed from dataset title
    dataset_title TEXT,
    url TEXT,
    record_count INTEGER,
    ingested_at TEXT DEFAULT (datetime('now'))
);

-- One row per unique enforcement action (deduped across snapshots).
CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,          -- sha1 of type|name|date_from
    type TEXT NOT NULL,                  -- banning order / compliance notice / ...
    name TEXT NOT NULL,
    abn TEXT,
    city TEXT, state TEXT, postcode TEXT,
    provider_number TEXT,
    date_from TEXT,                      -- date effective from
    date_to TEXT,                        -- date no longer in force ('' = still in force)
    registration_groups TEXT,
    detail TEXT,                         -- free-text 'Relevant information'
    first_seen TEXT NOT NULL,            -- earliest snapshot containing it
    last_seen TEXT NOT NULL,             -- latest snapshot containing it
    is_person INTEGER,                   -- heuristic: individual vs organisation
    norm_name TEXT                       -- normalised name for matching
);

CREATE INDEX IF NOT EXISTS idx_actions_name ON actions(norm_name);
CREATE INDEX IF NOT EXISTS idx_actions_abn ON actions(abn);
CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(type);

-- Slim ABR subset: only rows that could match an enforcement entity, plus
-- all entities whose ABN appears in the register.
CREATE TABLE IF NOT EXISTS abns (
    abn TEXT PRIMARY KEY,
    legal_name TEXT,
    entity_type TEXT,
    abn_status TEXT,
    status_date TEXT,                    -- ABN status from date
    gst_status TEXT,
    state TEXT, postcode TEXT,
    norm_name TEXT
);
CREATE INDEX IF NOT EXISTS idx_abns_norm ON abns(norm_name);

-- Phoenix / linkage candidates between an enforcement entity and an ABN.
CREATE TABLE IF NOT EXISTS matches (
    action_id TEXT,
    abn TEXT,
    match_type TEXT,                     -- exact-abn | exact-name | fuzzy-name
    score REAL,
    post_ban_registration INTEGER,       -- ABN active/started after ban date
    note TEXT,
    PRIMARY KEY (action_id, abn)
);

-- LLM typology classification of action free text.
CREATE TABLE IF NOT EXISTS typologies (
    action_id TEXT PRIMARY KEY,
    typology TEXT,
    section_cited TEXT,
    duration TEXT,                       -- permanent | years | n/a
    quote TEXT,
    quote_verified INTEGER,
    model TEXT,
    classified_at TEXT DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass  # another writer holds the lock; busy_timeout still applies
    conn.execute("PRAGMA busy_timeout=60000")
    conn.executescript(SCHEMA)
    return conn
