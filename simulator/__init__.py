"""live-sim: deterministic synthetic nightlife simulator for the 35 LES launch venues.

`generate(cfg)` returns every syn_ table as a DataFrame (UTC timestamps, hidden `_` helper columns).
Every row is synthetic (is_synthetic = 1). See docs/synthetic/live-sim.md.
"""
from __future__ import annotations

import logging
import time

import pandas as pd

__version__ = "1.0.0"
log = logging.getLogger("simulator")


def generate(cfg: dict) -> dict[str, pd.DataFrame]:
    """Run every stage in order (each with its own seeded RNG) and return the tables."""
    from . import events, extract, feedback, nightloop, timeutil, truth, trust, updates, users, venues
    from .rng import stage_rng

    t0 = time.perf_counter()
    seed = cfg["seed"]
    nights = timeutil.nights(cfg.get("nights"))
    inputs = extract.load_inputs()
    attrs = venues.generate(cfg, stage_rng(seed, "venues"), inputs)
    upd = updates.generate(cfg, stage_rng(seed, "updates"), attrs, nights)
    tru = truth.generate(cfg, stage_rng(seed, "truth"), attrs, upd, nights)
    loop = nightloop.run(cfg, stage_rng(seed, "nightloop"), attrs, inputs, tru, nights, stage_rng(seed, "scouts"))
    tr = trust.run(cfg, stage_rng(seed, "trust"), loop["reports"], loop["bounties"], loop["scouts"], attrs,
                   inputs, nights)
    usr = users.generate(cfg, stage_rng(seed, "users"))
    pop = attrs.set_index("venue_id")["_popularity"]
    ev = events.generate(cfg, stage_rng(seed, "events"), tru, usr, pop)
    fb = feedback.generate(cfg, stage_rng(seed, "feedback"), tru, usr, inputs, attrs)
    tables = {"syn_venue_attributes": attrs, "syn_users": usr, "syn_venue_updates": upd, "syn_feedback": fb,
              "syn_venue_events": ev, "syn_true_state": tru, **tr}
    tables["_meta"] = pd.DataFrame([{"rate_limited_dropped": loop["stats"]["rate_limited_dropped"],
                                     "generate_seconds": round(time.perf_counter() - t0, 2),
                                     "nights": len(nights)}])
    log.info("generated %d nights in %.1fs", len(nights), time.perf_counter() - t0)
    return tables
