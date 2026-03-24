from typing import Callable

from oberoon.logging import get_logger
from oberoon.requests import Request
from oberoon.responses import Response
from oberoon.exceptions import (
    HTTPException,
    NotFoundException,
    MethodNotAllowedException,
    ValidationError,
    default_error_handler,
    default_http_handler,
    default_validation_handler,
    debug_error_handler,
)
from oberoon.routing import Route, Router, RoutingMixin, compile_path
import msgspec

from oberoon.serialization import (
    inspect_handler_signature,
    decode_body,
    serialize_response,
)

logger = get_logger("core")


class Oberoon(RoutingMixin):
    def __init__(self, debug: bool = False, title: str = "Oberoon API"):
        self.debug = debug
        self.title = title
        self._routes: list[Route] = list()
        self._exception_handlers: dict[type, Callable] = {}

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

    def _build_route(
        self, pattern, handler, methods: list[str], param_types: dict
    ) -> Route:
        meta = inspect_handler_signature(handler, set(param_types.keys()))
        return Route(
            pattern=pattern,
            param_types=param_types,
            handler=handler,
            methods=methods,
            body_param=meta.body_param,
            body_type=meta.body_type,
            return_type=meta.return_type,
            query_type=meta.query_type,
            query_field_names=meta.query_field_names,
            header_type=meta.header_type,
            header_field_names=meta.header_field_names,
        )

    def route(self, path: str, methods: list[str] | None = None):
        def decorator(handler):
            pattern, param_types = compile_path(path)
            route = self._build_route(pattern, handler, methods or ["GET"], param_types)
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
            route = self._build_route(
                pattern, record.handler, record.methods, param_types
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
        except (NotFoundException, MethodNotAllowedException) as exc:
            exc_handler = self._lookup_exception_handler(exc)
            return exc_handler(request, exc)

        try:
            # Convert path params
            try:
                converted_params = {
                    k: route.param_types[k](v) for k, v in path_params.items()
                }
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    errors=[
                        {"loc": ["path"], "msg": str(e), "type": "validation_error"}
                    ]
                )

            # Validate and inject query params
            if route.query_type:
                try:
                    query_obj = msgspec.convert(
                        request.query_params, route.query_type, strict=False
                    )
                except (msgspec.ValidationError, msgspec.DecodeError) as e:
                    raise ValidationError(
                        errors=[
                            {
                                "loc": ["query"],
                                "msg": str(e),
                                "type": "validation_error",
                            }
                        ]
                    )
                for name in route.query_field_names:
                    converted_params[name] = getattr(query_obj, name)

            # Validate and inject header params
            if route.header_type:
                # Map underscore field names to hyphenated header keys
                header_data = {}
                for name in route.header_field_names:
                    header_key = name.replace("_", "-")
                    if header_key in request.headers:
                        header_data[name] = request.headers[header_key]
                try:
                    header_obj = msgspec.convert(
                        header_data, route.header_type, strict=False
                    )
                except (msgspec.ValidationError, msgspec.DecodeError) as e:
                    raise ValidationError(
                        errors=[
                            {
                                "loc": ["header"],
                                "msg": str(e),
                                "type": "validation_error",
                            }
                        ]
                    )
                for name in route.header_field_names:
                    converted_params[name] = getattr(header_obj, name)

            # Decode and validate request body
            if route.body_param and route.body_type:
                body = await decode_body(request, route.body_type)
                converted_params[route.body_param] = body

            # Call handler
            result = await route.handler(request, **converted_params)

            # Serialize response
            response = serialize_response(result, route.return_type)

        except Exception as exc:
            logger.warning(
                "%s %s %s: %s",
                getattr(exc, "status_code", 500),
                request.method,
                request.path,
                exc,
            )
            exc_handler = self._lookup_exception_handler(exc)
            return exc_handler(request, exc)

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

    def exception_handler(self, exc_class: type):
        def decorator(handler):
            self._exception_handlers[exc_class] = handler
            return handler

        return decorator

    def _lookup_exception_handler(self, exc: Exception) -> Callable:
        # Check user-registered handlers first, walking MRO for specificity
        for cls in type(exc).__mro__:
            if cls in self._exception_handlers:
                return self._exception_handlers[cls]

        # Fall back to defaults
        if isinstance(exc, ValidationError):
            return default_validation_handler
        if isinstance(exc, HTTPException):
            return default_http_handler
        if self.debug:
            return debug_error_handler
        return default_error_handler
