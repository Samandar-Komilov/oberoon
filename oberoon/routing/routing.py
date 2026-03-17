from __future__ import annotations

from abc import abstractmethod
from typing import Callable

from oberoon.routing.dtos import RouteRecord
from oberoon.logging import get_logger

logger = get_logger("routing")


class RoutingMixin:
    @abstractmethod
    def route(self, path: str, methods: list[str] | None = None) -> Callable:
        raise NotImplementedError

    def get(self, path: str) -> Callable:
        return self.route(path, methods=["GET"])

    def post(self, path: str) -> Callable:
        return self.route(path, methods=["POST"])

    def put(self, path: str) -> Callable:
        return self.route(path, methods=["PUT"])

    def patch(self, path: str) -> Callable:
        return self.route(path, methods=["PATCH"])

    def delete(self, path: str) -> Callable:
        return self.route(path, methods=["DELETE"])


class Router(RoutingMixin):
    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._route_records: list[RouteRecord] = []
        self._subrouters: list[Router] = []

    def route(self, path: str, methods: list[str] | None = None):
        def decorator(handler):
            route_record = RouteRecord(
                path=path,
                handler=handler,
                methods=methods or ["GET"],
            )
            self._route_records.append(route_record)
            logger.warning(
                "router: route registered: %s %s -> %s",
                methods,
                path,
                getattr(handler, "__name__", repr(handler)),
            )
            return handler

        return decorator

    def include_router(self, router: Router):
        self._subrouters.append((router))

    @property
    def prefix(self):
        return self._prefix
