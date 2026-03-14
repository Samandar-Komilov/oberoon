import pytest

from oberoon.responses import Response, build_response

pytestmark = pytest.mark.anyio


class TestResponse:
    def test_default_status(self):
        r = Response()
        assert r.status_code == 200

    def test_custom_status(self):
        r = Response(404)
        assert r.status_code == 404

    def test_set_body(self):
        r = Response()
        r.set_body(b"hi", content_type="text/plain")
        assert r.body == b"hi"
        assert r.headers["content-type"] == "text/plain"

    def test_headers_not_shared(self):
        r1 = Response()
        r2 = Response()
        r1.set_body(b"a", content_type="text/plain")
        assert "content-type" not in r2.headers

    async def test_send(self):
        messages = []

        async def mock_send(msg):
            messages.append(msg)

        r = Response(201)
        r.set_body(b"ok", content_type="text/plain")
        await r.send(mock_send)

        assert len(messages) == 2
        assert messages[0]["type"] == "http.response.start"
        assert messages[0]["status"] == 201
        assert messages[1]["type"] == "http.response.body"
        assert messages[1]["body"] == b"ok"


class TestBuildResponse:
    def test_basic(self):
        r = build_response(status_code=200, body=b"ok", content_type="text/plain")
        assert r.status_code == 200
        assert r.body == b"ok"
        assert r.headers["content-type"] == "text/plain"

    def test_defaults(self):
        r = build_response()
        assert r.status_code == 200
        assert r.body == b""
        assert r.headers["content-type"] == "text/plain"

    def test_json_content_type(self):
        r = build_response(
            status_code=404,
            body=b'{"error": "not found"}',
            content_type="application/json",
        )
        assert r.headers["content-type"] == "application/json"
