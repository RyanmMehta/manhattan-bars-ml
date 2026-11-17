"""Render the 5-panel stand-in dashboard (PNG + PDF) from the CSV extracts.

    python -I analytics/tableau/render_standin.py [--extracts ...] [--synthetic-dir ...] [--out ...]

Mirrors Tableau sheets S1-S5 (OUTLINE §4) with the colours in style.py.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import style  # noqa: E402

MANHATTAN_LON = (-74.03, -73.90)  # map window; a few geocodes fall outside Manhattan
MANHATTAN_LAT = (40.695, 40.885)
ASPECT = 1 / math.cos(math.radians(40.75))
VIBE_CMAP = LinearSegmentedColormap.from_list("vibe", style.VIBE_RAMP)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": style.GRID,
    "axes.labelcolor": style.INK_2, "xtick.color": style.MUTED, "ytick.color": style.INK_2,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlecolor": style.INK,
    "axes.titlelocation": "left", "figure.facecolor": style.SURFACE, "axes.facecolor": style.SURFACE,
})


def short(name: str, n: int = 24) -> str:
    """Title-case venue name, legal suffixes dropped, truncated."""
    s = str(name).title()
    s = re.sub(r"\s+(Llc|Inc|Corp|Ltd|Co)\.?$", "", s).replace("'S ", "'s ").replace("'S", "'s")
    return s if len(s) <= n else s[: n - 1] + "…"


def badge(ax, text=style.DEMO_LABEL, y=1.02):
    """Visible demo-data badge in the panel's top-right corner."""
    ax.text(1.0, y, text, transform=ax.transAxes, ha="right", va="bottom", fontsize=11,
            fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.35", fc=style.DEMO_BADGE, ec="none"))


def caption(ax, text, y=-0.06):
    ax.text(0, y, text, transform=ax.transAxes, ha="left", va="top", fontsize=10, color=style.INK_2,
            style="italic")


def clean(ax, grid_axis=None):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=style.GRID, lw=0.8)
        ax.set_axisbelow(True)


def panel_map(ax, bars):
    """S1: every bar coloured by complaint bucket, sized by log complaints."""
    b = bars[bars.has_coords == 1]
    for bucket in style.COMPLAINT_BUCKETS:
        s = b[b.complaint_bucket == bucket]
        ax.scatter(s.lon, s.lat, s=6 + 10 * np.log1p(s.noise_complaints), c=style.COMPLAINT_COLORS[bucket],
                   edgecolors=style.SURFACE, linewidths=0.4, label=f"{bucket} ({len(s)})", zorder=2)
    ax.set_xlim(*MANHATTAN_LON), ax.set_ylim(*MANHATTAN_LAT)
    ax.set_aspect(ASPECT)
    ax.set_xticks([]), ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f"S1  Manhattan's {len(bars):,} licensed bars")
    ax.legend(title="311 noise complaints", loc="upper left", frameon=False, fontsize=9, title_fontsize=10)
    outside = ((b.lon < MANHATTAN_LON[0]) | (b.lon > MANHATTAN_LON[1]) |
               (b.lat < MANHATTAN_LAT[0]) | (b.lat > MANHATTAN_LAT[1])).sum()
    caption(ax, style.COMPLAINT_CAPTION + f"\n{(bars.has_coords == 0).sum()} bars without coordinates and "
            f"{outside} geocoded outside the map window not shown.", y=0.0)


def panel_density(ax, hoods):
    """S2: bar count per neighbourhood, LES highlighted, complaints/bar labelled."""
    h = hoods.sort_values("n_bars")
    colors = [style.HIGHLIGHT if n in style.HIGHLIGHT_HOODS else style.OTHER for n in h.neighborhood]
    ax.barh(h.neighborhood, h.n_bars, color=colors, height=0.7, edgecolor=style.SURFACE, linewidth=2)
    for y, (n, cpb) in enumerate(zip(h.n_bars, h.complaints_per_bar)):
        ax.text(n + 4, y, f"{n}  ·  {cpb:.1f} complaints/bar", va="center", fontsize=9, color=style.INK_2)
    ax.set_xlim(0, h.n_bars.max() * 1.55)
    ax.set_xlabel("Licensed bars")
    clean(ax, "x")
    ax.tick_params(axis="y", length=0)
    ax.set_title("S2  Bars per neighbourhood (LES/Chinatown in blue)")
    caption(ax, "Neighbourhood = zip-code grouping. " + style.COMPLAINT_CAPTION, y=-0.09)


