import pytest
import httpx

from oberoon import Oberoon, Request, Response, Router
from oberoon.responses import build_response

pytestmark = pytest.mark.anyio


# -- Fixtures --


@pytest.fixture
def app_with_router():
    """App with a prefixed router and some direct routes."""
    app = Oberoon()

    # Direct route on app
    @app.get("/health")
    async def health(request: Request) -> Response:
        return build_response(body=b"ok")

    # Router with prefix
    router = Router(prefix="/api")

    @router.get("/items")
    async def list_items(request: Request) -> Response:
        return build_response(
            body=b'["item1","item2"]', content_type="application/json"
        )

    @router.post("/items")
    async def create_item(request: Request) -> Response:
        return build_response(
            status_code=201, body=b'{"created": true}', content_type="application/json"
        )

    @router.get("/items/{item_id:int}")
    async def get_item(request: Request, item_id: int) -> Response:
        return build_response(
            body=f'{{"id": {item_id}}}'.encode(), content_type="application/json"
        )

    @router.get("/items/{item_id:int}/details/{section}")
    async def get_item_detail(request: Request, item_id: int, section: str) -> Response:
        return build_response(
            body=f'{{"id": {item_id}, "section": "{section}"}}'.encode(),
            content_type="application/json",
        )

    app.include_router(router)
    return app


@pytest.fixture
async def client(app_with_router):
    transport = httpx.ASGITransport(app=app_with_router)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# -- Basic router functionality --


class TestRouterBasic:
    async def test_prefixed_get(self, client):
        resp = await client.get("/api/items")
        assert resp.status_code == 200
        assert resp.json() == ["item1", "item2"]

    async def test_prefixed_post(self, client):
        resp = await client.post("/api/items")
        assert resp.status_code == 201
        assert resp.json() == {"created": True}

    async def test_prefixed_path_param(self, client):
        resp = await client.get("/api/items/42")
        assert resp.status_code == 200
        assert resp.json() == {"id": 42}

    async def test_prefixed_multiple_params(self, client):
        resp = await client.get("/api/items/7/details/overview")
        assert resp.status_code == 200
        assert resp.json() == {"id": 7, "section": "overview"}

    async def test_direct_route_still_works(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.text == "ok"


# -- 404 / 405 on router routes --


class TestRouterErrors:
    async def test_404_no_prefix(self, client):
        """Route exists at /api/items, not at /items."""
        resp = await client.get("/items")
        assert resp.status_code == 404

    async def test_404_wrong_path_under_prefix(self, client):
        resp = await client.get("/api/nonexistent")
        assert resp.status_code == 404

    async def test_405_wrong_method_on_router_route(self, client):
        """GET /api/items is registered, DELETE is not."""
        resp = await client.delete("/api/items")
        assert resp.status_code == 405

    async def test_404_prefix_alone(self, client):
        """Just /api with nothing after should 404."""
        resp = await client.get("/api")
        assert resp.status_code == 404

    async def test_404_trailing_slash(self, client):
        """/api/items/ should not match /api/items (exact regex)."""
        resp = await client.get("/api/items/")
        assert resp.status_code == 404

    async def test_404_int_param_rejects_alpha(self, client):
        resp = await client.get("/api/items/abc")
        assert resp.status_code == 404


# -- Edge cases: empty prefix --


class TestRouterEmptyPrefix:
    @pytest.fixture
    async def empty_prefix_client(self):
        app = Oberoon()

        router = Router(prefix="")

        @router.get("/things")
        async def things(request: Request) -> Response:
            return build_response(body=b"things")

        app.include_router(router)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_empty_prefix_route(self, empty_prefix_client):
        resp = await empty_prefix_client.get("/things")
        assert resp.status_code == 200
        assert resp.text == "things"


# -- Edge cases: multiple routers --


class TestMultipleRouters:
    @pytest.fixture
    async def multi_client(self):
        app = Oberoon()

        api_router = Router(prefix="/api")
        admin_router = Router(prefix="/admin")

        @api_router.get("/data")
        async def api_data(request: Request) -> Response:
            return build_response(body=b"api_data")

        @admin_router.get("/data")
        async def admin_data(request: Request) -> Response:
            return build_response(body=b"admin_data")

        app.include_router(api_router)
        app.include_router(admin_router)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_routes_dont_clash(self, multi_client):
        resp1 = await multi_client.get("/api/data")
        resp2 = await multi_client.get("/admin/data")
        assert resp1.text == "api_data"
        assert resp2.text == "admin_data"

    async def test_wrong_prefix_404(self, multi_client):
        resp = await multi_client.get("/data")
        assert resp.status_code == 404


# -- Edge case: same router included twice --


class TestRouterIncludedTwice:
    @pytest.fixture
    async def twice_client(self):
        app = Oberoon()
        router = Router(prefix="/v1")

        @router.get("/ping")
        async def ping(request: Request) -> Response:
            return build_response(body=b"pong")

        app.include_router(router)
        # Include same router again with different prefix
        router2 = Router(prefix="/v2")

        @router2.get("/ping")
        async def ping2(request: Request) -> Response:
            return build_response(body=b"pong2")

        app.include_router(router2)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_both_versions_work(self, twice_client):
        r1 = await twice_client.get("/v1/ping")
        r2 = await twice_client.get("/v2/ping")
        assert r1.text == "pong"
        assert r2.text == "pong2"


# -- Edge case: router with only non-GET methods --


class TestRouterMethodsOnly:
    @pytest.fixture
    async def post_only_client(self):
        app = Oberoon()
        router = Router(prefix="/hooks")

        @router.post("/webhook")
        async def webhook(request: Request) -> Response:
            return build_response(status_code=202, body=b"accepted")

        app.include_router(router)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_post_works(self, post_only_client):
        resp = await post_only_client.post("/hooks/webhook")
        assert resp.status_code == 202

    async def test_get_returns_405(self, post_only_client):
        resp = await post_only_client.get("/hooks/webhook")
        assert resp.status_code == 405


# -- Unit tests for Router class itself --


class TestRouterUnit:
    def test_prefix_stored(self):
        r = Router(prefix="/api")
        assert r.prefix == "/api"

    def test_default_prefix_empty(self):
        r = Router()
        assert r.prefix == ""

    def test_route_records_populated(self):
        r = Router(prefix="/x")

        @r.get("/foo")
        async def foo(req):
            pass

        @r.post("/bar")
        async def bar(req):
            pass

        assert len(r._route_records) == 2
        assert r._route_records[0].path == "/foo"
        assert r._route_records[0].methods == ["GET"]
        assert r._route_records[1].path == "/bar"
        assert r._route_records[1].methods == ["POST"]

    def test_decorator_returns_original_handler(self):
        r = Router()

        @r.get("/x")
        async def handler(req):
            pass

        assert handler.__name__ == "handler"

    def test_route_with_multiple_methods(self):
        r = Router()

        @r.route("/multi", methods=["GET", "POST"])
        async def multi(req):
            pass

        assert r._route_records[0].methods == ["GET", "POST"]
