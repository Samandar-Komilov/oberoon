from dataclasses import dataclass, field
import re
from typing import Any, Callable


@dataclass
class Route:
    """Regex compiled, final routes"""

    pattern: re.Pattern
    param_types: dict[str, type]
    handler: Callable
    methods: list[str]
    # msgspec integration fields (populated by inspect_handler)
    body_param: str | None = None
    body_type: type | None = None
    return_type: Any = field(default=None)
    query_params: dict[str, tuple[type, Any]] = field(default_factory=dict)
    header_params: dict[str, tuple[type, str, Any]] = field(default_factory=dict)


@dataclass
class RouteRecord:
    """Uncompiled raw routes, collected and compiled at `include_router()` time"""

    path: str
    handler: Callable
    methods: list[str]
