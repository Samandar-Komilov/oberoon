import pytest

from oberoon.requests import Request

pytestmark = pytest.mark.anyio


def _make_scope(**overrides):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"key=val",
        "headers": [(b"content-type", b"text/plain"), (b"x-custom", b"foo")],
    }
    scope.update(overrides)
    return scope


class TestRequest:
    def test_method_uppercased(self):
        r = Request(_make_scope(method="get"), None)
        assert r.method == "GET"

    def test_path(self):
        r = Request(_make_scope(path="/hello"), None)
        assert r.path == "/hello"

    def test_query_string(self):
        r = Request(_make_scope(query_string=b"a=1&b=2"), None)
        assert r.query_string == "a=1&b=2"

    def test_headers(self):
        r = Request(_make_scope(), None)
        assert r.headers["content-type"] == "text/plain"
        assert r.headers["x-custom"] == "foo"

    async def test_body_single_chunk(self):
        chunks = [{"body": b"hello", "more_body": False}]

        async def receive():
            return chunks.pop(0)

        r = Request(_make_scope(), receive)
        assert await r.body() == b"hello"

    async def test_body_multiple_chunks(self):
        chunks = [
            {"body": b"hel", "more_body": True},
            {"body": b"lo", "more_body": False},
        ]

        async def receive():
            return chunks.pop(0)

        r = Request(_make_scope(), receive)
        assert await r.body() == b"hello"

    async def test_json(self):
        data = b'{"name": "test"}'
        chunks = [{"body": data, "more_body": False}]

        async def receive():
            return chunks.pop(0)

        scope = _make_scope(headers=[(b"content-type", b"application/json")])
        r = Request(scope, receive)
        result = await r.json()
        assert result == {"name": "test"}

    async def test_json_returns_none_for_non_json(self):
        chunks = [{"body": b"text", "more_body": False}]

        async def receive():
            return chunks.pop(0)

        r = Request(_make_scope(), receive)
        assert await r.json() is None
