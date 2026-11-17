"""Hit every endpoint of a running backend. `python backend/scripts/smoke.py BASE_URL`.
Exits non-zero on the first failure. Uses only the standard library."""

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
PREFS = {"genres": ["hip-hop", "r&b"], "want_dancing": True, "crowd_pref": 4, "max_cover_usd": 20,
         "max_line_minutes": 15, "max_distance_km": 1.5, "lat": 40.7203, "lon": -73.9881,
         "group_size": 4}


def call(method: str, path: str, body: dict | None = None, token: str | None = None,
         expect: int = 200):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, data = r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        status, data = e.code, json.loads(e.read() or b"null")
    ok = status == expect
    print(f"{'OK ' if ok else 'FAIL'} {method} {path} -> {status}")
    if not ok:
        print(json.dumps(data)[:500])
        raise SystemExit(1)
    return data


def main() -> None:
    h = call("GET", "/api/health")
    assert h["ok"] is True, h
    venues = call("GET", "/api/venues")
    vid = venues[0]["venue_id"]
    other = venues[1]["venue_id"]
    call("GET", f"/api/venues/{vid}")
    call("GET", f"/api/venues/{vid}/state")
    call("POST", "/api/recommend", PREFS)
    call("POST", "/api/plan-night", PREFS | {"n_stops": 3})
    call("GET", "/api/heatmap")
    call("GET", "/api/heatmap?by=hour")
    call("GET", "/api/scouts/leaderboard")
    call("GET", "/api/bounties")
    scout = call("POST", "/api/auth/demo-login", {"display_name": "Smoke Scout", "role": "scout"},
                 expect=201)
    call("POST", "/api/reports", {"venue_id": other, "crowd": 3, "dancing": 1, "line_minutes": 5},
         token=scout["token"], expect=201)
    owner = call("POST", "/api/auth/demo-login",
                 {"display_name": "Smoke Owner", "role": "owner", "venue_id": vid}, expect=201)
    call("GET", f"/api/owner/{vid}/dashboard", token=owner["token"])
    call("POST", f"/api/owner/{vid}/updates", {"dj": "Smoke DJ"}, token=owner["token"], expect=201)
    user = call("POST", "/api/auth/demo-login", {"display_name": "Smoke User", "role": "user"},
                expect=201)
    call("POST", "/api/feedback", {"venue_id": vid, "visited": 1, "rating": 4},
         token=user["token"], expect=201)
    print("smoke: all endpoints OK")


if __name__ == "__main__":
    main()
