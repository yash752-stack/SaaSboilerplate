import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.utils.tokens import (
    generate_email_verification_token,
    generate_password_reset_token,
)


async def _register_and_login(client, email, password="testpass123"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_register_triggers_verification_email():
    with patch("app.tasks.email_tasks.send_verification_email.delay") as mock_task:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/register", json={
                "email": "verify_me@test.com",
                "password": "testpass123",
            })
        assert resp.status_code == 201


@pytest.mark.asyncio
async def test_verify_email_with_valid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json={
            "email": "verifyflow@test.com", "password": "testpass123"
        })
        user_id = reg.json()["id"]

        with patch("app.utils.tokens._redis") as mock_redis:
            mock_redis.get.return_value = user_id
            mock_redis.delete.return_value = 1

            resp = await client.get(f"/api/v1/auth/verify-email?token=fake-valid-token")


@pytest.mark.asyncio
async def test_verify_email_invalid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/auth/verify-email?token=invalid-token-xyz")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_always_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Non-existent email — should still return 200 (prevent enumeration)
        resp = await client.post("/api/v1/auth/forgot-password", json={
            "email": "doesnotexist@test.com"
        })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/reset-password", json={
            "token": "bad-token",
            "new_password": "newpassword123",
        })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_wrong_current():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "changepass@test.com")
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrongpassword", "new_password": "newpass123"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, "changepass2@test.com")
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "testpass123", "new_password": "newpass123"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
