import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _register_and_login(client, email):
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "testpass123"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "testpass123"
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_list_plans():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/billing/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 3
    names = [p["name"] for p in plans]
    assert "Free" in names
    assert "Pro" in names
    assert "Enterprise" in names


@pytest.mark.asyncio
async def test_subscription_status_default_free():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "billing_test@example.com")
        response = await client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "free"
    assert data["stripe_customer_id"] is None


@pytest.mark.asyncio
async def test_checkout_free_plan_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "checkout_test@example.com")
        response = await client.post(
            "/api/v1/billing/checkout",
            json={"plan": "free", "success_url": "http://localhost/success", "cancel_url": "http://localhost/cancel"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_missing_signature():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/billing/webhook",
            content=b'{"type": "checkout.session.completed"}',
        )
    assert response.status_code == 400
    assert "stripe-signature" in response.json()["detail"].lower()
