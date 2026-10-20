"""Build the SQLite database data/manhattan_bars.db from data/raw/.

Tables
  sla_licenses     every active NY SLA license in Manhattan (raw, flattened)
  inspections      every DOHMH inspection/violation row in Manhattan (raw)
  complaints_311   311 noise complaints at Club/Bar/Restaurant locations (raw)
  osm_venues       OpenStreetMap bars, pubs, nightclubs, beer gardens
  venues           one row per on-premises drinking venue, with the matched
                   DOHMH establishment (camis) and OSM node
  venue_features   ML-ready table: one row per venue, features + targets
View
  v_bars           venues that are bars in the narrow sense (bar/tavern, club,
                   nightlife license, or tagged as a bar/pub/nightclub in OSM)

Usage:  python -I src/build_db.py
"""
import difflib
import gzip
import json
import pathlib
import re
import sqlite3

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "manhattan_bars.db"
EARTH_M = 6_371_000

# SLA license classes that allow drinking on the premises, grouped by venue type.
# "Additional bar" licenses (0422/0423/0426) are extra counters inside a parent
# venue; they become the n_additional_bars feature instead of separate venues.
VENUE_TYPE = {
    "0370": "Bar/Tavern", "0267": "Bar/Tavern", "0138": "Bar/Tavern",
    "0371": "Bar/Tavern", "0372": "Bar/Tavern", "0268": "Bar/Tavern",
    "0340": "Restaurant", "0240": "Restaurant", "0341": "Restaurant",
    "0416": "Restaurant",
    "0349": "Club", "0249": "Club",
    "0417": "Nightlife", "0415": "Nightlife",
    "0343": "Hotel", "0243": "Hotel",
    "0373": "Venue/Theatre", "0409": "Venue/Theatre",
}
BEER_WINE_ONLY = {"0240", "0267", "0138", "0243", "0249", "0268"}
ADDITIONAL_BAR = {"0422", "0423", "0426"}
PEST_CODES = {"04K", "04L", "04M", "04N", "08A"}  # rats, mice, roaches, flies, conducive conditions

NEIGHBORHOOD = {
    "Financial District": "10004 10005 10006 10038 10041 10045 10280 10281 10282",
    "Tribeca/SoHo": "10007 10012 10013",
    "LES/Chinatown": "10002",
    "East Village": "10003 10009",
    "West Village": "10014",
    "Chelsea": "10001 10011",
    "Flatiron/Gramercy": "10010",
    "Midtown West": "10018 10019 10036 10020 10119 10121 10123",
    "Midtown East/Murray Hill": "10016 10017 10022 10152 10153 10154 10165 10166 10167 10168 10169 10170 10171 10172 10173 10174 10177",
    "Upper West Side": "10023 10024 10025 10069",
    "Upper East Side": "10021 10028 10065 10075 10128 10162 10044",
    "Harlem": "10026 10027 10030 10037 10039 10031",
    "East Harlem": "10029 10035",
    "Washington Heights/Inwood": "10032 10033 10034 10040",
}
ZIP_TO_HOOD = {z: hood for hood, zips in NEIGHBORHOOD.items() for z in zips.split()}

# ---------------------------------------------------------------- normalisers
ORDINAL_WORDS = {"FIRST": "1", "SECOND": "2", "THIRD": "3", "FOURTH": "4", "FIFTH": "5",
                 "SIXTH": "6", "SEVENTH": "7", "EIGHTH": "8", "NINTH": "9", "TENTH": "10",
                 "ELEVENTH": "11", "TWELFTH": "12"}
STREET_WORDS = {"STREET": "ST", "STR": "ST", "AVENUE": "AVE", "AV": "AVE", "BOULEVARD": "BLVD",
                "PLACE": "PL", "ROAD": "RD", "DRIVE": "DR", "LANE": "LN", "SQUARE": "SQ",
                "PLAZA": "PLZ", "PARKWAY": "PKWY", "TERRACE": "TER", "WEST": "W", "EAST": "E",
                "NORTH": "N", "SOUTH": "S", "SAINT": "ST", "FREDERICK": "FREDERICK",
                "AMERICAS": "6", "OF": ""}
