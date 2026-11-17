"""Single source of colours, buckets and labels for the Tableau sheets and the stand-in PNG.

BUILD_TABLEAU.md copies these hex codes; change them here first.
Palette steps come from the dataviz reference palette (blue ramp, orange ramp, neutral inks).
"""

# Surfaces and inks
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"

# Complaint buckets (311 noise complaints). Neutral grey for 0, one orange hue light->dark.
COMPLAINT_BUCKETS = ["0", "1-2", "3-9", "10-49", "50+"]
COMPLAINT_EDGES = [0, 1, 3, 10, 50]  # lower bound of each bucket
COMPLAINT_COLORS = {
    "0": "#d4d3cd",
    "1-2": "#f3d9cc",
    "3-9": "#eb8a62",
    "10-49": "#d95926",
    "50+": "#9c3a14",
}
COMPLAINT_CAPTION = "311 noise complaints = complaint risk, not nightlife quality."

# Health grades (DOHMH). "Not matched" = no DOHMH record; shown, never dropped.
GRADE_ORDER = ["A", "B", "C", "N", "Z", "Not matched"]
GRADE_COLORS = {
    "A": "#1baf7a",
    "B": "#eda100",
    "C": "#eb6834",
    "N": "#898781",
    "Z": "#52514e",
    "Not matched": "#e1e0d9",
}

# Neighbourhood highlight (LES launch area)
HIGHLIGHT_HOODS = ["LES/Chinatown"]
HIGHLIGHT = "#2a78d6"
OTHER = "#c3c2b7"

# Tonight heatmap: continuous 0-100 sequential blue, legend ticks at the v2.2 band edges.
VIBE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
VIBE_TICKS = [0, 35, 65, 100]
VIBE_BANDS = [(0, 34, "Chill"), (35, 64, "Lively"), (65, 100, "Packed")]
LOW_CONF = "#c3c2b7"   # display = low (conf 0.20-0.39), hatched grey
NO_DATA = "#f0efec"    # display = none ("No fresh reports")
NOW_LINE = "#e34948"   # 23:30 DEMO_NOW outline

# Synthetic badge
DEMO_BADGE = "#6250d6"
DEMO_LABEL = "DEMO DATA (synthetic)"


def complaint_bucket(n):
    """Return the bucket label for a complaint count, or None when unknown."""
    if n is None or n != n:  # None or NaN
        return None
    label = COMPLAINT_BUCKETS[0]
    for edge, name in zip(COMPLAINT_EDGES, COMPLAINT_BUCKETS):
        if n >= edge:
            label = name
    return label


def vibe_band(v):
    """v2.2 §J vibe label band, None for null vibe."""
    if v is None or v != v:
        return None
    for lo, hi, name in VIBE_BANDS:
        if v <= hi:
            return name
    return "Packed"


def display_for(confidence, vibe):
    """v2 §A display threshold: show / low / none."""
    if vibe is None or vibe != vibe or confidence is None or confidence != confidence:
        return "none"
    if confidence >= 0.40:
        return "show"
    if confidence >= 0.20:
        return "low"
    return "none"
