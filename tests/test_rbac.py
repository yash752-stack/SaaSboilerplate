import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _register_and_login(client, email, password="testpass123"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_stats_requires_admin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "normaluser@test.com")
        response = await client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pro_feature_blocked_for_free_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "freeuser@test.com")
        response = await client.get(
            "/api/v1/features/pro",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
    assert "pro" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_blocked():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/features/free")
    assert response.status_code == 403
