from typing import Callable

from oberoon.logging import get_logger
from oberoon.requests import Request
from oberoon.responses import Response, build_response
from oberoon.exceptions import NotFoundException, MethodNotAllowedException
from oberoon.routing import Route, Router, RoutingMixin, compile_path

logger = get_logger("core")


class Oberoon(RoutingMixin):
    def __init__(self):
        self._routes: list[Route] = list()

    # SECTION: core

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] == "lifespan":
            await self.handle_lifespan(receive, send)
        elif scope["type"] == "http":
            request = Request(scope, receive)
            response = await self.handle_request(request)
            await response.send(send)
        elif scope["type"] == "websocket":
            raise NotImplementedError("WebSockets not implemented yet")
        else:
            raise NotImplementedError(f"Unknown scope type: {scope['type']}")

    def route(self, path: str, methods: list[str] | None = None):
        def decorator(handler):
            pattern, param_types = compile_path(path)
            route = Route(
                pattern=pattern,
                param_types=param_types,
                handler=handler,
                methods=methods or ["GET"],
            )
            self._routes.append(route)
            logger.warning(
                "route registered: %s %s -> %s", methods, path, handler.__name__
            )
            return handler

        return decorator

    def include_router(self, router: Router, prefix: str = ""):
        for record in router._route_records:
            pattern, param_types = compile_path(prefix + router.prefix + record.path)
            route = Route(
                pattern=pattern,
                param_types=param_types,
                handler=record.handler,
                methods=record.methods,
            )
            self._routes.append(route)
            logger.warning(
                "route include regged: %s %s -> %s",
                route.pattern,
                route.param_types,
                route.handler.__name__,
            )

        for subrouter in router._subrouters:
            self.include_router(subrouter, prefix + router.prefix)

    async def handle_request(self, request: Request) -> Response:
        try:
            route, path_params = await self.find_handler(request.method, request.path)
        except NotFoundException:
            logger.warning("404 %s %s", request.method, request.path)
            response = build_response(
                status_code=404,
                content_type="application/json",
                body=b'{"error": "Not Found"}',
            )
            return response
        except MethodNotAllowedException:
            logger.warning("405 %s %s", request.method, request.path)
            response = build_response(
                status_code=405,
                content_type="application/json",
                body=b'{"error": "Method Not Allowed"}',
            )
            return response

        converted_params = {k: route.param_types[k](v) for k, v in path_params.items()}
        response = await route.handler(request, **converted_params)

        logger.info("%s %s -> %d", request.method, request.path, response.status_code)

        return response

    async def find_handler(self, method: str, path: str):
        logger.warning("finding handler for: %s %s", method, path)
        method_mismatch: bool = False

        for route in self._routes:
            logger.warning(
                "checking route: %s %s -> %s",
                route.methods,
                route.pattern,
                route.handler,
            )
            match = route.pattern.match(path)
            if match:
                if method in route.methods:
                    return route, match.groupdict()
                method_mismatch = True

        if method_mismatch:
            raise MethodNotAllowedException
        raise NotFoundException

    async def handle_lifespan(self, receive, send):
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
