import logging
import sys
from typing import Literal

LOG_FORMAT = "%(levelname)-8s %(name)-20s %(message)s"
LOG_FORMAT_VERBOSE = "%(asctime)s %(levelname)-8s %(name)-20s %(message)s"


def setup_logging(
    level: int = logging.DEBUG,
    fmt: Literal["default", "verbose"] = "default",
) -> None:
    """Configure logging for the oberoon framework.

    Sets up a stdout StreamHandler on the root 'oberoon' logger.
    Call once at startup; subsequent calls are no-ops (handler guard).
    """
    root = logging.getLogger("oberoon")

    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(LOG_FORMAT_VERBOSE if fmt == "verbose" else LOG_FORMAT)
    )
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'oberoon' namespace.

    Usage: logger = get_logger("routing")  ->  logger named 'oberoon.routing'
    """
    return logging.getLogger(f"oberoon.{name}")