def panel_grades(ax, grades, hoods):
    """S3: 100% stacked bar of latest DOHMH grade per neighbourhood."""
    order = hoods.sort_values("n_bars").neighborhood.tolist()
    p = grades.pivot(index="neighborhood", columns="latest_grade", values="pct").reindex(order)
    left = np.zeros(len(p))
    for g in style.GRADE_ORDER:
        vals = p[g].to_numpy()
        ax.barh(p.index, vals, left=left, color=style.GRADE_COLORS[g], height=0.7, label=g,
                edgecolor=style.SURFACE, linewidth=1)
        left += vals
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of bars")
    clean(ax)
    ax.tick_params(axis="y", length=0)
    ax.legend(ncol=6, loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=9,
              handlelength=1, columnspacing=1)
    ax.set_title("S3  Health grade mix by neighbourhood", pad=28)
    nm = grades[grades.latest_grade == "Not matched"].n.sum() / grades.n.sum() * 100
    caption(ax, f"'Not matched' = no DOHMH inspection match ({nm:.0f}% of bars), shown not dropped.", y=-0.09)


def panel_les(ax, bars, launch):
    """S4: zip 10002 bars faded, the 35 launch venues marked and labelled."""
    z = bars[(bars.zip == "10002") & (bars.has_coords == 1)]
    other = z[z.is_launch == 0]
    ax.scatter(other.lon, other.lat, s=22, c=style.OTHER, edgecolors=style.SURFACE, linewidths=0.5,
               label=f"Other 10002 bars ({len(other)})")
    ax.scatter(launch.lon, launch.lat, s=60, c=style.HIGHLIGHT, edgecolors=style.SURFACE, linewidths=1.2,
               label=f"Launch venues ({len(launch)})", zorder=3)
    for _, r in launch.iterrows():
        ax.annotate(short(r["name"], 18), (r.lon, r.lat), xytext=(4, 3), textcoords="offset points",
                    fontsize=7.5, color=style.INK)
    ax.set_aspect(ASPECT)
    ax.set_xticks([]), ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(style.GRID)
    ax.legend(loc="lower left", frameon=True, facecolor=style.SURFACE, edgecolor=style.GRID, fontsize=9)
    ax.set_title("S4  Lower East Side (zip 10002): launch area")
    caption(ax, "Full table of the 35 launch venues: extracts/launch_venues.csv (Tableau S4 table).", y=-0.02)


