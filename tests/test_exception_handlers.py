"""Tests for exception handler registry, debug mode, and standardized error responses."""

import httpx
import pytest

from oberoon import Oberoon, HTTPException, Request, JSONResponse

pytestmark = pytest.mark.anyio


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    app = Oberoon()

    @app.get("/crash")
    async def crash(request: Request) -> dict:
        raise RuntimeError("something broke")

    @app.get("/http-error")
    async def http_error(request: Request) -> dict:
        raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/ok")
    async def ok(request: Request) -> dict:
        return {"status": "ok"}

    return app


@pytest.fixture
def debug_app():
    app = Oberoon(debug=True)

    @app.get("/crash")
    async def crash(request: Request) -> dict:
        raise RuntimeError("something broke")

    return app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def debug_client(debug_app):
    transport = httpx.ASGITransport(app=debug_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Tests ───────────────────────────────────────────────────────────────────


class TestDefaultErrorHandling:
    async def test_500_returns_json(self, client):
        resp = await client.get("/crash")
        assert resp.status_code == 500
        assert resp.json() == {"error": "Internal Server Error"}

    async def test_500_no_detail_in_production(self, client):
        resp = await client.get("/crash")
        assert "detail" not in resp.json()

    async def test_http_exception(self, client):
        resp = await client.get("/http-error")
        assert resp.status_code == 403
        assert resp.json() == {"error": "Forbidden"}

    async def test_404(self, client):
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404
        assert resp.json() == {"error": "Not Found"}

    async def test_405(self, client):
        resp = await client.post("/ok")
        assert resp.status_code == 405
        assert resp.json() == {"error": "Method Not Allowed"}


class TestDebugMode:
    async def test_500_includes_detail(self, debug_client):
        resp = await debug_client.get("/crash")
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "Internal Server Error"
        assert "RuntimeError: something broke" in data["detail"]


class TestCustomExceptionHandler:
    async def test_override_default(self):
        app = Oberoon()

        @app.exception_handler(RuntimeError)
        def handle_runtime(request, exc):
            return JSONResponse({"error": "Custom", "msg": str(exc)}, status_code=503)

        @app.get("/crash")
        async def crash(request: Request) -> dict:
            raise RuntimeError("oops")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/crash")

        assert resp.status_code == 503
        assert resp.json() == {"error": "Custom", "msg": "oops"}
