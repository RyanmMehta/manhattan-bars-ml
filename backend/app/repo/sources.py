"""The ONLY place that builds `real UNION ALL syn_*` selects (RULES §7.7).
INCLUDE_SYNTHETIC=0 (or no sim DB) drops the synthetic side here and nowhere else."""

from dataclasses import dataclass, field

from ..simdb import EXPECTED

# Neutral fills when a live-sim table lacks an optional column (specs §5.1: no status = accepted)
FILL = {"status": "'accepted'"}

# SYNTHETIC: twin tables of live-sim; replace by real tables (same name without `syn_`)
TWINS = {
    "scout_reports": "syn_scout_reports",
    "venue_updates": "syn_venue_updates",
    "venue_events": "syn_venue_events",
    "scouts": "syn_scouts",
    "users": "syn_users",
    "bounties": "syn_bounties",
    "points_ledger": "syn_points_ledger",
    "feedback": "syn_feedback",
    "venue_attributes": "syn_venue_attributes",
}


@dataclass
class Sources:
    include_synthetic: bool
    sim_prefix: str
    sim_schema: dict[str, set[str]] = field(default_factory=dict)

    @property
    def synthetic_on(self) -> bool:
        return self.include_synthetic and bool(self.sim_schema)

    def has_sim(self, real: str) -> bool:
        return self.synthetic_on and TWINS[real] in self.sim_schema

    def union(self, real: str, where: str = "", cols: list[str] | None = None) -> str:
        """SQL for `(SELECT cols FROM real [WHERE] UNION ALL SELECT cols FROM sim.syn_real)`.
        `where` is applied to both sides and may use bind params."""
        twin = TWINS[real]
        cols = cols or EXPECTED[twin]
        w = f" WHERE {where}" if where else ""
        sql = f"SELECT {', '.join(cols)} FROM {real}{w}"
        if self.has_sim(real):
            have = self.sim_schema[twin]
            sim_cols = [c if c in have else f"{FILL.get(c, 'NULL')} AS {c}" for c in cols]
            # SYNTHETIC: live-sim rows; INCLUDE_SYNTHETIC=0 removes this branch
            sql += f" UNION ALL SELECT {', '.join(sim_cols)} FROM {self.sim_prefix}{twin}{w}"
        return f"({sql})"

    def data_label(self, has_real_rows: bool) -> str:
        if not self.synthetic_on:
            return "real"
        return "mixed" if has_real_rows else "synthetic"
