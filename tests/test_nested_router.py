import pytest
import httpx

from oberoon import Oberoon, Request, Response, Router
from oberoon.responses import TextResponse

pytestmark = pytest.mark.anyio


# -- Helper to create a client from an app --


async def make_client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# -- Two-level nesting: app -> router -> subrouter --


class TestTwoLevelNesting:
    @pytest.fixture
    async def client(self):
        app = Oberoon()

        api_router = Router(prefix="/api")
        v1_router = Router(prefix="/v1")

        @v1_router.get("/users")
        async def list_users(request: Request) -> Response:
            return TextResponse("v1_users")

        @v1_router.get("/users/{user_id:int}")
        async def get_user(request: Request, user_id: int) -> Response:
            return TextResponse(f"v1_user_{user_id}")

        @api_router.get("/health")
        async def api_health(request: Request) -> Response:
            return TextResponse("api_ok")

        # This requires Router.include_router to exist
        api_router.include_router(v1_router)
        app.include_router(api_router)

        async with await make_client(app) as c:
            yield c

    async def test_nested_route(self, client):
        """GET /api/v1/users should work."""
        resp = await client.get("/api/v1/users")
        assert resp.status_code == 200
        assert resp.text == "v1_users"

    async def test_nested_with_path_param(self, client):
        """GET /api/v1/users/42 should work with int conversion."""
        resp = await client.get("/api/v1/users/42")
        assert resp.status_code == 200
        assert resp.text == "v1_user_42"

    async def test_parent_router_route_still_works(self, client):
        """GET /api/health (direct route on parent router) should work."""
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.text == "api_ok"

    async def test_404_partial_prefix(self, client):
        """/api/v1 alone should 404."""
        resp = await client.get("/api/v1")
        assert resp.status_code == 404

    async def test_404_missing_parent_prefix(self, client):
        """/v1/users without /api should 404."""
        resp = await client.get("/v1/users")
        assert resp.status_code == 404

    async def test_404_child_route_without_nesting(self, client):
        """/users should 404 — only accessible under /api/v1."""
        resp = await client.get("/users")
        assert resp.status_code == 404

    async def test_405_on_nested_route(self, client):
        """POST /api/v1/users should 405 (only GET registered)."""
        resp = await client.post("/api/v1/users")
        assert resp.status_code == 405


# -- Three-level nesting: app -> api -> v1 -> admin --


class TestThreeLevelNesting:
    @pytest.fixture
    async def client(self):
        app = Oberoon()

        api_router = Router(prefix="/api")
        v1_router = Router(prefix="/v1")
        admin_router = Router(prefix="/admin")

        @admin_router.get("/dashboard")
        async def dashboard(request: Request) -> Response:
            return TextResponse("admin_dashboard")

        @admin_router.delete("/purge")
        async def purge(request: Request) -> Response:
            return TextResponse("purged")

        v1_router.include_router(admin_router)
        api_router.include_router(v1_router)
        app.include_router(api_router)

        async with await make_client(app) as c:
            yield c

    async def test_three_level_route(self, client):
        """GET /api/v1/admin/dashboard should work."""
        resp = await client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 200
        assert resp.text == "admin_dashboard"

    async def test_three_level_different_method(self, client):
        """DELETE /api/v1/admin/purge should work."""
        resp = await client.delete("/api/v1/admin/purge")
        assert resp.status_code == 200
        assert resp.text == "purged"

    async def test_404_skip_middle(self, client):
        """/api/admin/dashboard (skipping v1) should 404."""
        resp = await client.get("/api/admin/dashboard")
        assert resp.status_code == 404

    async def test_405_wrong_method_deep(self, client):
        """POST /api/v1/admin/dashboard should 405."""
        resp = await client.post("/api/v1/admin/dashboard")
        assert resp.status_code == 405


# -- Sibling subrouters at the same level --


