"""Scrape public data on Manhattan bars into data/raw/.

Sources (all free, no API key):
  1. NY State Liquor Authority - current active licenses (data.ny.gov 9s3h-dpkz)
  2. NYC DOHMH restaurant/bar inspection results (data.cityofnewyork.us 43nn-pn8j)
  3. NYC 311 noise complaints at Club/Bar/Restaurant locations (erm2-nwe9)
  4. OpenStreetMap bars / pubs / nightclubs / beer gardens (Overpass API)

Usage:  python -I src/scrape.py [--years 3] [--skip-osm]
"""
import argparse
import gzip
import datetime as dt
import json
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "manhattan-bars-research/1.0 (educational ML project)"}

SLA_URL = "https://data.ny.gov/resource/9s3h-dpkz.json"
DOHMH_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"
NYC311_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
# Bounding box around Manhattan (S, W, N, E). Points outside Manhattan are
# dropped later when OSM venues are matched to Manhattan licenses.
MANHATTAN_BBOX = (40.680, -74.030, 40.882, -73.906)


def socrata_all(url, params, page=50000, label=""):
    """Page through a Socrata endpoint and return every row."""
    rows, offset = [], 0
    while True:
        q = dict(params, **{"$limit": page, "$offset": offset, "$order": ":id"})
        for attempt in range(5):
            try:
                r = requests.get(url, params=q, headers=UA, timeout=180)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                wait = 2 ** attempt * 5
                print(f"  {label}: {e} - retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
        else:
            raise RuntimeError(f"{label}: failed after retries")
        batch = r.json()
        rows.extend(batch)
        print(f"  {label}: {len(rows):,} rows")
        if len(batch) < page:
            return rows
        offset += page


def scrape_sla():
    return socrata_all(SLA_URL, {"premisescounty": "New York"}, label="SLA licenses")


def scrape_inspections():
    cols = ("camis,dba,building,street,zipcode,phone,cuisine_description,inspection_date,"
            "action,violation_code,critical_flag,score,grade,inspection_type,latitude,longitude,nta")
    return socrata_all(DOHMH_URL, {"$select": cols, "boro": "Manhattan"}, label="DOHMH inspections")


def scrape_311(years):
    since = (dt.date.today() - dt.timedelta(days=365 * years)).isoformat()
    cols = ("unique_key,created_date,complaint_type,descriptor,incident_address,incident_zip,"
            "latitude,longitude,status")
    where = (f"borough='MANHATTAN' AND location_type='Club/Bar/Restaurant' "
             f"AND created_date >= '{since}'")
    return socrata_all(NYC311_URL, {"$select": cols, "$where": where}, label="311 complaints")


def scrape_osm():
    s, w, n, e = MANHATTAN_BBOX
    query = (f'[out:json][timeout:120];'
             f'(nwr["amenity"~"^(bar|pub|nightclub|biergarten)$"]({s},{w},{n},{e}););'
             f'out center tags;')
    for attempt in range(6):
        url = OVERPASS_MIRRORS[attempt % len(OVERPASS_MIRRORS)]
        try:
            r = requests.post(url, data={"data": query}, headers=UA, timeout=200)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                elements = r.json()["elements"]
                print(f"  OSM: {len(elements):,} venues from {url}")
                return elements
            print(f"  OSM: HTTP {r.status_code} from {url}", file=sys.stderr)
        except requests.RequestException as ex:
            print(f"  OSM: {ex} from {url}", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("Overpass API unavailable - rerun later or use --skip-osm")


def save(name, rows):
    path = RAW / f"{name}.json.gz"
    with gzip.open(path, "wt") as fh:
        json.dump(rows, fh)
    print(f"  saved {path.relative_to(ROOT)} ({path.stat().st_size / 1e6:.1f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=3, help="years of 311 history")
    ap.add_argument("--skip-osm", action="store_true")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    print("[1/4] NY State Liquor Authority")
    save("sla_licenses", scrape_sla())
    print("[2/4] NYC DOHMH inspections")
    save("dohmh_inspections", scrape_inspections())
    print("[3/4] NYC 311 noise complaints")
    save("nyc311_complaints", scrape_311(args.years))
    if not args.skip_osm:
        print("[4/4] OpenStreetMap")
        save("osm_bars", scrape_osm())
    meta = {"scraped_at": dt.datetime.now().isoformat(timespec="seconds"),
            "complaint_years": args.years}
    (RAW / "meta.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
