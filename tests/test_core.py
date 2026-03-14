import pytest

pytestmark = pytest.mark.anyio


class TestBasicRouting:
    async def test_get_static(self, client):
        resp = await client.get("/hello")
        assert resp.status_code == 200
        assert resp.text == "Hello!"
        assert resp.headers["content-type"] == "text/plain"

    async def test_post_creates(self, client):
        resp = await client.post("/users")
        assert resp.status_code == 201
        assert resp.json() == {"created": True}

    async def test_multi_method_get(self, client):
        resp = await client.get("/multi")
        assert resp.status_code == 200
        assert resp.text == "GET"

    async def test_multi_method_post(self, client):
        resp = await client.post("/multi")
        assert resp.status_code == 200
        assert resp.text == "POST"


class TestPathParams:
    async def test_int_param_converted(self, client):
        resp = await client.get("/users/42")
        data = resp.json()
        assert data["user_id"] == 42
        assert data["type"] == "int"

    async def test_str_param(self, client):
        resp = await client.get("/items/widget")
        assert resp.status_code == 200
        assert resp.text == "widget"

    async def test_int_param_rejects_alpha(self, client):
        resp = await client.get("/users/abc")
        assert resp.status_code == 404


class TestErrorResponses:
    async def test_404_unknown_path(self, client):
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404
        assert resp.json() == {"error": "Not Found"}
        assert resp.headers["content-type"] == "application/json"

    async def test_405_wrong_method(self, client):
        resp = await client.delete("/hello")
        assert resp.status_code == 405
        assert resp.json() == {"error": "Method Not Allowed"}
        assert resp.headers["content-type"] == "application/json"

    async def test_405_on_post_to_get_only(self, client):
        resp = await client.post("/hello")
        assert resp.status_code == 405