UNIT_RE = re.compile(r"\b(FL|FLR|FLOOR|STE|SUITE|UNIT|APT|RM|ROOM|BSMT|BASEMENT|STORE|"
                     r"GROUND|GRD|LOBBY|LEVEL|SPACE|PH|CELLAR|MEZZ|MEZZANINE|FRNT|FRONT|REAR)\b.*$")


def norm_addr(addr):
    if not isinstance(addr, str):
        return ""
    s = re.split(r",| AKA ", addr.upper())[0]
    s = s.replace("#", " UNIT ")
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"^(\d+)[A-Z]?-\d+[A-Z]?\b", r"\1", s.strip())   # 1-3 Main St -> 1 Main St
    m = re.match(r"^(\d+) (\d+) ", s)                           # 501 503 Columbus -> 501 Columbus
    if m and 0 < int(m[2]) - int(m[1]) <= 30 and int(m[1]) % 2 == int(m[2]) % 2:
        s = m[1] + s[m.end(2):]
    s = re.sub(r"\b(\d+)(ST|ND|RD|TH)\b", r"\1", s)              # 14th -> 14
    s = UNIT_RE.sub("", s)
    words = []
    for w in s.split():
        w = ORDINAL_WORDS.get(w, w)
        w = STREET_WORDS.get(w, w)
        if w:
            words.append(w)
    return " ".join(words)


NAME_STOP = re.compile(r"\b(LLC|INC|CORP|CORPORATION|CO|LTD|LP|THE|NYC|NY|RESTAURANT|REST|BAR|"
                       r"LOUNGE|GRILL|CAFE|AND|OF|GROUP|HOLDINGS|HOSPITALITY|ENTERPRISES|D/B/A|DBA)\b")


def norm_name(name):
    if not isinstance(name, str):
        return ""
    s = re.sub(r"[{}\"'.,&!()\-/]", " ", name.upper())
    s = NAME_STOP.sub(" ", s)
    return " ".join(s.split())


