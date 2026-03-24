"""Tests for query parameter extraction and validation via Annotated[type, Query(...)]."""

from typing import Annotated

import httpx
import pytest

from oberoon import Oberoon, Query, Request

pytestmark = pytest.mark.anyio


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    app = Oberoon()

    @app.get("/search")
    async def search(
        request: Request,
        page: Annotated[int, Query(ge=1)] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 10,
    ) -> dict:
        return {"page": page, "limit": limit}

    @app.get("/required")
    async def required_param(
        request: Request,
        name: Annotated[str, Query()],
    ) -> dict:
        return {"name": name}

    @app.get("/bool")
    async def bool_param(
        request: Request,
        active: Annotated[bool, Query()] = True,
    ) -> dict:
        return {"active": active}

    @app.get("/float")
    async def float_param(
        request: Request,
        score: Annotated[float, Query(ge=0.0, le=1.0)] = 0.5,
    ) -> dict:
        return {"score": score}

    return app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Tests ───────────────────────────────────────────────────────────────────


class TestQueryParams:
    async def test_defaults_when_no_query(self, client):
        resp = await client.get("/search")
        assert resp.status_code == 200
        assert resp.json() == {"page": 1, "limit": 10}

    async def test_type_coercion_string_to_int(self, client):
        resp = await client.get("/search?page=3&limit=50")
        assert resp.status_code == 200
        assert resp.json() == {"page": 3, "limit": 50}

    async def test_partial_override(self, client):
        resp = await client.get("/search?page=5")
        assert resp.status_code == 200
        assert resp.json() == {"page": 5, "limit": 10}

    async def test_constraint_violation_ge(self, client):
        resp = await client.get("/search?page=0")
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"] == "Validation Error"
        assert data["detail"][0]["loc"] == ["query"]

    async def test_constraint_violation_le(self, client):
        resp = await client.get("/search?limit=200")
        assert resp.status_code == 422

    async def test_invalid_type(self, client):
        resp = await client.get("/search?page=abc")
        assert resp.status_code == 422

    async def test_required_param_present(self, client):
        resp = await client.get("/required?name=alice")
        assert resp.status_code == 200
        assert resp.json() == {"name": "alice"}

    async def test_required_param_missing(self, client):
        resp = await client.get("/required")
        assert resp.status_code == 422

    async def test_bool_coercion(self, client):
        resp = await client.get("/bool?active=false")
        assert resp.status_code == 200
        assert resp.json() == {"active": False}

    async def test_float_coercion(self, client):
        resp = await client.get("/float?score=0.75")
        assert resp.status_code == 200
        assert resp.json() == {"score": 0.75}

    async def test_float_constraint_violation(self, client):
        resp = await client.get("/float?score=1.5")
        assert resp.status_code == 422
