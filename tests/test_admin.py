import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.user import User, UserRole
from tests.utils import unique_email


async def _register(client: AsyncClient, email: str, password: str = "testpass123") -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})


async def _login(client: AsyncClient, email: str, password: str = "testpass123") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _promote_to_admin(email: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.role = UserRole.admin
        session.add(user)
        await session.commit()


@pytest.mark.asyncio
async def test_admin_can_list_users_and_view_stats():
    admin_email = unique_email("admin")
    regular_email = unique_email("regular")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register(client, admin_email)
        await _register(client, regular_email)
        await _promote_to_admin(admin_email)
        admin_token = await _login(client, admin_email)

        users_resp = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        stats_resp = await client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert users_resp.status_code == 200
    assert stats_resp.status_code == 200
    assert users_resp.json()["total"] >= 2
    assert "total_users" in stats_resp.json()


@pytest.mark.asyncio
async def test_admin_can_update_role():
    admin_email = unique_email("role-admin")
    user_email = unique_email("role-user")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register(client, admin_email)
        await _register(client, user_email)
        await _promote_to_admin(admin_email)
        admin_token = await _login(client, admin_email)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == user_email))
            user = result.scalar_one()
            user_id = user.id

        update_resp = await client.patch(
            f"/api/v1/admin/users/{user_id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["role"] == "admin"