def panel_tonight(ax, heat, cax):
    """S5: launch venue x hour heatmap of synthetic vibe_score (HH:30 snapshots)."""
    hours = heat.drop_duplicates("hour_order").sort_values("hour_order")
    peak = heat.groupby("venue_id")["vibe_score"].max().fillna(-1)
    names = heat.drop_duplicates("venue_id").set_index("venue_id")["name"]
    venues = peak.sort_values(ascending=False, kind="stable").index.tolist()
    ncol = len(hours)
    for i, vid in enumerate(venues):
        rows = heat[heat.venue_id == vid].set_index("hour_order")
        for j in range(ncol):
            r = rows.loc[j]
            if r.display == "show":
                fc, hatch = VIBE_CMAP(r.vibe_score / 100), None
            elif r.display == "low":
                fc, hatch = style.LOW_CONF, "///"
            else:
                fc, hatch = style.NO_DATA, None
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=fc, edgecolor=style.SURFACE, lw=1.5,
                                   hatch=hatch))
            if r.display in ("show", "low"):
                dark = r.display == "show" and r.vibe_score >= 50
                ax.text(j + 0.5, i + 0.5, f"{int(r.vibe_score)}", ha="center", va="center", fontsize=7.5,
                        color="white" if dark else style.INK_2)
    now_j = int(hours[hours.hour == 23].hour_order.iloc[0])
    ax.add_patch(Rectangle((now_j, 0), 1, len(venues), fill=False, edgecolor=style.NOW_LINE, lw=2.5,
                           zorder=5))
    ax.text(now_j + 0.5, len(venues) + 0.15, "now 23:30", ha="center", va="top", color=style.NOW_LINE,
            fontweight="bold", fontsize=10)
    ax.set_xlim(0, ncol), ax.set_ylim(len(venues), 0)
    ax.set_xticks(np.arange(ncol) + 0.5)
    ax.set_xticklabels([f"{h}\n({lbl[:-2]}:30)" for h, lbl in zip(hours.hour_label, hours.hour_label)],
                       fontsize=9)
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(venues)) + 0.5)
    ax.set_yticklabels([short(names[v], 26) for v in venues], fontsize=8)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    src = heat.source.iloc[0]
    ax.set_title("S5  Tonight (Sat Nov 14): vibe by hour", pad=48)
    ax.text(1.0, 1.075, f"source: {src}", transform=ax.transAxes, ha="right", va="bottom", fontsize=9,
            color=style.INK_2)
    badge(ax, y=1.11)
    # legend: colour bar + state swatches
    sm = plt.cm.ScalarMappable(cmap=VIBE_CMAP, norm=plt.Normalize(0, 100))
    cb = plt.colorbar(sm, cax=cax, orientation="horizontal", ticks=style.VIBE_TICKS)
    cb.outline.set_visible(False)
    cb.set_label("vibe_score (0-34 Chill · 35-64 Lively · 65-100 Packed), confidence ≥ 0.40", fontsize=9)
    cax.legend(handles=[Patch(fc=style.LOW_CONF, hatch="///", ec=style.SURFACE, label="low confidence (0.20-0.39)"),
                        Patch(fc=style.NO_DATA, ec=style.GRID, label="No fresh reports"),
                        Line2D([], [], color=style.NOW_LINE, lw=2.5, label="DEMO_NOW 23:30")],
               loc="upper left", bbox_to_anchor=(0, -3.2), ncol=3, frameon=False, fontsize=9)


def render(extracts: Path, synthetic_dir: Path, out: Path) -> Path:
    bars = pd.read_csv(extracts / "bars.csv", dtype={"zip": str})
    hoods = pd.read_csv(extracts / "neighborhood_summary.csv")
    grades = pd.read_csv(extracts / "grade_by_neighborhood.csv")
    launch = pd.read_csv(extracts / "launch_venues.csv")
    # SYNTHETIC: tonight heatmap extract (SYN-T2); real = GET /api/heatmap?by=hour
    heat = pd.read_csv(synthetic_dir / "syn_tonight_heatmap.csv")

    fig = plt.figure(figsize=(24, 16), dpi=150)
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.08], width_ratios=[0.8, 1.1, 1.1],
                          left=0.03, right=0.985, top=0.9, bottom=0.05, hspace=0.32, wspace=0.42)
    panel_map(fig.add_subplot(gs[:, 0]), bars)
    panel_density(fig.add_subplot(gs[0, 1]), hoods)
    panel_grades(fig.add_subplot(gs[0, 2]), grades, hoods)
    panel_les(fig.add_subplot(gs[1, 1]), bars, launch)
    sub = gs[1, 2].subgridspec(2, 1, height_ratios=[1, 0.025], hspace=0.06)
    panel_tonight(fig.add_subplot(sub[0]), heat, fig.add_subplot(sub[1]))

    fig.text(0.03, 0.965, "Nightlife Autopilot: where Manhattan drinks, and why we launch on the Lower East Side",
             fontsize=24, fontweight="bold", color=style.INK)
    fig.text(0.03, 0.948,  "Public data: NY SLA liquor licences, NYC DOHMH inspections, NYC 311 noise complaints, "
             "OpenStreetMap (data/manhattan_bars.db).\nPanel S5 only is synthetic demo data (live-sim / SYN-T1 "
             "placeholder), cell HH = HH:30 Live Venue State.  Stand-in for the Tableau Public dashboard.",
             fontsize=12, color=style.INK_2, va="top")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=style.SURFACE)
    fig.savefig(out.with_suffix(".pdf"), facecolor=style.SURFACE)
    plt.close(fig)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--extracts", type=Path, default=HERE / "extracts")
    p.add_argument("--synthetic-dir", type=Path, default=None, help="default: <extracts>/synthetic")
    p.add_argument("--out", type=Path, default=HERE / "dashboard_standin.png")
    a = p.parse_args(argv)
    path = render(a.extracts, a.synthetic_dir or a.extracts / "synthetic", a.out)
    print(f"wrote {path} and {path.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
