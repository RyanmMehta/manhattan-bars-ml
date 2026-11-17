"""Data contract for data/live_sim.db (CONTRACTS v1 schemas + v2 §B/§D/§E)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from tests.contract import schemas
from tests.contract.constants import DEMO_NOW, GENRES, SIM_FIRST_NIGHT, SIM_LAST_NIGHT, SIM_NIGHTS

ALL_TABLES = {**schemas.APP_TABLES, **schemas.EVAL_ONLY_TABLES}


def cols(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


@pytest.mark.parametrize("table", sorted(ALL_TABLES))
def test_table_has_contract_columns(live_db, table):
    have = cols(live_db, table)
    assert have, f"{table} missing from live_sim.db"
    missing = ALL_TABLES[table] - have
    assert not missing, f"{table} missing columns {sorted(missing)}"


@pytest.mark.parametrize("table", sorted(ALL_TABLES))
def test_all_rows_synthetic(live_db, table):
    n_bad = live_db.execute(f"SELECT COUNT(*) FROM {table} WHERE is_synthetic IS NOT 1").fetchone()[0]
    assert n_bad == 0


@pytest.mark.parametrize("table,pk", sorted(schemas.PRIMARY_KEYS.items()))
def test_primary_keys_prefixed_and_unique(live_db, table, pk):
    bad = live_db.execute(f"SELECT COUNT(*) FROM {table} WHERE {pk} NOT LIKE 'syn-%'").fetchone()[0]
    assert bad == 0, f"{table}.{pk} has {bad} ids without syn- prefix"
    dup = live_db.execute(f"SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {table}").fetchone()[0]
    assert dup == 0


@pytest.mark.parametrize("table", [t for t, c in ALL_TABLES.items() if "venue_id" in c])
def test_venue_ids_are_launch_venues(live_db, launch_ids, table):
    ids = {r[0] for r in live_db.execute(f"SELECT DISTINCT venue_id FROM {table} WHERE venue_id IS NOT NULL")}
    assert ids <= launch_ids, f"{table} has unknown venue_ids {sorted(ids - launch_ids)[:5]}"


def test_venue_attributes_cover_all_launch_venues(live_db, launch_ids):
    ids = {r[0] for r in live_db.execute("SELECT venue_id FROM syn_venue_attributes")}
    assert ids == launch_ids


def test_report_ranges(live_db):
    q = lambda sql: live_db.execute(sql).fetchone()[0]  # noqa: E731
    assert q("SELECT COUNT(*) FROM syn_scout_reports WHERE crowd NOT BETWEEN 1 AND 5") == 0
    assert q("SELECT COUNT(*) FROM syn_scout_reports WHERE dancing NOT IN (0,1,2)") == 0
    assert q("SELECT COUNT(*) FROM syn_scout_reports WHERE line_minutes < 0") == 0
    assert q("SELECT COUNT(*) FROM syn_scout_reports WHERE verified_presence NOT IN (0,1)") == 0
    status = {r[0] for r in live_db.execute("SELECT DISTINCT status FROM syn_scout_reports")}
    assert status <= schemas.REPORT_STATUS
    orphans = q("SELECT COUNT(*) FROM syn_scout_reports r LEFT JOIN syn_scouts s USING(scout_id) WHERE s.scout_id IS NULL")
    assert orphans == 0


def test_scout_and_attribute_ranges(live_db):
    q = lambda sql: live_db.execute(sql).fetchone()[0]  # noqa: E731
    assert q("SELECT COUNT(*) FROM syn_scouts WHERE reputation < 0 OR reputation > 1") == 0
    assert q("SELECT COUNT(*) FROM syn_venue_attributes WHERE price_level NOT BETWEEN 1 AND 4") == 0
    styles = {r[0] for r in live_db.execute("SELECT DISTINCT style FROM syn_venue_attributes")}
    assert styles <= schemas.STYLES
    events = {r[0] for r in live_db.execute("SELECT DISTINCT event_type FROM syn_venue_events")}
    assert events <= schemas.EVENT_TYPES
    arche = {r[0] for r in live_db.execute("SELECT DISTINCT archetype FROM syn_scout_truth")}
    assert arche <= schemas.ARCHETYPES


def test_genres_in_vocabulary(root, live_db):
    gpath = root / "simulator/config/genres.json"
    if gpath.exists():
        vocab = json.loads(gpath.read_text())
        vocab = set(vocab if isinstance(vocab, list) else vocab.get("genres", vocab))
        assert vocab == set(GENRES)
    seen = set()
    for (g,) in live_db.execute("SELECT genres FROM syn_venue_attributes"):
        seen |= {x for x in (g or "").split("|") if x}
    for (g,) in live_db.execute("SELECT DISTINCT music_genre FROM syn_scout_reports WHERE music_genre IS NOT NULL"):
        seen.add(g)
    assert seen <= set(GENRES), sorted(seen - set(GENRES))


def _night(ts: str):
    return (datetime.fromisoformat(ts) - timedelta(hours=6)).date()


def test_timestamps_tz_aware_and_nights_covered(live_db):
    nights = set()
    for (ts,) in live_db.execute("SELECT ts FROM syn_scout_reports"):
        dt = datetime.fromisoformat(ts)
        assert dt.tzinfo is not None, f"naive timestamp {ts}"
        nights.add(_night(ts))
    assert min(nights).isoformat() == SIM_FIRST_NIGHT
    assert max(nights).isoformat() == SIM_LAST_NIGHT
    assert len(nights) == SIM_NIGHTS
    assert {n.weekday() for n in nights} == {3, 4, 5}  # Thu, Fri, Sat


def test_demo_now_has_recent_reports(live_db):
    now = datetime.fromisoformat(DEMO_NOW)
    n = 0
    for (ts,) in live_db.execute("SELECT ts FROM syn_scout_reports WHERE ts LIKE '2026-11-14%'"):
        dt = datetime.fromisoformat(ts)
        if now - timedelta(minutes=180) <= dt <= now:
            n += 1
    assert n >= 20, f"only {n} reports in the 3 h before DEMO_NOW"


def test_real_twin_tables_not_in_live_sim(live_db):
    """Real twins belong to the backend DB, never to the synthetic file."""
    names = {r[0] for r in live_db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not (names & set(schemas.REAL_TWINS)) or all(
        live_db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0 for t in names & set(schemas.REAL_TWINS))