def name_sim(a, b):
    a, b = norm_name(a), norm_name(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def balltree(lat, lon):
    return BallTree(np.radians(np.c_[lat, lon]), metric="haversine")


def closes_late(hours):
    """True if an OSM opening_hours string closes at/after 2am or is 24/7."""
    if not isinstance(hours, str):
        return np.nan
    if "24/7" in hours:
        return 1
    for start, end in re.findall(r"(\d{1,2}):\d{2}\s*-\s*(\d{1,2}):\d{2}", hours):
        start, end = int(start), int(end)
        if (end < start and 2 <= end <= 8) or end >= 26:
            return 1
    return 0


# ---------------------------------------------------------------- loaders
def read_raw(name):
    with gzip.open(RAW / f"{name}.json.gz", "rt") as fh:
        return json.load(fh)


def load_sla():
    df = pd.DataFrame(read_raw("sla_licenses"))
    geo = df.pop("georeference")
    df["lon"] = [g["coordinates"][0] if isinstance(g, dict) else np.nan for g in geo]
    df["lat"] = [g["coordinates"][1] if isinstance(g, dict) else np.nan for g in geo]
    df = df.drop(columns=[c for c in df.columns if c.startswith(":@")])
    df["dba"] = df["dba"].str.strip("{}")
    for c in ["originalissuedate", "lastissuedate", "effectivedate", "expirationdate"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["zipcode"] = df["zipcode"].astype(str).str[:5]
    return df


def load_inspections():
    df = pd.DataFrame(read_raw("dohmh_inspections"))
    df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    for c in ["latitude", "longitude"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").replace(0, np.nan)
    df["zipcode"] = df["zipcode"].astype(str).str[:5]
    return df


def load_311():
    df = pd.DataFrame(read_raw("nyc311_complaints"))
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    for c in ["latitude", "longitude"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["incident_zip"] = df["incident_zip"].astype(str).str[:5]
    return df


def load_osm():
    rows = []
    for e in read_raw("osm_bars"):
        t = e.get("tags", {})
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        rows.append({
            "osm_id": f"{e['type']}/{e['id']}", "name": t.get("name"), "amenity": t.get("amenity"),
            "lat": lat, "lon": lon,
            "addr": f"{t.get('addr:housenumber', '')} {t.get('addr:street', '')}".strip(),
            "postcode": t.get("addr:postcode"), "opening_hours": t.get("opening_hours"),
            "outdoor_seating": t.get("outdoor_seating"), "website": t.get("website") or t.get("contact:website"),
            "sport": t.get("sport"), "cocktails": t.get("cocktails"), "happy_hours": t.get("happy_hours"),
            "tags_json": json.dumps(t),
        })
    return pd.DataFrame(rows).dropna(subset=["lat", "lon"])


# ---------------------------------------------------------------- build
def per_establishment(insp):
    """Aggregate DOHMH violation rows to one row per establishment (camis)."""
    real = insp[insp["inspection_date"].dt.year > 1900]
    visits = real.drop_duplicates(["camis", "inspection_date"])
    latest = visits.sort_values("inspection_date").groupby("camis").tail(1).set_index("camis")
    graded = real.dropna(subset=["grade"]).sort_values("inspection_date").groupby("camis").tail(1)
    g = real.groupby("camis")
    est = pd.DataFrame({
        "n_inspections": visits.groupby("camis").size(),
        "mean_score": visits.groupby("camis")["score"].mean(),
        "max_score": visits.groupby("camis")["score"].max(),
        "n_violations": g["violation_code"].count(),
        "n_critical_violations": g["critical_flag"].apply(lambda s: (s == "Critical").sum()),
        "has_pest_violation": g["violation_code"].apply(lambda s: int(s.isin(PEST_CODES).any())),
        "last_inspection": latest["inspection_date"],
    })
    est["latest_grade"] = graded.set_index("camis")["grade"]
    base = insp.drop_duplicates("camis").set_index("camis")[
        ["dba", "building", "street", "zipcode", "cuisine_description", "latitude", "longitude", "nta"]]
    est = base.join(est, how="left")
    est["addr_key"] = (est["building"].fillna("") + " " + est["street"].fillna("")).map(norm_addr) + "|" + est["zipcode"]
    return est.reset_index()


def match_dohmh(venues, est):
    """Match each venue to a DOHMH establishment: same address + best name, else nearby + name."""
    by_key = est.groupby("addr_key").indices
    geo = est.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    tree = balltree(geo["latitude"], geo["longitude"])
    camis, how = [], []
    for v in venues.itertuples():
        best, best_sim, method = None, 0.0, None
        idx = by_key.get(v.addr_key, [])
        for i in idx:
            sim = max(name_sim(v.name, est.at[i, "dba"]), name_sim(v.legal_name, est.at[i, "dba"]))
            if sim > best_sim:
                best, best_sim = est.at[i, "camis"], sim
        if best is not None and (best_sim >= 0.5 or len(idx) == 1):
            method = "address"
        elif not np.isnan(v.lat):
            best, best_sim = None, 0.0
            near = tree.query_radius(np.radians([[v.lat, v.lon]]), r=60 / EARTH_M)[0]
            for j in near:
                sim = max(name_sim(v.name, geo.at[j, "dba"]), name_sim(v.legal_name, geo.at[j, "dba"]))
                if sim > best_sim:
                    best, best_sim = geo.at[j, "camis"], sim
            method = "nearby+name" if best_sim >= 0.75 else None
        camis.append(best if method else None)
        how.append(method)
    return camis, how


def match_osm(venues, osm):
    tree = balltree(osm["lat"], osm["lon"])
    ok = venues["lat"].notna()
    ids, how = [None] * len(venues), [None] * len(venues)
    pts = np.radians(venues.loc[ok, ["lat", "lon"]].to_numpy())
    neigh, dist = tree.query_radius(pts, r=60 / EARTH_M, return_distance=True)
    for row, cand, d in zip(np.flatnonzero(ok), neigh, dist):
        v = venues.iloc[row]
        best, score = None, 0.0
        for j, dj in zip(cand, d * EARTH_M):
            sim = max(name_sim(v["name"], osm.iat[j, 1]), name_sim(v["legal_name"], osm.iat[j, 1]))
            if sim >= 0.6 and sim - dj / 600 > score:
                best, score = j, sim - dj / 600
        if best is not None:
            ids[row], how[row] = osm.iat[best, 0], "nearby+name"
    return ids, how


def build_venues(sla, est, osm, complaints):
    on_prem = sla[sla["class"].isin(VENUE_TYPE)].copy()
    extra = sla[sla["class"].isin(ADDITIONAL_BAR)].groupby("parentlicenseid").size()
    v = pd.DataFrame({
        "license_id": on_prem["licensepermitid"],
        "name": on_prem["dba"].fillna(on_prem["legalname"]),
        "legal_name": on_prem["legalname"],
        "address": on_prem["actualaddressofpremises"],
        "zip": on_prem["zipcode"],
        "lat": on_prem["lat"], "lon": on_prem["lon"],
        "license_class": on_prem["class"],
        "license_description": on_prem["description"],
        "venue_type": on_prem["class"].map(VENUE_TYPE),
        "liquor_tier": np.where(on_prem["class"].isin(BEER_WINE_ONLY), "beer_wine", "full_liquor"),
        "original_issue_date": on_prem["originalissuedate"],
        "expiration_date": on_prem["expirationdate"],
    }).reset_index(drop=True)
    v["n_additional_bars"] = v["license_id"].map(extra).fillna(0).astype(int)
    v["neighborhood"] = v["zip"].map(ZIP_TO_HOOD).fillna("Other Manhattan")
    v["addr_key"] = v["address"].map(norm_addr) + "|" + v["zip"]

    print("  matching venues to DOHMH inspections ...")
    v["camis"], v["dohmh_match"] = match_dohmh(v, est)
    print("  matching venues to OpenStreetMap ...")
    v["osm_id"], v["osm_match"] = match_osm(v, osm)

    # Same licensee + premises listed twice (renewal or transfer still active): keep the oldest.
    v["_dedup"] = v["name"].map(norm_name) + "|" + v["addr_key"]
    v = (v.sort_values("original_issue_date").drop_duplicates("_dedup")
         .drop(columns="_dedup").reset_index(drop=True))

    # 311 noise complaints: same normalised address; otherwise the nearest complaint
    # address within 30 m that has the same house number (catches street-name
    # spelling differences without taking a neighbour's or a whole block's complaints).
    complaints = complaints.copy()
    complaints["addr_key"] = complaints["incident_address"].map(norm_addr) + "|" + complaints["incident_zip"]
    by_addr = complaints.groupby("addr_key").agg(
        n=("unique_key", "size"), lat=("latitude", "median"), lon=("longitude", "median")).dropna()
    house = by_addr.index.str.split(" ").str[0].to_numpy()
    v["noise_complaints"] = v["addr_key"].map(by_addr["n"])
    v["complaint_match"] = np.where(v["noise_complaints"].notna(), "address", None)
    tree = balltree(by_addr["lat"], by_addr["lon"])
    miss = np.flatnonzero(v["noise_complaints"].isna() & v["lat"].notna())
    near = tree.query_radius(np.radians(v.loc[miss, ["lat", "lon"]].to_numpy()), r=30 / EARTH_M,
                             return_distance=True, sort_results=True)
    for row, cand in zip(miss, near[0]):
        num = v.at[row, "addr_key"].split(" ")[0]
        same = [j for j in cand if house[j] == num]
        if same:
            v.at[row, "noise_complaints"] = by_addr["n"].iat[same[0]]
            v.at[row, "complaint_match"] = "same_number_within_30m"
    v["noise_complaints"] = v["noise_complaints"].fillna(0).astype(int)

    # Density of other on-premises venues nearby.
    ok = v["lat"].notna()
    t = balltree(v.loc[ok, "lat"], v.loc[ok, "lon"])
    pts = np.radians(v.loc[ok, ["lat", "lon"]].to_numpy())
    for r in (100, 250):
        v.loc[ok, f"density_{r}m"] = t.query_radius(pts, r=r / EARTH_M, count_only=True) - 1
    return v


def build_features(v, est, osm, scraped_at):
    f = v.merge(est.drop(columns=["addr_key"]).add_prefix("d_"), left_on="camis", right_on="d_camis", how="left")
    f = f.merge(osm.add_prefix("o_"), left_on="osm_id", right_on="o_osm_id", how="left")
    top_cuisines = est["cuisine_description"].value_counts().head(12).index
    cuisine = f["d_cuisine_description"].where(f["d_cuisine_description"].isin(top_cuisines), "Other")
    out = pd.DataFrame({
        "license_id": f["license_id"],
        # categorical
        "venue_type": f["venue_type"],
        "liquor_tier": f["liquor_tier"],
        "neighborhood": f["neighborhood"],
        "cuisine": cuisine.where(f["camis"].notna(), "Not matched"),
        "latest_grade": f["d_latest_grade"].fillna("None"),
        "osm_amenity": f["o_amenity"].fillna("not_listed"),
        # binary
        "dohmh_matched": f["camis"].notna().astype(int),
        "has_pest_violation": f["d_has_pest_violation"].fillna(0).astype(int),
        "osm_closes_late": f["o_opening_hours"].map(closes_late).fillna(0).astype(int),
        "osm_outdoor_seating": (f["o_outdoor_seating"] == "yes").astype(int),
        "osm_has_website": f["o_website"].notna().astype(int),
        # numeric
        "lat": f["lat"], "lon": f["lon"],
        "years_licensed": ((pd.Timestamp(scraped_at) - f["original_issue_date"]).dt.days / 365.25).round(2),
        "n_additional_bars": f["n_additional_bars"],
        "density_100m": f["density_100m"], "density_250m": f["density_250m"],
        # -1 = no matched inspection record
        "n_inspections": f["d_n_inspections"].fillna(0),
        "mean_score": f["d_mean_score"].round(2).fillna(-1),
        "max_score": f["d_max_score"].fillna(-1),
        "n_violations": f["d_n_violations"].fillna(0),
        "n_critical_violations": f["d_n_critical_violations"].fillna(0),
        # targets
        "noise_complaints": f["noise_complaints"],
    })
    out = out.dropna(subset=["lat", "lon", "years_licensed"])
    threshold = 3
    out["high_noise"] = (out["noise_complaints"] >= threshold).astype(int)
    return out


def main():
    meta = json.loads((RAW / "meta.json").read_text())
    print("loading raw data ...")
    sla, insp, c311, osm = load_sla(), load_inspections(), load_311(), load_osm()
    est = per_establishment(insp)
    print("building venues ...")
    venues = build_venues(sla, est, osm, c311)
    features = build_features(venues, est, osm, meta["scraped_at"])

    DB.unlink(missing_ok=True)
    with sqlite3.connect(DB) as con:
        sla.to_sql("sla_licenses", con, index=False)
        insp.to_sql("inspections", con, index=False)
        c311.to_sql("complaints_311", con, index=False)
        osm.to_sql("osm_venues", con, index=False)
        venues.to_sql("venues", con, index=False)
        features.to_sql("venue_features", con, index=False)
        con.executescript("""
            CREATE INDEX ix_venues_license ON venues(license_id);
            CREATE INDEX ix_insp_camis ON inspections(camis);
            CREATE INDEX ix_feat_license ON venue_features(license_id);
            CREATE VIEW v_bars AS
              SELECT * FROM venues
              WHERE venue_type IN ('Bar/Tavern', 'Club', 'Nightlife')
                 OR osm_id IS NOT NULL;
        """)
        n_bars = con.execute("SELECT COUNT(*) FROM v_bars").fetchone()[0]

    print(f"\nwrote {DB.relative_to(ROOT)}")
    print(f"  venues (on-premises liquor licenses): {len(venues):,}")
    print(f"  of which bars in the narrow sense (v_bars): {n_bars:,}")
    print(f"  matched to DOHMH inspections: {venues['camis'].notna().mean():.1%}")
    print(f"  matched to OpenStreetMap:     {venues['osm_id'].notna().mean():.1%}")
    print(f"  with >=1 noise complaint:     {(venues['noise_complaints'] > 0).mean():.1%}")
    print(f"  venue_features rows: {len(features):,}  high_noise rate: {features['high_noise'].mean():.1%}")
    print(venues["venue_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
