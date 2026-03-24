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
    # msgspec fields (populated by inspect_handler_signature)
    body_param: str | None = None
    body_type: type | None = None
    return_type: Any = field(default=None)
    query_type: type | None = None
    query_field_names: list[str] = field(default_factory=list)
    header_type: type | None = None
    header_field_names: list[str] = field(default_factory=list)


@dataclass
class RouteRecord:
    """Uncompiled raw routes, collected and compiled at `include_router()` time"""

    path: str
    handler: Callable
    methods: list[str]
