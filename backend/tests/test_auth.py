from tests.conftest import VENUE, login


def test_login_roles(client):
    u = login(client, "user")
    assert u["user_id"] and u["scout_id"] is None
    s = login(client, "scout")
    assert s["scout_id"] and len(s["token"]) >= 40
    o = login(client, "owner", VENUE)
    assert o["venue_id"] == VENUE


def test_second_owner_login_same_identity(client):
    a = login(client, "owner", VENUE)
    b = login(client, "owner", VENUE)
    assert a["venue_id"] == b["venue_id"] and a["token"] != b["token"]
    r = client.get(f"/api/owner/{VENUE}/dashboard", headers=a["headers"])
    assert r.status_code == 200  # first token still valid


def test_owner_needs_launch_venue(client):
    r = client.post("/api/auth/demo-login", json={"display_name": "x", "role": "owner"})
    assert r.status_code == 422
    r = client.post(
        "/api/auth/demo-login", json={"display_name": "x", "role": "owner", "venue_id": "nope"}
    )
    assert r.status_code == 422


def test_bad_role_422(client):
    r = client.post("/api/auth/demo-login", json={"display_name": "x", "role": "god"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_demo_auth_off_404(make_client):
    c = make_client(demo_auth=False)
    r = c.post("/api/auth/demo-login", json={"display_name": "x", "role": "scout"})
    assert r.status_code == 404


def test_tokens_hashed(client):
    from sqlalchemy import text

    s = login(client, "scout")
    with client.app.state.ctx.db.engine.connect() as c:
        hashes = [r[0] for r in c.execute(text("SELECT token_hash FROM api_tokens"))]
    assert s["token"] not in hashes and len(hashes[0]) == 64


def test_missing_and_bad_token_401(client):
    body = {"venue_id": VENUE, "crowd": 3, "dancing": 1, "line_minutes": 5}
    assert client.post("/api/reports", json=body).status_code == 401
    r = client.post("/api/reports", json=body, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


def test_admin_token(client):
    r = client.get(f"/api/owner/{VENUE}/dashboard", headers={"Authorization": "Bearer test-admin"})
    assert r.status_code == 200
