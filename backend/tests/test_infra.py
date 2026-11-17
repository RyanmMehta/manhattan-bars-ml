import re
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import Settings
from app.engine import StubEngine, get_engine
from app.simdb import read_schema, resolve_sim_path, schema_problems

APP = Path(__file__).resolve().parents[1] / "app"


def test_migration_upgrade_downgrade(tmp_path):
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
    url = f"sqlite:///{tmp_path}/m.db"
    cfg.attributes["url"] = url
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(f"{tmp_path}/m.db")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {
        "scout_reports",
        "venue_updates",
        "venue_events",
        "feedback",
        "bounties",
        "disputes",
        "points_ledger",
        "scouts",
        "users",
        "api_tokens",
        "venue_attributes",
    } <= tables
    command.downgrade(cfg, "base")


def test_no_truth_tables_in_app():
    banned = re.compile(r"syn_true_state|syn_scout_truth|syn_scout_reputation_history")
    hits = [p for p in APP.rglob("*.py") if banned.search(p.read_text())]
    assert hits == []


def test_every_syn_read_marked():
    """Each module that names a syn_ table carries a SYNTHETIC: marker."""
    for p in APP.rglob("*.py"):
        t = p.read_text()
        if re.search(r"\bsyn_[a-z_]+", t):
            assert "SYNTHETIC:" in t, p


def test_engine_selection():
    assert isinstance(get_engine("stub"), StubEngine)
    e = get_engine("auto")
    assert e.name in ("stub", "recs")


def test_recs_failure_falls_back(monkeypatch):
    import sys
    import types

    from app.engine.recs_engine import RecsEngine

    fake = types.ModuleType("recs")
    for sub in ("live_state", "scoring", "routing"):
        m = types.ModuleType(f"recs.{sub}")
        setattr(fake, sub, m)
        monkeypatch.setitem(sys.modules, f"recs.{sub}", m)

    def boom(*a, **k):
        raise RuntimeError("drift")

    fake.live_state.compute = fake.live_state.compute_all = boom
    fake.scoring.recommend = boom
    fake.routing.plan_night = boom
    monkeypatch.setitem(sys.modules, "recs", fake)
    e = get_engine("auto")
    assert e.name == "recs"
    from tests.fixtures.golden import G1_REPORTS, NOW, VENUE

    assert e.compute(VENUE, G1_REPORTS, [], NOW)["vibe_score"] == 65
    assert e.last_served == "stub"
    assert isinstance(e, RecsEngine)


def test_recs_bad_output_validated(make_client, monkeypatch):
    """A malformed recs state is replaced by the stub's, never returned raw."""
    c = make_client()
    eng = c.app.state.ctx.engine
    monkeypatch.setattr(
        eng, "compute_all", lambda *a: [{"venue_id": "0370-24-138636", "vibe_score": "loud"}]
    )
    r = c.get("/api/venues/0370-24-138636/state")
    assert r.status_code == 200 and isinstance(r.json()["vibe_score"], int)


def test_sim_schema_check(tmp_path, fixture_sim):
    assert schema_problems(read_schema(fixture_sim)) == []
    bad = tmp_path / "bad.db"
    conn = sqlite3.connect(bad)
    conn.execute("CREATE TABLE syn_scout_reports (report_id, venue_id)")
    conn.close()
    probs = schema_problems(read_schema(str(bad)))
    assert any("syn_scout_reports" in p and "crowd" in p for p in probs)
    s = Settings(live_sim_db=str(bad), allow_fixture_sim=False)
    path, problems = resolve_sim_path(s)
    assert path is None and problems
    s2 = Settings(
        live_sim_db=str(tmp_path / "missing.db"),
        allow_fixture_sim=True,
        fixture_sim_db=str(tmp_path / "synthetic" / "fx.db"),
    )
    path, problems = resolve_sim_path(s2)
    assert path and Path(path).exists() and "not found" in problems[0]


def test_sim_missing_optional_columns(make_client, tmp_path):
    """live-sim without status/distance_m still works (status treated as accepted)."""
    from app.simdb import EXPECTED

    p = tmp_path / "old_sim.db"
    conn = sqlite3.connect(p)
    for t, cols in EXPECTED.items():
        cols = [c for c in cols if not (t == "syn_scout_reports" and c in ("status", "distance_m"))]
        conn.execute(f"CREATE TABLE {t} ({', '.join(cols)})")
    conn.execute(
        "INSERT INTO syn_scout_reports VALUES ('syn-r-1','0370-24-138636','syn-s-1',"
        "'2026-11-14T23:20:00-05:00',4,1,10,NULL,NULL,1,1)"
    )
    conn.commit()
    conn.close()
    c = make_client(live_sim_db=str(p))
    assert c.get("/api/venues/0370-24-138636/state").json()["n_reports"] == 1
