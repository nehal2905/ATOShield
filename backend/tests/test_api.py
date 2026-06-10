"""Phase 3 acceptance: register/login, auth enforcement, and live model scoring."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.scorer import Scorer, set_scorer
from app.db.session import init_db
from app.main import app

ARTIFACTS_PRESENT = all(
    os.path.exists(os.path.join(settings.ml_artifacts_dir, f))
    for f in ("model.pkl", "scaler.pkl", "calibration.json")
)


@pytest_asyncio.fixture
async def client():
    await init_db()
    if ARTIFACTS_PRESENT:
        set_scorer(Scorer().load())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client):
    r = await client.get("/api/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_register_login_and_access(client):
    # register a fresh analyst
    reg = await client.post("/api/auth/register", json={
        "username": "analyst1", "password": "supersecret", "role": "analyst"})
    assert reg.status_code in (201, 409)

    login = await client.post("/api/auth/login", json={
        "username": "analyst1", "password": "supersecret"})
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    token = body["access_token"]

    # cookie was set; client carries it. Stats should now work.
    r = await client.get("/api/stats")
    assert r.status_code == 200
    assert "events_24h" in r.json()

    # bearer header also works
    r2 = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["username"] == "analyst1"


@pytest.mark.asyncio
@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="ML artifacts missing")
async def test_simulate_uses_real_model(client):
    await client.post("/api/auth/register", json={
        "username": "analyst2", "password": "supersecret", "role": "analyst"})
    await client.post("/api/auth/login", json={
        "username": "analyst2", "password": "supersecret"})

    # an obvious attack should score high; a normal event low — proving the
    # backend model (not a client heuristic) drives the score.
    attack = await client.post("/api/simulate", json={
        "login_hour": 3, "ip_change": 1, "device_change": 1,
        "frequency": 30, "geo_velocity": 4000, "failed_attempts": 20})
    assert attack.status_code == 200
    normal = await client.post("/api/simulate", json={
        "login_hour": 14, "ip_change": 0, "device_change": 0,
        "frequency": 1, "geo_velocity": 0, "failed_attempts": 0})
    assert normal.status_code == 200

    assert attack.json()["result"]["risk"] > normal.json()["result"]["risk"]
    assert len(attack.json()["trace"]) >= 6
