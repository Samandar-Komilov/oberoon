"""Tests for header parameter extraction and validation via Annotated[type, Header(...)]."""

from typing import Annotated

import httpx
import pytest

from oberoon import Oberoon, Header, Request

pytestmark = pytest.mark.anyio


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    app = Oberoon()

    @app.get("/auth")
    async def auth(
        request: Request,
        authorization: Annotated[str, Header()],
    ) -> dict:
        return {"auth": authorization}

    @app.get("/optional-header")
    async def optional_header(
        request: Request,
        x_request_id: Annotated[str, Header()] = "default-id",
    ) -> dict:
        return {"id": x_request_id}

    @app.get("/multi-header")
    async def multi_header(
        request: Request,
        authorization: Annotated[str, Header()],
        x_request_id: Annotated[str, Header()] = "",
    ) -> dict:
        return {"auth": authorization, "id": x_request_id}

    return app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Tests ───────────────────────────────────────────────────────────────────


class TestHeaderParams:
    async def test_required_header_present(self, client):
        resp = await client.get("/auth", headers={"authorization": "Bearer token123"})
        assert resp.status_code == 200
        assert resp.json() == {"auth": "Bearer token123"}

    async def test_required_header_missing(self, client):
        resp = await client.get("/auth")
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"] == "Validation Error"
        assert data["detail"][0]["loc"] == ["header"]

    async def test_underscore_to_hyphen_mapping(self, client):
        resp = await client.get("/optional-header", headers={"x-request-id": "abc-123"})
        assert resp.status_code == 200
        assert resp.json() == {"id": "abc-123"}

    async def test_optional_header_default(self, client):
        resp = await client.get("/optional-header")
        assert resp.status_code == 200
        assert resp.json() == {"id": "default-id"}

    async def test_multiple_headers(self, client):
        resp = await client.get(
            "/multi-header",
            headers={"authorization": "Bearer xyz", "x-request-id": "req-1"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"auth": "Bearer xyz", "id": "req-1"}
