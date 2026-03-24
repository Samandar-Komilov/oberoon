"""Parameter markers for header injection.

Usage::

    from oberoon import Header

    @app.get("/items")
    async def get_items(request: Request, x_token: str = Header()) -> dict:
        # x_token extracted from the "x-token" header
        ...

    @app.get("/items")
    async def get_items(
        request: Request,
        auth: str = Header(alias="authorization"),
        x_req_id: str = Header(default="unknown"),
    ) -> dict:
        ...
"""


class _HeaderMarker:
    """Sentinel returned by Header(). Detected during handler introspection."""

    __slots__ = ("alias", "default")

    def __init__(self, *, alias: str | None = None, default=...):
        self.alias = alias
        self.default = default

    def __repr__(self):
        parts = []
        if self.alias is not None:
            parts.append(f"alias={self.alias!r}")
        if self.default is not ...:
            parts.append(f"default={self.default!r}")
        return f"Header({', '.join(parts)})"


def Header(*, alias: str | None = None, default=...):
    """Mark a handler parameter as a header value.

    The header name is derived from the parameter name by replacing ``_`` with ``-``.
    Use ``alias`` to override the header name explicitly.

    Args:
        alias: Custom header name (e.g. ``"authorization"``).
        default: Default value if header is absent. Omit to make the header required.
    """
    return _HeaderMarker(alias=alias, default=default)
