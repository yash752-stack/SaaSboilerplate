import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.utils import unique_email


async def _register_and_login(client: AsyncClient, email: str, password: str = "testpass123") -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_org_members_require_membership():
    owner_email = unique_email("org-owner")
    outsider_email = unique_email("org-outsider")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_token = await _register_and_login(client, owner_email)
        outsider_token = await _register_and_login(client, outsider_email)

        create_resp = await client.post(
            "/api/v1/orgs",
            json={"name": "Acme Cloud"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        org_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/orgs/{org_id}/members",
            headers={"Authorization": f"Bearer {outsider_token}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_org_owner_can_add_member_but_member_cannot_administer():
    owner_email = unique_email("org-admin-owner")
    member_email = unique_email("org-member")
    third_email = unique_email("org-third")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_token = await _register_and_login(client, owner_email)
        member_token = await _register_and_login(client, member_email)
        await _register_and_login(client, third_email)

        create_resp = await client.post(
            "/api/v1/orgs",
            json={"name": "Platform Ops"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert create_resp.status_code == 200
        org_id = create_resp.json()["id"]

        add_resp = await client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": member_email, "role": "member"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert add_resp.status_code == 200

        members_resp = await client.get(
            f"/api/v1/orgs/{org_id}/members",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert members_resp.status_code == 200
        assert len(members_resp.json()) == 2

        blocked_resp = await client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": third_email, "role": "member"},
            headers={"Authorization": f"Bearer {member_token}"},
        )

    assert blocked_resp.status_code == 403


@pytest.mark.asyncio
async def test_cannot_remove_last_active_owner():
    owner_email = unique_email("org-last-owner")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_token = await _register_and_login(client, owner_email)

        create_resp = await client.post(
            "/api/v1/orgs",
            json={"name": "Last Owner Org"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        org_id = create_resp.json()["id"]

        members_resp = await client.get(
            f"/api/v1/orgs/{org_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        owner_user_id = members_resp.json()[0]["user_id"]

        delete_resp = await client.delete(
            f"/api/v1/orgs/{org_id}/members/{owner_user_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert delete_resp.status_code == 400
    assert "last active organization owner" in delete_resp.json()["detail"].lower()
