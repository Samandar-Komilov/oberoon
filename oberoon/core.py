from typing import Callable

from oberoon.logging import get_logger
from oberoon.requests import Request
from oberoon.responses import build_response
from oberoon.exceptions import NotFoundException, MethodNotAllowedException
from oberoon.routing import Route, compile_path

logger = get_logger("core")


class Oberoon:
    def __init__(self):
        self._routes: list[Route] = list()

    # SECTION: core

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
        elif scope["type"] == "http":
            request = Request(scope, receive)
            logger.debug("%s %s", request.method, request.path)

            try:
                route, path_params = await self.find_handler(
                    request.method, request.path
                )
            except NotFoundException:
                logger.warning("404 %s %s", request.method, request.path)
                response = build_response(
                    status_code=404,
                    content_type="application/json",
                    body=b'{"error": "Not Found"}',
                )
                await response.send(send)
                return
            except MethodNotAllowedException:
                logger.warning("405 %s %s", request.method, request.path)
                response = build_response(
                    status_code=405,
                    content_type="application/json",
                    body=b'{"error": "Method Not Allowed"}',
                )
                await response.send(send)
                return

            converted_params = {
                k: route.param_types[k](v) for k, v in path_params.items()
            }
            response = await route.handler(request, **converted_params)

            logger.info(
                "%s %s -> %d", request.method, request.path, response.status_code
            )
            await response.send(send)
        elif scope["type"] == "websocket":
            raise NotImplementedError("WebSockets not implemented yet")
        else:
            raise NotImplementedError(f"Unknown scope type: {scope['type']}")

    async def _handle_lifespan(self, receive, send):
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    # SECTION: routing

    async def find_handler(self, method: str, path: str):
        for route in self._routes:
            logger.debug(
                "checking route: %s %s -> %s",
                route.methods,
                route.pattern,
                route.handler,
            )
            match = route.pattern.match(path)
            if match:
                if method in route.methods:
                    return route, match.groupdict()
                raise MethodNotAllowedException
        raise NotFoundException

    def route(self, path: str, methods: list[str] | None = None):
        def decorator(handler):
            pattern, param_types = compile_path(path)
            route = Route(
                pattern=pattern,
                param_types=param_types,
                handler=handler,
                methods={m.upper() for m in (methods or [])},
            )
            self._routes.append(route)
            logger.debug(
                "route registered: %s %s -> %s", methods, path, handler.__name__
            )
            return handler

        return decorator

    def get(self, path: str):
        return self.route(path, methods=["get"])

    def post(self, path: str):
        return self.route(path, methods=["post"])

    def put(self, path: str):
        return self.route(path, methods=["put"])

    def patch(self, path: str):
        return self.route(path, methods=["patch"])

    def delete(self, path: str):
        return self.route(path, methods=["delete"])
