from urllib.parse import parse_qs

import msgspec


class Request:
    def __init__(self, scope, receive):
        self._scope = scope
        self._receive = receive

    @property
    def method(self) -> str:
        return self._scope["method"].upper()

    @property
    def path(self) -> str:
        return self._scope["path"]

    @property
    def query_string(self) -> str:
        return self._scope["query_string"].decode()

    @property
    def query_params(self) -> dict[str, str]:
        """Parse query string into {key: last_value} dict."""
        parsed = parse_qs(self._scope["query_string"].decode(), keep_blank_values=True)
        return {key: val[-1] for key, val in parsed.items()}

    @property
    def headers(self) -> dict[str, str]:
        return {k.decode(): v.decode() for k, v in self._scope["headers"]}

    async def body(self) -> bytes:
        # ASGI body may arrive in multiple chunks
        chunks = []
        while True:
            message = await self._receive()
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    async def json(self):
        if self.headers.get("content-type", "").startswith("application/json"):
            return msgspec.json.decode(await self.body())
