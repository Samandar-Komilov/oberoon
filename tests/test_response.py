import pytest
import msgspec.json

from oberoon.responses import Response, JSONResponse, TextResponse, HTMLResponse

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


class TestJSONResponse:
    def test_dict(self):
        r = JSONResponse({"key": "value"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/json"
        assert msgspec.json.decode(r.body) == {"key": "value"}

    def test_list(self):
        r = JSONResponse([1, 2, 3])
        assert msgspec.json.decode(r.body) == [1, 2, 3]

    def test_custom_status(self):
        r = JSONResponse({"error": "not found"}, status_code=404)
        assert r.status_code == 404

    def test_nested(self):
        data = {"users": [{"id": 1, "name": "Alice"}]}
        r = JSONResponse(data)
        assert msgspec.json.decode(r.body) == data

    def test_empty_dict(self):
        r = JSONResponse({})
        assert msgspec.json.decode(r.body) == {}

    def test_string_value(self):
        r = JSONResponse("hello")
        assert msgspec.json.decode(r.body) == "hello"

    def test_null_value(self):
        r = JSONResponse(None)
        assert msgspec.json.decode(r.body) is None

    def test_bool_value(self):
        r = JSONResponse(True)
        assert msgspec.json.decode(r.body) is True


class TestTextResponse:
    def test_basic(self):
        r = TextResponse("Hello!")
        assert r.status_code == 200
        assert r.body == b"Hello!"
        assert r.headers["content-type"] == "text/plain; charset=utf-8"

    def test_custom_status(self):
        r = TextResponse("Not Found", status_code=404)
        assert r.status_code == 404

    def test_unicode(self):
        r = TextResponse("Привет мир")
        assert r.body == "Привет мир".encode("utf-8")

    def test_empty(self):
        r = TextResponse("")
        assert r.body == b""


class TestHTMLResponse:
    def test_basic(self):
        r = HTMLResponse("<h1>Hello</h1>")
        assert r.status_code == 200
        assert r.body == b"<h1>Hello</h1>"
        assert r.headers["content-type"] == "text/html; charset=utf-8"

    def test_custom_status(self):
        r = HTMLResponse("<p>Not Found</p>", status_code=404)
        assert r.status_code == 404

    def test_unicode(self):
        r = HTMLResponse("<p>日本語</p>")
        assert r.body == "<p>日本語</p>".encode("utf-8")
