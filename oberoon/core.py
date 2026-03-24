from typing import Callable

from oberoon.logging import get_logger
from oberoon.requests import Request
from oberoon.responses import Response, JSONResponse
from oberoon.exceptions import (
    HTTPException,
    NotFoundException,
    MethodNotAllowedException,
    ValidationError,
)
from oberoon.routing import Route, Router, RoutingMixin, compile_path
from oberoon.serialization import (
    REQUIRED,
    inspect_handler,
    decode_body,
    process_response,
)

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
            body_param, body_type, return_type, query_params, header_params = (
                inspect_handler(handler, set(param_types.keys()))
            )
            route = Route(
                pattern=pattern,
                param_types=param_types,
                handler=handler,
                methods=methods or ["GET"],
                body_param=body_param,
                body_type=body_type,
                return_type=return_type,
                query_params=query_params,
                header_params=header_params,
            )
            self._routes.append(route)
            logger.warning(
                "route registered: %s %s -> %s",
                methods,
                path,
                getattr(handler, "__name__", repr(handler)),
            )
            return handler

        return decorator

    def include_router(self, router: Router, prefix: str = ""):
        for record in router._route_records:
            pattern, param_types = compile_path(prefix + router.prefix + record.path)
            body_param, body_type, return_type, query_params, header_params = (
                inspect_handler(record.handler, set(param_types.keys()))
            )
            route = Route(
                pattern=pattern,
                param_types=param_types,
                handler=record.handler,
                methods=record.methods,
                body_param=body_param,
                body_type=body_type,
                return_type=return_type,
                query_params=query_params,
                header_params=header_params,
            )
            self._routes.append(route)
            logger.warning(
                "route include regged: %s %s -> %s",
                route.pattern,
                route.param_types,
                getattr(route.handler, "__name__", repr(route.handler)),
            )

        for subrouter in router._subrouters:
            self.include_router(subrouter, prefix + router.prefix)

    async def handle_request(self, request: Request) -> Response:
        try:
            route, path_params = await self.find_handler(request.method, request.path)
        except NotFoundException:
            logger.warning("404 %s %s", request.method, request.path)
            return JSONResponse({"error": "Not Found"}, status_code=404)
        except MethodNotAllowedException:
            logger.warning("405 %s %s", request.method, request.path)
            return JSONResponse({"error": "Method Not Allowed"}, status_code=405)

        # Convert path parameters
        try:
            converted_params = {
                k: route.param_types[k](v) for k, v in path_params.items()
            }
        except (ValueError, TypeError) as exc:
            return JSONResponse(
                {
                    "error": "Validation Error",
                    "detail": [
                        {
                            "loc": ["path"],
                            "msg": str(exc),
                            "type": "validation_error",
                        }
                    ],
                },
                status_code=422,
            )

        # Extract and validate query parameters
        if route.query_params:
            raw_query = request.query_params
            for qname, (qtype, qdefault) in route.query_params.items():
                raw_val = raw_query.get(qname)
                if raw_val is None:
                    if qdefault is REQUIRED:
                        return JSONResponse(
                            {
                                "error": "Validation Error",
                                "detail": [
                                    {
                                        "loc": ["query", qname],
                                        "msg": "Missing required query parameter",
                                        "type": "missing",
                                    }
                                ],
                            },
                            status_code=422,
                        )
                    converted_params[qname] = qdefault
                else:
                    try:
                        if qtype is bool:
                            converted_params[qname] = raw_val.lower() in (
                                "true",
                                "1",
                                "yes",
                                "on",
                            )
                        else:
                            converted_params[qname] = qtype(raw_val)
                    except (ValueError, TypeError):
                        return JSONResponse(
                            {
                                "error": "Validation Error",
                                "detail": [
                                    {
                                        "loc": ["query", qname],
                                        "msg": f"Invalid value for type {qtype.__name__}",
                                        "type": "validation_error",
                                    }
                                ],
                            },
                            status_code=422,
                        )

        # Extract and validate header parameters
        if route.header_params:
            req_headers = request.headers
            for hname, (htype, header_key, hdefault) in route.header_params.items():
                raw_val = req_headers.get(header_key.lower())
                if raw_val is None:
                    if hdefault is ...:
                        return JSONResponse(
                            {
                                "error": "Validation Error",
                                "detail": [
                                    {
                                        "loc": ["header", header_key],
                                        "msg": "Missing required header",
                                        "type": "missing",
                                    }
                                ],
                            },
                            status_code=422,
                        )
                    converted_params[hname] = hdefault
                else:
                    try:
                        converted_params[hname] = htype(raw_val)
                    except (ValueError, TypeError):
                        return JSONResponse(
                            {
                                "error": "Validation Error",
                                "detail": [
                                    {
                                        "loc": ["header", header_key],
                                        "msg": f"Invalid value for type {htype.__name__}",
                                        "type": "validation_error",
                                    }
                                ],
                            },
                            status_code=422,
                        )

        # Decode and validate request body if handler expects a body parameter
        if route.body_param and route.body_type:
            try:
                body = await decode_body(request, route.body_type)
            except ValidationError as exc:
                logger.warning(
                    "422 %s %s: %s", request.method, request.path, exc.detail
                )
                return JSONResponse(
                    {"error": "Validation Error", "detail": exc.errors},
                    status_code=422,
                )
            converted_params[route.body_param] = body

        try:
            result = await route.handler(request, **converted_params)
        except HTTPException as exc:
            logger.warning(
                "%d %s %s: %s",
                exc.status_code,
                request.method,
                request.path,
                exc.detail,
            )
            return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

        # Convert handler return value to a Response
        response = process_response(result, route.return_type)

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
