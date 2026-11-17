"""Generate the research workstream's SYNTHETIC interview and survey datasets.

Purpose
    Placeholder data with the same shape real interviews/surveys will have, so
    tableau / frontend / coursework can build now and swap later. Every row is
    `is_synthetic = 1`, every ID starts `syn-`, every quote starts "[SYNTHETIC] ".
    Nothing here is a real finding. CSV only: no database is read or written
    (CONTRACTS v2 section E).

Usage
    python -I research/gen_synthetic.py [--seed 42] [--n-interviews 15]
                                        [--n-survey 300] [--out-dir DIR] [--no-db]

Outputs (default DIR = research/synthetic/)
    syn_interviews.csv, syn_interview_quotes.csv, syn_survey_responses.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "research" / "synthetic"
LAUNCH_VENUES = ROOT / "data" / "launch_venues.csv"
GENRES_JSON = ROOT / "simulator" / "config" / "genres.json"
ET = ZoneInfo("America/New_York")

# Shared genre vocabulary (CONTRACTS v2.1 section E). Owned by live-sim at
# simulator/config/genres.json; this copy is checked against it by the tests.
GENRES_FALLBACK = [
    "hip-hop", "r&b", "afrobeats", "latin", "reggaeton", "house", "techno", "edm",
    "disco", "pop", "top-40", "throwbacks", "indie", "rock", "punk", "jazz", "soul-funk",
]
FACTORS = ["genres", "want_dancing", "crowd_pref", "max_cover_usd",
           "max_line_minutes", "max_distance_km", "price", "friends_there"]
TOOLS = ["google_maps", "instagram", "group_chat", "partiful", "resy", "dice", "yelp", "tiktok"]
AGE_BANDS = ["18-20", "21-24", "25-29", "30-34", "35+"]
FRESHNESS_OPTIONS = [15, 30, 45, 60, 90, 120]
NEIGHBORHOODS = ["les", "east_village", "soho", "williamsburg", "west_village",
                 "chinatown", "bushwick", "midtown"]
OPERATOR_WANTS = ["claimed_profile", "post_offers", "dj_updates", "demand_analytics",
                  "scout_reports_on_my_venue", "competitor_benchmark"]

# All values are [PLACEHOLDER] guesses, not findings.
PRIORS = {
    # SYNTHETIC: survey Q1 age_band distribution
    "age_band_p": [0.15, 0.45, 0.28, 0.08, 0.04],
    # SYNTHETIC: survey Q2 share of students per age band
    "student_p_by_age": [0.95, 0.70, 0.25, 0.08, 0.03],
    # SYNTHETIC: survey Q3 median nights out / month (Poisson rate) and latent slope
    "nights_out_lambda": 6.0, "nights_out_z_slope": 0.4,
    # SYNTHETIC: survey Q4 group size = 1 + Poisson(lambda)
    "group_extra_lambda": 2.8,
    # SYNTHETIC: survey Q5 who picks
    "who_picks": {"me": 0.35, "friend": 0.30, "rotates": 0.20, "group_vote": 0.15},
    # SYNTHETIC: survey Q6 decision minutes ~ lognormal(median, sigma)
    "decision_median_min": 20.0, "decision_sigma": 0.6,
    # SYNTHETIC: survey Q7 per-tool usage probability
    "tool_p": {"google_maps": 0.70, "instagram": 0.65, "group_chat": 0.80, "partiful": 0.25,
               "resy": 0.20, "dice": 0.15, "yelp": 0.30, "tiktok": 0.35},
    # SYNTHETIC: survey Q8 bad pick in last month, logistic(b0 + bz*z)
    "bad_pick_b0": 0.4, "bad_pick_bz": 0.5,
    # SYNTHETIC: survey Q9 factor-importance Dirichlet concentration
    "importance_alpha": {"genres": 3.0, "want_dancing": 1.8, "crowd_pref": 2.6,
                         "max_cover_usd": 2.4, "max_line_minutes": 3.2,
                         "max_distance_km": 1.6, "price": 2.0, "friends_there": 1.4},
    # SYNTHETIC: survey Q10 genre popularity weights (same order as GENRES) and no-pref share
    "genre_w": [10, 7, 4, 4, 4, 6, 3, 3, 3, 6, 5, 6, 4, 3, 1, 2, 2],
    "genre_no_pref_p": 0.12,
    # SYNTHETIC: survey Q11 freshness tolerance option probabilities
    "freshness_p": [0.18, 0.32, 0.15, 0.22, 0.08, 0.05],
    # SYNTHETIC: survey Q12 trust cue preference
    "trust_cue": {"n_reports": 0.30, "recency": 0.38, "verified_scout": 0.20, "venue_official": 0.12},
    # SYNTHETIC: survey Q13 would_use_weekly logistic coefficients
    "use_b0": -0.5, "use_bz": 0.9, "use_b_badpick": 0.6,
    # SYNTHETIC: survey Q14 NPS = clip(round(mean + sd*(0.6 z + noise)))
    "nps_mean": 6.0, "nps_sd": 2.0,
    # SYNTHETIC: survey Q15 would_scout ordinal thresholds on latent z + noise
    "scout_cuts": [0.2, 1.1, 2.3],
    # SYNTHETIC: survey Q16 reports per night if scout ~ Poisson
    "reports_lambda": 1.4,
    # SYNTHETIC: survey Q17 reward preference
    "points_pref": {"free_drink": 0.34, "skip_line": 0.30, "cover_waiver": 0.24, "status": 0.12},
    # SYNTHETIC: survey fielding window (real export timestamps replace this)
    "survey_start": "2026-10-26", "survey_end": "2026-11-12",
    # SYNTHETIC: interview segment mix and dates (real note template rows replace this)
    "interview_mix": {"consumer": 8, "scout": 3, "operator": 4},
    "interview_start": "2026-11-02", "interview_end": "2026-11-12",
    # SYNTHETIC: operator interview answers (roles, willingness to pay USD/month)
    "operator_role": {"owner": 0.35, "gm": 0.30, "bar_manager": 0.20, "promoter": 0.15},
    "operator_wtp_choices": [0, 0, 25, 49, 49, 99, 150],
    # SYNTHETIC: scout motivators from interviews
    "scout_motivator": {"points": 0.15, "perks": 0.45, "status": 0.15, "helping": 0.20, "none": 0.05},
    # SYNTHETIC: quotes per interview (uniform integer range, inclusive)
    "quotes_per_interview": [4, 6],
}

# SYNTHETIC: real anonymized quotes from interview notes replace these templates.
QUOTE_TEMPLATES = {
    "pain": {
        "H1": [(-1, "Last weekend we walked to {n} places before we found one that wasn't dead or a 40-minute line."),
               (-1, "The bar looked great on Instagram but it was empty when we showed up around {hh}."),
               (0, "Honestly it works out about half the time, the other half we just settle.")],
        "H2": [(-1, "We spent like {m} minutes in the group chat arguing before anyone moved."),
               (0, "Picking the spot is always on me and it takes longer than it should.")],
    },
    "tools": {
        "H3": [(0, "I check Google Maps for how busy it is but I don't really know how live that is."),
               (0, "Mostly I watch stories from friends who are already out, then decide."),
               (-1, "Every app I've tried tells me what a place is like in general, not tonight.")],
    },
    "trust": {
        "H4": [(0, "If it's more than about {f} minutes old I'd assume it changed."),
               (1, "Seeing '12 minutes ago' would make me trust it way more than a star rating.")],
        "H6": [(1, "If a few different people said the same thing I'd believe it."),
               (-1, "If the bar posts it themselves I'd assume it's marketing.")],
    },
    "scouting": {
        "H7": [(1, "I'd tap a ten-second check-in if I'm already there, sure."),
               (-1, "I'm not going to stop my night to fill out a form."),
               (0, "Maybe once a night, if it was really quick.")],
        "H8": [(1, "Skipping the line would get me to do it every time."),
               (0, "Points alone don't do much for me, a free drink would.")],
    },
    "pricing": {
        "H10": [(1, "If it shows me when people are deciding where to go, ${w} a month is nothing."),
                (-1, "We already pay for enough marketing tools, I'd need to see bodies in the door."),
                (0, "I'd try a free profile first and see if it moves anything.")],
        "H11": [(1, "Posting the DJ and the cover each week is easy, we do it on Instagram anyway."),
                (-1, "Nobody here has time to update another app on a Saturday.")],
    },
    "other": {
        "H12": [(1, "If it actually knew what my group likes I'd open it every time we go out."),
                (0, "It sounds useful, but I'd need my friends on it too."),
                (-1, "I kind of like just wandering around the LES and seeing what's good.")],
        "H9": [(0, "Usually one person decides and everyone else just complains after.")],
    },
}
SEGMENT_THEMES = {
    "consumer": ["pain", "tools", "trust", "other", "scouting"],
    "scout": ["scouting", "trust", "pain", "tools", "other"],
    "operator": ["pricing", "tools", "trust", "other"],
}


def load_genres() -> list[str]:
    """Shared genre slugs: simulator/config/genres.json when present, else the copied constant."""
    if GENRES_JSON.exists():
        data = json.loads(GENRES_JSON.read_text())
        if isinstance(data, dict):
            data = data.get("genres", data.get("slugs", list(data)))
        slugs = [g["slug"] if isinstance(g, dict) else g for g in data]
        return list(slugs)
    return list(GENRES_FALLBACK)


def load_launch_venue_ids() -> list[str]:
    with LAUNCH_VENUES.open(newline="", encoding="utf-8") as fh:
        return [row["license_id"] for row in csv.DictReader(fh)]


def _choice(rng: np.random.Generator, probs: dict[str, float]) -> str:
    keys = list(probs)
    p = np.array([probs[k] for k in keys], dtype=float)
    return keys[int(rng.choice(len(keys), p=p / p.sum()))]


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _tools(rng: np.random.Generator) -> str:
    picked = [t for t in TOOLS if rng.random() < PRIORS["tool_p"][t]]
    return "|".join(picked) if picked else "none"


def _genres(rng: np.random.Generator, genres: list[str], k_max: int = 3) -> str:
    w = np.array(PRIORS["genre_w"][: len(genres)] + [1] * max(0, len(genres) - len(PRIORS["genre_w"])), float)
    k = int(rng.integers(1, k_max + 1))
    idx = rng.choice(len(genres), size=k, replace=False, p=w / w.sum())
    return "|".join(genres[i] for i in sorted(idx))


def _importance(rng: np.random.Generator) -> dict[str, int]:
    alpha = np.array([PRIORS["importance_alpha"][f] for f in FACTORS])
    w = rng.dirichlet(alpha * 2.0)
    raw = 1 + 4 * w / w.max() + rng.normal(0, 0.4, len(FACTORS))
    return {f: int(np.clip(round(v), 1, 5)) for f, v in zip(FACTORS, raw)}


def _ts_between(rng: np.random.Generator, start: str, end: str, n: int) -> list[dt.datetime]:
    t0 = dt.datetime.fromisoformat(start).replace(tzinfo=ET).timestamp()
    t1 = (dt.datetime.fromisoformat(end) + dt.timedelta(days=1)).replace(tzinfo=ET).timestamp() - 1
    secs = np.sort(rng.uniform(t0, t1, n))
    return [dt.datetime.fromtimestamp(int(s), tz=ET) for s in secs]


def make_survey(rng: np.random.Generator, n: int, genres: list[str]) -> list[dict]:
    """SYNTHETIC: replaced by the real survey export mapped through research/survey/codebook.csv."""
    P = PRIORS
    rows = []
    for i, ts in enumerate(_ts_between(rng, P["survey_start"], P["survey_end"], n), start=1):
        z = float(rng.normal())
        a = int(rng.choice(len(AGE_BANDS), p=P["age_band_p"]))
        bad = int(rng.random() < _sigmoid(P["bad_pick_b0"] + P["bad_pick_bz"] * z))
        imp = _importance(rng)
        no_pref = int(rng.random() < P["genre_no_pref_p"])
        scout_latent = z + float(rng.normal(0, 0.9))
        would_scout = int(np.searchsorted(P["scout_cuts"], scout_latent))
        rows.append({
            "response_id": f"syn-srv-{i:04d}",
            "submitted_at": ts.isoformat(),
            "age_band": AGE_BANDS[a],
            "student": int(rng.random() < P["student_p_by_age"][a]),
            "nights_out_per_month": int(np.clip(rng.poisson(P["nights_out_lambda"] * np.exp(P["nights_out_z_slope"] * z)), 0, 30)),
            "typical_group_size": int(np.clip(1 + rng.poisson(P["group_extra_lambda"]), 1, 12)),
            "who_picks": _choice(rng, P["who_picks"]),
            "decision_minutes": int(np.clip(round(rng.lognormal(np.log(P["decision_median_min"]), P["decision_sigma"])), 0, 120)),
            "current_tools": _tools(rng),
            "bad_pick_last_month": bad,
            **{f"importance_{f}": imp[f] for f in FACTORS},
            "favorite_genres": "" if no_pref else _genres(rng, genres),
            "genre_no_pref": no_pref,
            "freshness_tolerance_min": int(FRESHNESS_OPTIONS[int(rng.choice(6, p=P["freshness_p"]))]),
            "trust_cue_pref": _choice(rng, P["trust_cue"]),
            "would_use_weekly": int(rng.random() < _sigmoid(P["use_b0"] + P["use_bz"] * z + P["use_b_badpick"] * bad)),
            "nps_concept": int(np.clip(round(P["nps_mean"] + P["nps_sd"] * (0.6 * z + 0.8 * rng.normal())), 0, 10)),
            "would_scout": would_scout,
            "reports_per_night_if_scout": 0 if would_scout == 0 else int(np.clip(rng.poisson(P["reports_lambda"]), 0, 10)),
            "points_value_pref": _choice(rng, P["points_pref"]),
            "is_synthetic": 1,
        })
    return rows


def make_interviews(rng: np.random.Generator, n: int, genres: list[str], venue_ids: list[str]) -> list[dict]:
    """SYNTHETIC: replaced by research/interviews/interviews.csv filled from the note template."""
    P = PRIORS
    mix = P["interview_mix"]
    total = sum(mix.values())
    counts = {k: int(round(v * n / total)) for k, v in mix.items()}
    counts["consumer"] += n - sum(counts.values())
    segments = [s for s in ("consumer", "scout", "operator") for _ in range(counts[s])]
    dates = [d.date().isoformat() for d in _ts_between(rng, P["interview_start"], P["interview_end"], len(segments))]
    rows = []
    for i, (seg, date) in enumerate(zip(segments, dates), start=1):
        z = float(rng.normal()) + (1.0 if seg == "scout" else 0.0)
        mentions = rng.choice(len(venue_ids), size=int(rng.integers(1, 4)), replace=False)
        hoods = rng.choice(len(NEIGHBORHOODS), size=int(rng.integers(1, 4)), replace=False,
                           p=np.array([5, 3, 1, 2, 1, 2, 1, 1], float) / 16)
        row = {
            "interview_id": f"syn-int-{i:03d}", "segment": seg, "date": date,
            "age_band": AGE_BANDS[int(rng.choice(5, p=P["age_band_p"]))] if seg != "operator" else "na",
            "nights_out_per_month": int(np.clip(rng.poisson(P["nights_out_lambda"] * np.exp(0.4 * z)), 0, 30)),
            "typical_group_size": "", "neighborhoods": "|".join(NEIGHBORHOODS[j] for j in sorted(hoods)),
            "current_tools": _tools(rng), "bad_pick_last_month": "", "favorite_genres": _genres(rng, genres),
            "top_factor_1": "", "top_factor_2": "", "top_factor_3": "", "freshness_tolerance_min": "",
            "would_scout": "", "scout_motivator": "", "operator_role": "", "operator_wtp_usd_month": "",
            "operator_wants": "", "venue_mentions": "|".join(venue_ids[j] for j in sorted(mentions)),
            "concept_reaction": int(np.clip(round(3.4 + 0.7 * z + rng.normal(0, 0.6)), 1, 5)),
            "is_synthetic": 1,
        }
        if seg == "operator":
            wants = rng.choice(len(OPERATOR_WANTS), size=int(rng.integers(1, 4)), replace=False)
            row.update({
                "nights_out_per_month": int(rng.integers(12, 27)),
                "operator_role": _choice(rng, P["operator_role"]),
                "operator_wtp_usd_month": int(rng.choice(P["operator_wtp_choices"])),
                "operator_wants": "|".join(OPERATOR_WANTS[j] for j in sorted(wants)),
            })
        else:
            alpha = np.array([P["importance_alpha"][f] for f in FACTORS])
            top = rng.choice(len(FACTORS), size=3, replace=False, p=alpha / alpha.sum())
            row.update({
                "typical_group_size": int(np.clip(1 + rng.poisson(P["group_extra_lambda"]), 1, 12)),
                "bad_pick_last_month": int(rng.random() < _sigmoid(P["bad_pick_b0"] + P["bad_pick_bz"] * z)),
                "top_factor_1": FACTORS[top[0]], "top_factor_2": FACTORS[top[1]], "top_factor_3": FACTORS[top[2]],
                "freshness_tolerance_min": int(FRESHNESS_OPTIONS[int(rng.choice(6, p=P["freshness_p"]))]),
                "would_scout": int(np.searchsorted(P["scout_cuts"], z + rng.normal(0, 0.7))) if seg == "consumer" else int(rng.choice([2, 3])),
                "scout_motivator": _choice(rng, P["scout_motivator"]),
            })
        rows.append(row)
    return rows


def make_quotes(rng: np.random.Generator, interviews: list[dict]) -> list[dict]:
    """SYNTHETIC: replaced by research/interviews/quotes.csv (real, anonymized)."""
    lo, hi = PRIORS["quotes_per_interview"]
    rows, qid = [], 0
    for iv in interviews:
        themes = SEGMENT_THEMES[iv["segment"]]
        for _ in range(int(rng.integers(lo, hi + 1))):
            theme = themes[int(rng.integers(len(themes)))]
            hyps = list(QUOTE_TEMPLATES[theme])
            hyp = hyps[int(rng.integers(len(hyps)))]
            sentiment, template = QUOTE_TEMPLATES[theme][hyp][int(rng.integers(len(QUOTE_TEMPLATES[theme][hyp])))]
            text = template.format(
                n=int(rng.integers(2, 5)), hh=["11", "midnight", "10:30"][int(rng.integers(3))],
                m=int(rng.integers(15, 60)), f=iv["freshness_tolerance_min"] or 30,
                w=iv["operator_wtp_usd_month"] or 49)
            qid += 1
            rows.append({"quote_id": f"syn-q-{qid:04d}", "interview_id": iv["interview_id"],
                         "hypothesis_id": hyp, "theme": theme, "sentiment": sentiment,
                         "text": "[SYNTHETIC] " + text, "is_synthetic": 1})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def generate(seed: int = 42, n_interviews: int = 15, n_survey: int = 300) -> dict[str, list[dict]]:
    rng = np.random.default_rng(seed)
    genres = load_genres()
    venue_ids = load_launch_venue_ids()
    interviews = make_interviews(rng, n_interviews, genres, venue_ids)
    quotes = make_quotes(rng, interviews)
    survey = make_survey(rng, n_survey, genres)
    return {"syn_interviews": interviews, "syn_interview_quotes": quotes, "syn_survey_responses": survey}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-interviews", type=int, default=15)
    ap.add_argument("--n-survey", type=int, default=300)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--no-db", action="store_true", help="no-op: this script never writes a database")
    args = ap.parse_args()
    data = generate(args.seed, args.n_interviews, args.n_survey)
    for name, rows in data.items():
        write_csv(args.out_dir / f"{name}.csv", rows)
        print(f"wrote {args.out_dir / (name + '.csv')} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
