from tests.conftest import VENUE, login

NOW = "2026-11-14T23:30:00-05:00"


def test_dashboard(client):
    o = login(client, "owner", VENUE)
    r = client.get(f"/api/owner/{VENUE}/dashboard?now={NOW}", headers=o["headers"])
    assert r.status_code == 200
    b = r.json()
    assert set(b) == {
        "venue_id",
        "views",
        "taps",
        "saves",
        "reports_tonight",
        "rec_appearances",
        "demand_by_hour",
        "is_synthetic",
    }
    assert b["is_synthetic"] is True and b["reports_tonight"] > 0
    assert [h["hour"] for h in b["demand_by_hour"]] == [18, 19, 20, 21, 22, 23]


def test_dashboard_counts_real_views(client):
    o = login(client, "owner", VENUE)
    url = f"/api/owner/{VENUE}/dashboard?now={NOW}"
    before = client.get(url, headers=o["headers"]).json()["views"]
    client.get(f"/api/venues/{VENUE}")
    assert client.get(url, headers=o["headers"]).json()["views"] == before + 1


def test_dashboard_auth(client):
    assert client.get(f"/api/owner/{VENUE}/dashboard").status_code == 401
    other = login(client, "owner", "0370-23-139405")
    assert client.get(f"/api/owner/{VENUE}/dashboard", headers=other["headers"]).status_code == 403
    sc = login(client, "scout")
    assert client.get(f"/api/owner/{VENUE}/dashboard", headers=sc["headers"]).status_code == 403
    assert client.get("/api/owner/nope/dashboard", headers=sc["headers"]).status_code == 404


def test_update_shows_in_offers_and_state(client):
    o = login(client, "owner", VENUE)
    r = client.post(
        f"/api/owner/{VENUE}/updates?now={NOW}",
        headers=o["headers"],
        json={
            "cover_usd": 0,
            "dj": "DJ Test",
            "genres": ["house"],
            "offer": "Free entry before 1",
            "offer_expires_at": "2026-11-15T01:00:00-05:00",
        },
    )
    assert r.status_code == 201
    u = r.json()
    assert u["genres"] == "house" and u["ts"] == NOW and u["is_synthetic"] is False
    d = client.get(f"/api/venues/{VENUE}?now={NOW}").json()
    assert u["update_id"] in {x["update_id"] for x in d["offers"]}
    assert "venue_update" in d["state"]["sources"]
    later = client.get(f"/api/venues/{VENUE}?now=2026-11-15T01:30:00-05:00").json()
    assert u["update_id"] not in {x["update_id"] for x in later["offers"]}


def test_update_validation_and_auth(client):
    o = login(client, "owner", VENUE)
    h = o["headers"]
    url = f"/api/owner/{VENUE}/updates"
    assert client.post(url, headers=h, json={"genres": ["polka"]}).status_code == 422
    assert (
        client.post(url, headers=h, json={"offer": "x", "offer_expires_at": "soon"}).status_code
        == 422
    )
    assert client.post(url, json={"dj": "x"}).status_code == 401
    other = login(client, "owner", "0370-23-139405")
    assert client.post(url, headers=other["headers"], json={"dj": "x"}).status_code == 403
    r = client.post(url, headers=h, json={"offer": "2 for 1"})
    assert r.status_code == 201 and r.json()["offer_expires_at"]
