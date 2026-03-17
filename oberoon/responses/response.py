from typing import Any, Callable

import msgspec.json


class Response:
    def __init__(self, status_code: int = 200):
        self._status_code: int = status_code
        self._headers: dict[str, str] = {}
        self._body: bytes = b""

    async def send(self, send: Callable) -> None:
        encoded_headers = [[k.encode(), v.encode()] for k, v in self.headers.items()]
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": encoded_headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": self._body,
                "more_body": False,
            }
        )

    def set_body(self, body: bytes, content_type: str):
        self._body = body
        self.headers["content-type"] = content_type

    @property
    def status_code(self):
        return self._status_code

    @property
    def headers(self):
        return self._headers

    @property
    def body(self):
        return self._body


class JSONResponse(Response):
    def __init__(self, content: Any, status_code: int = 200):
        super().__init__(status_code)
        self.set_body(msgspec.json.encode(content), "application/json")


class TextResponse(Response):
    def __init__(self, content: str, status_code: int = 200):
        super().__init__(status_code)
        self.set_body(content.encode("utf-8"), "text/plain; charset=utf-8")


class HTMLResponse(Response):
    def __init__(self, content: str, status_code: int = 200):
        super().__init__(status_code)
        self.set_body(content.encode("utf-8"), "text/html; charset=utf-8")
