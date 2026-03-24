"""Parameter markers for Query and Header extraction."""


class Query:
    """Marker for query string parameters.

    Usage with Annotated::

        from oberoon import Query
        from typing import Annotated

        @app.get("/users")
        async def list_users(
            request: Request,
            page: Annotated[int, Query(ge=1)] = 1,
            limit: Annotated[int, Query(ge=1, le=100)] = 10,
        ) -> list[User]:
            ...

    Constraint kwargs (ge, le, gt, lt, min_length, max_length, pattern)
    are forwarded to msgspec.Meta for validation.
    """

    def __init__(self, **constraints):
        self.constraints = constraints

    def __repr__(self) -> str:
        if self.constraints:
            kw = ", ".join(f"{k}={v!r}" for k, v in self.constraints.items())
            return f"Query({kw})"
        return "Query()"


class Header:
    """Marker for HTTP header parameters.

    Usage with Annotated::

        from oberoon import Header
        from typing import Annotated

        @app.get("/protected")
        async def protected(
            request: Request,
            authorization: Annotated[str, Header()],
            x_request_id: Annotated[str, Header()] = "",
        ) -> dict:
            ...

    Python underscores are auto-converted to hyphens for header lookup
    (e.g., ``x_request_id`` matches the ``x-request-id`` header).

    Constraint kwargs are forwarded to msgspec.Meta for validation.
    """

    def __init__(self, **constraints):
        self.constraints = constraints

    def __repr__(self) -> str:
        if self.constraints:
            kw = ", ".join(f"{k}={v!r}" for k, v in self.constraints.items())
            return f"Header({kw})"
        return "Header()"
