from typing import Callable


class Response:
    def __init__(self):
        self.status_code: int = 200
        self.headers: dict[str, str] = {}
        self._body: bytes = b""

    def set_body(self, body: bytes, content_type: str):
        self._body = body
        self.headers["content-type"] = content_type

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
