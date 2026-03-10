from typing import Callable

from oberoon.requests import Request
from oberoon.responses import Response


class Oberoon:
    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
        elif scope["type"] == "http":
            request = Request(scope, receive)
            response = Response()
            await self._handle_request(request, response)
            await response.send(send)
        elif scope["type"] == "websocket":
            raise NotImplementedError("WebSockets not implemented yet")

    async def _handle_request(self, request: Request, response: Response):
        response.status_code = 200
        response.headers = request.headers
        response.set_body(
            b"Hello, world!",
            content_type=request.headers.get("content-type", "text/plain"),
        )

    async def _handle_lifespan(self, receive, send):
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
