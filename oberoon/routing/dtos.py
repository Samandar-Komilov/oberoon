from dataclasses import dataclass
import re
from typing import Callable


@dataclass
class Route:
    """Regex compiled, final routes"""

    pattern: re.Pattern
    param_types: dict[str, type]
    handler: Callable
    methods: list[str]


@dataclass
class RouteRecord:
    """Uncompiled raw routes, collected and compiled at `include_router()` time"""

    path: str
    handler: Callable
    methods: list[str]
