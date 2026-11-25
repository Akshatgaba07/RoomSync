import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def client():
    from backend.app.db import reset_db
    reset_db()
    from backend.app.main import app
    from backend.scripts.seed_demo import seed
    seed()
    return TestClient(app)

def signup(c, email="new@x.com", pw="supersecret1", name="New Student"):
    r = c.post("/api/auth/signup", json={"email": email, "password": pw, "name": name})
    return r

def auth(c, email="new@x.com"):
    t = c.post("/api/auth/login", json={"email": email, "password": "supersecret1"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}

def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"

def test_signup_login_and_validation(client):
    assert signup(client).status_code == 201
    assert signup(client).status_code == 409
    assert signup(client, "bad", "supersecret1").status_code == 422
    assert signup(client, "b@x.com", "short").status_code == 422
    assert client.post("/api/auth/login", json={"email": "new@x.com", "password": "wrongwrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@x.com", "password": "wrongwrong"}).status_code == 401

def test_password_is_hashed(client):
    from backend.app.db import get_db
    u = get_db().users.find_one({"email": "new@x.com"})
    assert u["password_hash"].startswith("$2") and "supersecret1" not in str(u)

def test_auth_required(client):
    for path in ("/api/me", "/api/matches", "/api/stats"):
        assert client.get(path).status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer junk"}).status_code == 401

def test_questionnaire_public_spec(client):
    q = client.get("/api/questionnaire").json()
    assert len(q["questions"]) == 25 and q["max_priorities"] == 3

def test_incomplete_profile_cannot_match(client, base_answers):
    h = auth(client)
    assert client.get("/api/matches", headers=h).status_code == 409
    r = client.put("/api/profile", headers=h, json={"answers": {"hostel": "Boys hostel", "bedtime": "Before 11 PM"}})
    assert r.status_code == 200 and not r.json()["profile_complete"] and r.json()["completeness"] < 1
    assert client.get("/api/matches", headers=h).status_code == 409

def test_invalid_answers_rejected(client, base_answers):
    h = auth(client)
    assert client.put("/api/profile", headers=h, json={"answers": {"tidiness": 11}}).status_code == 422
    assert client.put("/api/profile", headers=h, json={"answers": {"food": "Pizza"}}).status_code == 422
    assert client.put("/api/profile", headers=h, json={"answers": base_answers, "priorities": ["Sleep schedule"] * 1 + ["Cleanliness", "Food habits", "Sharing and borrowing"]}).status_code == 422

def test_full_flow_matching_is_dynamic(client, base_answers):
    h = auth(client)
    r = client.put("/api/profile", headers=h, json={"answers": base_answers, "priorities": ["Sleep schedule", "Cleanliness"]})
    assert r.json()["profile_complete"]
    m1 = client.get("/api/matches?k=5", headers=h).json()
    assert 0 < len(m1["matches"]) <= 5 and all(x["hostel"] == "Boys hostel" for x in m1["matches"])
    assert [x["rank"] for x in m1["matches"]] == list(range(1, len(m1["matches"]) + 1))
    assert len({x["id"] for x in m1["matches"]}) == len(m1["matches"])
    me = client.get("/api/me", headers=h).json()["id"]
    assert me not in {x["id"] for x in m1["matches"]} and "email" not in m1["matches"][0]
    scores = [x["score"] for x in m1["matches"]]; assert scores == sorted(scores, reverse=True)
    # change preferences -> recommendations recalculated
    changed = {**base_answers, "bedtime": "After 3 AM", "wake": "After 10 AM", "study_env": "Total silence"}
    client.put("/api/profile", headers=h, json={"answers": changed, "priorities": ["Sleep schedule", "Cleanliness"]})
    m2 = client.get("/api/matches?k=5", headers=h).json()
    assert [(x["id"], x["score"]) for x in m1["matches"]] != [(x["id"], x["score"]) for x in m2["matches"]]

def test_dealbreakers_filter_and_detail(client, base_answers):
    h = auth(client)
    client.put("/api/profile", headers=h, json={"answers": base_answers, "priorities": ["Noise and study environment"],
                                                "dealbreakers": ["Plays music or videos on speaker", "Has overnight guests often"]})
    strict = client.get("/api/matches?k=50", headers=h).json()
    loose = client.get("/api/matches?k=50&strict=false", headers=h).json()
    assert strict["excluded_by_dealbreakers"] > 0 and len(loose["matches"]) > len(strict["matches"])
    assert all(not x["blocked"] for x in strict["matches"]) and any(x["blocked"] for x in loose["matches"])
    top = strict["matches"][0]
    d = client.get(f"/api/matches/{top['id']}", headers=h).json()
    assert len(d["result"]["dimensions"]) == 12 and d["result"]["label"] and "estimate" in d["disclaimer"]
    blocked = next(x for x in loose["matches"] if x["blocked"])
    db = client.get(f"/api/matches/{blocked['id']}", headers=h).json()["result"]
    assert db["blocked"] and db["dealbreakers"]

def test_detail_edge_cases(client):
    h = auth(client)
    me = client.get("/api/me", headers=h).json()["id"]
    assert client.get(f"/api/matches/{me}", headers=h).status_code == 404
    assert client.get("/api/matches/not-an-id", headers=h).status_code == 404
    # girls-hostel demo student is not an eligible roommate for a boys-hostel user
    from backend.app.db import get_db
    from backend.app.services.matching import user_profile
    g = next(u for u in get_db().users.find({"is_synthetic": True}) if user_profile(u)["hostel"] == "Girls hostel")
    assert client.get(f"/api/matches/{g['_id']}", headers=h).status_code == 404

def test_second_real_user_sees_first_when_complete(client, base_answers):
    assert signup(client, "two@x.com").status_code == 201
    h2 = auth(client, "two@x.com")
    client.put("/api/profile", headers=h2, json={"answers": base_answers, "priorities": ["Cleanliness"]})
    names = [x["name"] for x in client.get("/api/matches?k=50", headers=h2).json()["matches"]]
    assert "New Student" in names
    only_real = client.get("/api/matches?k=50&include_demo=false", headers=h2).json()["matches"]
    assert all(not x["is_demo"] for x in only_real)

def test_feedback_and_stats(client):
    h = auth(client)
    assert client.post("/api/feedback", headers=h, json={"rating": 6}).status_code == 422
    assert client.post("/api/feedback", headers=h, json={"rating": 4, "note": "ok"}).status_code == 201
    s = client.get("/api/stats", headers=h).json()
    assert s["profiles_total"] >= 62 and s["profiles_complete"] >= 61 and s["eligible_matches"] >= 0
