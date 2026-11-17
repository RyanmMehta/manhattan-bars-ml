"""Unit tests for reference_scoring.py and the golden checker (stdlib unittest).

    python -I -m unittest discover -s docs/specs/tools -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_golden as B  # noqa: E402
import check_golden as C  # noqa: E402
import reference_scoring as R  # noqa: E402

NOW = B.NOW
V = "0370-24-119240"


def rep(age: float, crowd: int = 4, scout: int = 1, **kw) -> dict:
    """Minimal synthetic report at venue V."""
    row = {"venue_id": V, "scout_id": f"syn-s-{scout:04d}", "ts": B.ts(age), "crowd": crowd,
           "dancing": 1, "line_minutes": 10, "verified_presence": 1, "reputation": 0.8,
           "status": "accepted", "is_synthetic": 1}
    row.update(kw)
    return row


class DecayAndMedian(unittest.TestCase):
    def test_half_life(self):
        self.assertAlmostEqual(R.decay(30, 30), 0.5)
        self.assertAlmostEqual(R.decay(0, 30), 1.0)
        self.assertAlmostEqual(R.decay(-2, 30), 1.0)  # future skew clamps to age 0

    def test_weighted_median_resists_troll(self):
        self.assertEqual(R.wmedian([(10, 1.0), (10, 1.0), (60, 1.5)]), 10)

    def test_weighted_median_lower_on_exact_half(self):
        self.assertEqual(R.wmedian([(5, 1.0), (15, 1.0)]), 5)

    def test_round_half_up(self):
        self.assertEqual(R.round_half_up(64.5), 65)
        self.assertEqual(R.round_half_up(0.125, 2), 0.13)


class Eligibility(unittest.TestCase):
    def test_cutoff_and_future(self):
        s = R.compute_state(V, [rep(181), rep(-3)], [], NOW)
        self.assertEqual(s["n_reports"], 0)
        s = R.compute_state(V, [rep(180), rep(-2)], [], NOW)
        self.assertEqual(s["n_reports"], 2)

    def test_missing_status_is_accepted(self):
        r = rep(5)
        del r["status"]
        self.assertEqual(R.compute_state(V, [r], [], NOW)["n_reports"], 1)

    def test_flagged_and_removed_count_zero(self):
        s = R.compute_state(V, [rep(5, status="flagged"), rep(5, status="removed")], [], NOW)
        self.assertEqual((s["n_reports"], s["vibe_score"], s["confidence"]), (0, None, 0.0))


class Confidence(unittest.TestCase):
    def test_no_inputs(self):
        s = R.compute_state(V, [], [], NOW)
        self.assertEqual((s["vibe_score"], s["confidence"], s["display"], s["freshness_minutes"]),
                         (None, 0.0, "none", None))
        self.assertEqual(s["sources"], [])

    def test_one_scout_capped_by_diversity(self):
        parts = R.confidence_parts(R.eligible_reports([rep(0)], R.parse_ts(NOW)), [])
        self.assertEqual(parts["diverse"], 0.6)
        self.assertEqual(parts["agree"], 1.0)

    def test_operator_only_capped(self):
        upd = {"venue_id": V, "ts": B.ts(0), "cover_usd": 10, "genres": "house", "is_synthetic": 1}
        s = R.compute_state(V, [], [upd, dict(upd), dict(upd)], NOW)
        self.assertIsNone(s["vibe_score"])
        self.assertEqual(s["confidence"], 0.25)
        self.assertIsNone(s["crowd"])

    def test_operator_never_sets_crowd(self):
        upd = {"venue_id": V, "ts": B.ts(0), "cover_usd": 10, "genres": None, "crowd": 5}
        self.assertIsNone(R.compute_state(V, [], [upd], NOW)["crowd"])


class Vibe(unittest.TestCase):
    def test_renormalises_when_line_missing(self):
        self.assertAlmostEqual(R.vibe_raw(5, 2, None), 100.0)
        self.assertAlmostEqual(R.vibe_raw(3, None, None), 50.0)

    def test_crowd_null_means_vibe_null(self):
        self.assertIsNone(R.vibe_raw(None, 2, 30))

    def test_bands(self):
        def lab(v):
            return R.ui_labels({"vibe_score": v, "freshness_minutes": 0})["vibe_label"]
        self.assertEqual([lab(34), lab(35), lab(64), lab(65), lab(None)],
                         ["Chill", "Lively", "Lively", "Packed", None])

    def test_stale_tag(self):
        self.assertTrue(R.ui_labels({"vibe_score": 50, "freshness_minutes": 61})["stale"])
        self.assertFalse(R.ui_labels({"vibe_score": 50, "freshness_minutes": 60})["stale"])


class Trend(unittest.TestCase):
    def test_null_when_windows_thin(self):
        reps = R.eligible_reports([rep(5), rep(80, crowd=2)], R.parse_ts(NOW))
        self.assertIsNone(R.trend(reps))

    def test_steady(self):
        rows = [rep(a, scout=i) for i, a in enumerate((5, 10, 40, 50))]
        self.assertEqual(R.trend(R.eligible_reports(rows, R.parse_ts(NOW))), "steady")


class Match(unittest.TestCase):
    PREFS = B.CONTRACT_PREFS
    VENUE = B.VENUES["HSH"]

    def state(self, **kw) -> dict:
        s = R.compute_state(V, [], [], NOW)
        s.update(kw)
        return s

    def test_unknown_cover_not_excluded(self):
        out = R.recommend(self.PREFS, [self.state(crowd=4.0, confidence=0.5)], [self.VENUE], NOW)[0]
        self.assertFalse(out["excluded"])
        self.assertIn("cover not reported tonight", out["missing"])

    def test_known_cover_excluded(self):
        out = R.recommend(self.PREFS, [self.state(cover_usd=25)], [self.VENUE], NOW)[0]
        self.assertEqual(out["excluded_reason"], "cover $25 over your $20")

    def test_known_line_excluded(self):
        out = R.recommend(self.PREFS, [self.state(line_minutes=20)], [self.VENUE], NOW)[0]
        self.assertEqual(out["excluded_reason"], "line ~20 min over your 15")

    def test_distance_excluded(self):
        prefs = dict(self.PREFS, max_distance_km=0.2)
        out = R.recommend(prefs, [self.state()], [self.VENUE], NOW)[0]
        self.assertTrue(out["excluded_reason"].endswith("over your 0.2 km"))

    def test_closed_excludes_unknown_hours_do_not(self):
        closed = dict(self.VENUE, is_open_now=False)
        self.assertEqual(R.recommend(self.PREFS, [], [closed], NOW)[0]["excluded_reason"], "closed now")
        self.assertFalse(R.recommend(self.PREFS, [], [self.VENUE], NOW)[0]["excluded"])

    def test_empty_genres_scores_one_without_reason(self):
        s, reason, missing = R.comp_genre({"genres": []}, self.state(), self.VENUE)
        self.assertEqual((s, reason, missing), (1.0, None, None))

    def test_static_genre_overlap(self):
        s, reason, _ = R.comp_genre({"genres": ["house"]}, self.state(), self.VENUE)
        self.assertEqual((s, reason), (0.6, "Usually plays House"))

    def test_want_dancing_null_drops_weight(self):
        self.assertIsNone(R.comp_dancing({"want_dancing": None}, self.state(dancing=2.0))[0])

    def test_excluded_sorted_last(self):
        other = B.VENUES["VER"]
        states = [self.state(venue_id=V, cover_usd=25, crowd=4.0, confidence=0.9),
                  self.state(venue_id=other["venue_id"], crowd=2.0, confidence=0.2)]
        out = R.recommend(self.PREFS, states, [self.VENUE, other], NOW)
        self.assertEqual([r["excluded"] for r in out], [False, True])
        self.assertEqual([r["rank"] for r in out], [1, 2])


class Golden(unittest.TestCase):
    def test_goldens_pass(self):
        self.assertEqual(C.check(), [])

    def test_g2_stale(self):
        g2 = {v["id"]: v for v in B.build_all()}["G2"]
        s = g2["expected"]["states"][0]
        self.assertLess(s["confidence"], 0.20)
        self.assertEqual(s["display"], "none")
        self.assertTrue(g2["expected"]["ui"][s["venue_id"]]["stale"])


if __name__ == "__main__":
    unittest.main()
