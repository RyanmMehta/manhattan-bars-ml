def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    b = r.json()
    assert b["ok"] is True and b["recs"] == "stub" and b["data"] == "synthetic"
    assert b["demo_now"] == "2026-11-14T23:30:00-05:00"


def test_health_real_when_synthetic_off(make_client):
    b = make_client(include_synthetic=False).get("/api/health").json()
    assert b["data"] == "real" and b["is_synthetic"] is False


def test_health_mixed_after_real_write(client):
    from tests.conftest import login

    login(client, "scout")
    assert client.get("/api/health").json()["data"] == "mixed"


def test_openapi_and_docs(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/api/docs").status_code == 200


def test_error_envelope_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_cors(client):
    r = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
