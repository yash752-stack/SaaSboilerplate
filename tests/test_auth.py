import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from tests.utils import unique_email


@pytest.mark.asyncio
async def test_register_user():
    email = unique_email("register")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "testpass123",
            "full_name": "Test User",
        })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "user"
    assert data["plan"] == "free"


@pytest.mark.asyncio
async def test_register_duplicate_email():
    email = unique_email("duplicate")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"email": email, "password": "testpass123"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success():
    email = unique_email("login")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "testpass123",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "testpass123",
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "wrongpassword",
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me():
    email = unique_email("me")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "testpass123",
        })
        login = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "testpass123",
        })
        token = login.json()["access_token"]
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert response.json()["email"] == email
