from typing import Callable


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


def build_response(
    status_code: int = 200,
    body: bytes = b"",
    content_type: str = "text/plain",
) -> Response:
    response = Response(status_code)
    response.set_body(body, content_type)
    return response