class TestSiblingSubrouters:
    @pytest.fixture
    async def client(self):
        app = Oberoon()

        api_router = Router(prefix="/api")
        v1_router = Router(prefix="/v1")
        v2_router = Router(prefix="/v2")

        @v1_router.get("/items")
        async def v1_items(request: Request) -> Response:
            return TextResponse("v1_items")

        @v2_router.get("/items")
        async def v2_items(request: Request) -> Response:
            return TextResponse("v2_items")

        api_router.include_router(v1_router)
        api_router.include_router(v2_router)
        app.include_router(api_router)

        async with await make_client(app) as c:
            yield c

    async def test_v1_route(self, client):
        resp = await client.get("/api/v1/items")
        assert resp.status_code == 200
        assert resp.text == "v1_items"

    async def test_v2_route(self, client):
        resp = await client.get("/api/v2/items")
        assert resp.status_code == 200
        assert resp.text == "v2_items"

    async def test_no_cross_contamination(self, client):
        """v1 and v2 should be independent — /api/items should 404."""
        resp = await client.get("/api/items")
        assert resp.status_code == 404


# -- Edge: subrouter with empty prefix --


class TestNestedEmptyPrefix:
    @pytest.fixture
    async def client(self):
        app = Oberoon()

        parent = Router(prefix="/api")
        child = Router(prefix="")

        @child.get("/ping")
        async def ping(request: Request) -> Response:
            return TextResponse("pong")

        parent.include_router(child)
        app.include_router(parent)

        async with await make_client(app) as c:
            yield c

    async def test_empty_child_prefix(self, client):
        """Child with empty prefix: /api/ping should work."""
        resp = await client.get("/api/ping")
        assert resp.status_code == 200
        assert resp.text == "pong"


# -- Edge: all empty prefixes --


class TestAllEmptyPrefixes:
    @pytest.fixture
    async def client(self):
        app = Oberoon()

        r1 = Router(prefix="")
        r2 = Router(prefix="")

        @r2.get("/deep")
        async def deep(request: Request) -> Response:
            return TextResponse("deep")

        r1.include_router(r2)
        app.include_router(r1)

        async with await make_client(app) as c:
            yield c

    async def test_all_empty_prefixes(self, client):
        resp = await client.get("/deep")
        assert resp.status_code == 200
        assert resp.text == "deep"


# -- Edge: routes at every level of the tree --


class TestRoutesAtEveryLevel:
    @pytest.fixture
    async def client(self):
        app = Oberoon()

        @app.get("/app-level")
        async def app_route(request: Request) -> Response:
            return TextResponse("app")

        parent = Router(prefix="/parent")

        @parent.get("/parent-level")
        async def parent_route(request: Request) -> Response:
            return TextResponse("parent")

        child = Router(prefix="/child")

        @child.get("/child-level")
        async def child_route(request: Request) -> Response:
            return TextResponse("child")

        parent.include_router(child)
        app.include_router(parent)

        async with await make_client(app) as c:
            yield c

    async def test_app_level(self, client):
        resp = await client.get("/app-level")
        assert resp.status_code == 200
        assert resp.text == "app"

    async def test_parent_level(self, client):
        resp = await client.get("/parent/parent-level")
        assert resp.status_code == 200
        assert resp.text == "parent"

    async def test_child_level(self, client):
        resp = await client.get("/parent/child/child-level")
        assert resp.status_code == 200
        assert resp.text == "child"


# -- Edge: subrouter included into multiple parents --


class TestSharedSubrouter:
    @pytest.fixture
    async def client(self):
        app = Oberoon()

        shared = Router(prefix="/shared")

        @shared.get("/resource")
        async def resource(request: Request) -> Response:
            return TextResponse("shared_resource")

        parent_a = Router(prefix="/a")
        parent_b = Router(prefix="/b")

        parent_a.include_router(shared)
        parent_b.include_router(shared)

        app.include_router(parent_a)
        app.include_router(parent_b)

        async with await make_client(app) as c:
            yield c

    async def test_shared_under_a(self, client):
        resp = await client.get("/a/shared/resource")
        assert resp.status_code == 200
        assert resp.text == "shared_resource"

    async def test_shared_under_b(self, client):
        resp = await client.get("/b/shared/resource")
        assert resp.status_code == 200
        assert resp.text == "shared_resource"

    async def test_shared_alone_404(self, client):
        resp = await client.get("/shared/resource")
        assert resp.status_code == 404
