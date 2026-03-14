from dataclasses import dataclass
import re
from typing import Callable

from oberoon.logging import get_logger

logger = get_logger("routing")


@dataclass
class Route:
    pattern: re.Pattern
    param_types: dict[str, type]
    handler: Callable
    methods: set[str]


CONVERTERS = {
    "str": r"[^\s/]+",  # any char except space or slash
    "int": r"[0-9]+",  # any integer
    "path": r".+",  # any char
}


def compile_path(path: str) -> tuple[re.Pattern, dict[str, type]]:
    """
    "/users/{user_id:int}" -> (re.compile(r"^/users/(?P<user_id>[0-9]+)$"), {"user_id": int})
    "/items/{name}"        -> (re.compile(r"^/items/(?P<name>[^/]+)$"), {"name": str})
    """
    param_types = {}

    def replace(match):
        name, _, converter = match.group(1).partition(":")
        converter = converter or "str"
        param_types[name] = int if converter == "int" else str
        return f"(?P<{name}>{CONVERTERS[converter]})"

    pattern = re.sub(r"\{([^}]+)\}", replace, path)
    compiled = re.compile(f"^{pattern}$")
    logger.debug("compiled path: %s -> %s", path, compiled.pattern)
    return compiled, param_types
