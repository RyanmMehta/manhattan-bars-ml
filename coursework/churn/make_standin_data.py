"""SYNTHETIC stand-in for live-sim's Scout tables (fallback: used only while data/live_sim.db is missing).

Why it exists: the live-sim branch had no simulator/ code on Nov 17, so `data/live_sim.db`
could not be built. This script writes CSVs with the SAME columns as the contract tables
(CONTRACTS v2 §E), so load.py / build_dataset.py work unchanged once the real file exists.

Outputs (all is_synthetic=1, under coursework/churn/outputs/synthetic/):
  standin_scouts.csv, standin_scout_reports.csv, standin_points_ledger.csv,
  standin_bounties.csv, standin_scout_reputation_history.csv, standin_scout_truth.csv (eval only)
Run: python -I coursework/churn/make_standin_data.py --seed 0

How Scouts behave (the "data-generating process", so Ryan can explain what the model can learn):
  - 150 Scouts join in 12 weekly cohorts: 30 in launch week, ~11 a week after that
    (Aug 27 -> Nov 14 2026, Thu-Sat nights, 20:00-03:00 ET).
  - Each Scout has a starting engagement lam0 ~ Gamma(2.5, 1.5) reports/week that decays as
    exp(-weeks_since_join / tau), tau ~ LogNormal(ln 5, 0.6) weeks.
  - Saturdays get 1.5x the Thursday/Friday rate. Claiming a bounty boosts engagement +30% for 14 days.
  - A Scout "quits" for good (truth churned_at) when engagement falls under 0.35 reports/week,
    or with a 3%/week random-quit hazard (life happens).
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.common import ROOT  # noqa: E402

NY = ZoneInfo("America/New_York")
OUT = Path(__file__).resolve().parent / "outputs" / "synthetic"
FIRST_NIGHT, LAST_NIGHT = datetime(2026, 8, 27), datetime(2026, 11, 14)
ARCHETYPES = ["honest", "casual", "sloppy", "gamer", "shill"]
ARCH_P = [0.40, 0.30, 0.12, 0.12, 0.06]
ACCURACY = {"honest": 0.92, "casual": 0.8, "sloppy": 0.55, "gamer": 0.7, "shill": 0.4}
NIGHT_WEIGHT = {3: 0.8, 4: 1.0, 5: 1.5}  # Thu, Fri, Sat (weekday numbers) -> relative rate
GENRES = ["hip-hop", "r&b", "house", "techno", "pop", "top-40", "throwbacks", "indie", "rock", "latin"]


def nights() -> list[datetime]:
    days = (LAST_NIGHT - FIRST_NIGHT).days + 1
    return [FIRST_NIGHT + timedelta(d) for d in range(days) if (FIRST_NIGHT + timedelta(d)).weekday() in NIGHT_WEIGHT]


def make_scouts(rng: np.random.Generator, venues: list[str], n: int = 150) -> pd.DataFrame:
    rows = []
    for i in range(n):
        # launch week brings 30 Scouts (launch push), the other 120 join over weeks 1-11
        cohort = 0 if i < 30 else 1 + (i - 30) * 11 // (n - 30)
        joined = FIRST_NIGHT + timedelta(days=7 * cohort + int(rng.integers(0, 7)), hours=int(rng.integers(9, 23)))
        arch = str(rng.choice(ARCHETYPES, p=ARCH_P))
        rows.append({"scout_id": f"syn-s-{i + 1:04d}", "display_name": f"Scout {i + 1}",
                     "joined_at": joined.replace(tzinfo=NY), "cohort_week": cohort, "archetype": arch,
                     "home_venue_id": str(rng.choice(venues)), "true_accuracy": ACCURACY[arch],
                     "lam0": rng.gamma(2.5, 1.5) * (1.3 if arch == "gamer" else 1.0),
                     "tau": rng.lognormal(np.log(5), 0.6), "boost_until": None, "churned_at": None})
    return pd.DataFrame(rows)


def one_report(rng, scout, night, venue, rid) -> dict:
    """One 10-second vibe check with fields per CONTRACTS syn_scout_reports (+ status, distance_m)."""
    ts = night.replace(tzinfo=NY) + timedelta(hours=20, minutes=int(rng.integers(0, 7 * 60)))
    verified = int(rng.random() < (0.85 if scout["archetype"] in ("honest", "casual") else 0.45))
    bad = rng.random() > scout["true_accuracy"]               # inaccurate report -> more likely flagged
    status = str(rng.choice(["flagged", "removed", "accepted"], p=[0.35, 0.25, 0.40])) if bad else "accepted"
    return {"report_id": f"syn-r-{rid:06d}", "venue_id": venue, "scout_id": scout["scout_id"],
            "ts": ts.isoformat(), "crowd": int(rng.integers(1, 6)), "dancing": int(rng.integers(0, 3)),
            "line_minutes": int(rng.choice([0, 0, 5, 10, 15, 20, 30])),
            "cover_usd": None if rng.random() < 0.5 else int(rng.choice([0, 10, 15, 20])),
            "music_genre": None if rng.random() < 0.3 else str(rng.choice(GENRES)),
            "verified_presence": verified, "status": status,
            "distance_m": int(rng.integers(5, 150)) if verified else None, "is_synthetic": 1}


def simulate(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    # SYNTHETIC: launch venues are real public data; everything generated below is synthetic
    venues = pd.read_csv(ROOT / "data" / "launch_venues.csv")["license_id"].tolist()
    scouts = make_scouts(rng, venues)
    reports, bounties, ledger = [], [], []
    for night in nights():
        night_start = night.replace(tzinfo=NY) + timedelta(hours=20)
        open_bounties = {}
        for v in rng.choice(venues, size=3, replace=False):  # 3 bounties per night
            bid = f"syn-b-{len(bounties) + 1:05d}"
            open_bounties[str(v)] = bid
            bounties.append({"bounty_id": bid, "venue_id": str(v), "created_at": night_start.isoformat(),
                             "points": 25, "reason": "no fresh reports", "claimed_by": None,
                             "expires_at": (night_start + timedelta(hours=7)).isoformat(),
                             "claimed_at": None, "is_synthetic": 1})
        night_reports = []
        for i, s in scouts.iterrows():
            if s["joined_at"] > night_start or s["churned_at"] is not None:
                continue
            weeks = (night_start - s["joined_at"]).days / 7
            lam = s["lam0"] * np.exp(-weeks / s["tau"])           # reports per week, decaying
            if s["boost_until"] is not None and night_start < s["boost_until"]:
                lam *= 1.3                                        # bounty bump
            if lam < 0.35 or rng.random() < 0.03 / 3:             # quits for good
                scouts.at[i, "churned_at"] = night_start
                continue
            for _ in range(rng.poisson(lam * NIGHT_WEIGHT[night.weekday()] / 3.3)):
                venue = s["home_venue_id"] if rng.random() < 0.5 else str(rng.choice(venues))
                night_reports.append(one_report(rng, s, night, venue, len(reports) + len(night_reports) + 1))
        night_reports.sort(key=lambda r: r["ts"])
        for r in night_reports:                                  # first report at a bounty venue claims it
            ledger.append({"scout_id": r["scout_id"], "report_id": r["report_id"], "bounty_id": None,
                           "points": 10 if r["status"] == "accepted" else 0, "reason": "report", "ts": r["ts"]})
            bid = open_bounties.pop(r["venue_id"], None)
            if bid and r["status"] != "removed":
                b = bounties[int(bid.split("-")[-1]) - 1]
                b["claimed_by"], b["claimed_at"] = r["scout_id"], r["ts"]
                ledger.append({"scout_id": r["scout_id"], "report_id": r["report_id"], "bounty_id": bid,
                               "points": 25, "reason": "bounty", "ts": r["ts"]})
                row = scouts.index[scouts["scout_id"] == r["scout_id"]][0]
                scouts.at[row, "boost_until"] = datetime.fromisoformat(r["ts"]) + timedelta(days=14)
        reports += night_reports
    return {"scouts": scouts, "reports": pd.DataFrame(reports), "bounties": pd.DataFrame(bounties),
            "ledger": pd.DataFrame(ledger)}


def reputation_history(reports: pd.DataFrame, ledger: pd.DataFrame, scouts: pd.DataFrame) -> pd.DataFrame:
    """Daily as-of reputation/points/level. Reputation = running average of 'accepted' (starts at 0.5)."""
    rep = reports.assign(day=pd.to_datetime(reports["ts"], utc=True).dt.tz_convert(NY).dt.date,
                         ok=(reports["status"] == "accepted").astype(float))
    led = ledger.assign(day=pd.to_datetime(ledger["ts"], utc=True).dt.tz_convert(NY).dt.date)
    rows = []
    for _, s in scouts.iterrows():
        r_s, l_s = rep[rep.scout_id == s.scout_id], led[led.scout_id == s.scout_id]
        day, reputation = s["joined_at"].date(), 0.5
        while day <= LAST_NIGHT.date() + timedelta(1):
            for ok in r_s.loc[r_s.day == day, "ok"]:
                reputation = 0.9 * reputation + 0.1 * ok       # exponential moving average
            points = int(l_s.loc[l_s.day <= day, "points"].sum())
            rows.append({"scout_id": s.scout_id, "as_of_date": day.isoformat(), "reputation": round(reputation, 4),
                         "points": points, "level": 1 + points // 200, "is_synthetic": 1})
            day += timedelta(1)
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    sim = simulate(args.seed)
    scouts, reports, ledger = sim["scouts"], sim["reports"], sim["ledger"]
    ledger.insert(0, "entry_id", [f"syn-l-{i + 1:06d}" for i in range(len(ledger))])
    ledger["is_synthetic"] = 1
    history = reputation_history(reports, ledger, scouts)
    final = history.groupby("scout_id").last()
    last_ts = reports.groupby("scout_id")["ts"].max()
    out_scouts = pd.DataFrame({  # end-of-simulation SNAPSHOT columns, exactly like live-sim's syn_scouts
        "scout_id": scouts.scout_id, "display_name": scouts.display_name,
        "joined_at": scouts.joined_at.map(lambda d: d.isoformat()),
        "reputation": scouts.scout_id.map(final["reputation"]), "points": scouts.scout_id.map(final["points"]),
        "level": scouts.scout_id.map(final["level"]),
        "reports_count": scouts.scout_id.map(reports.groupby("scout_id").size()).fillna(0).astype(int),
        "last_active_at": scouts.scout_id.map(last_ts), "is_synthetic": 1})
    truth = scouts[["scout_id", "archetype", "home_venue_id", "true_accuracy", "cohort_week"]].assign(
        churned_at=scouts.churned_at.map(lambda d: d.isoformat() if d is not None else None), is_synthetic=1)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in [("scouts", out_scouts), ("scout_reports", reports), ("points_ledger", ledger),
                     ("bounties", sim["bounties"]), ("scout_reputation_history", history),
                     ("scout_truth", truth)]:
        df.to_csv(OUT / f"standin_{name}.csv", index=False)  # SYNTHETIC: replace with live-sim syn_{name}
    print(f"stand-in: {len(out_scouts)} scouts, {len(reports)} reports, {len(sim['bounties'])} bounties, "
          f"{truth.churned_at.notna().mean():.0%} churned by Nov 14 -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
