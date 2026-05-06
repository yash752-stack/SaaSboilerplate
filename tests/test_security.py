import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.utils import unique_email


async def _register_and_login(client: AsyncClient, email: str, password: str = "testpass123") -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_api_key_create_and_list():
    email = unique_email("api-key")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, email)

        create_resp = await client.post(
            "/api/v1/security/api-keys",
            json={"name": "CI Runner", "scopes": ["read", "write"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_resp.status_code == 200
        assert create_resp.json()["api_key"].startswith("sk_live_")

        list_resp = await client.get(
            "/api/v1/security/api-keys",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["name"] == "CI Runner"


@pytest.mark.asyncio
async def test_two_factor_setup_enable_and_disable():
    email = unique_email("two-factor")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, email)

        setup_resp = await client.post(
            "/api/v1/security/2fa/setup",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert setup_resp.status_code == 200
        setup_data = setup_resp.json()
        assert setup_data["secret"]
        assert setup_data["qr_png_base64"]

        secret = setup_data["secret"]
        code = pyotp.TOTP(secret).now()
        enable_resp = await client.post(
            f"/api/v1/security/2fa/enable?secret={secret}",
            json={"code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert enable_resp.status_code == 200

        disable_resp = await client.post(
            "/api/v1/security/2fa/disable",
            json={"code": pyotp.TOTP(secret).now()},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert disable_resp.status_code == 200
