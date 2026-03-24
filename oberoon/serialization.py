"""Handler introspection, request body decoding, and response processing.

This module powers the automatic msgspec integration:
- Inspects handler signatures to find body parameters (msgspec.Struct types)
- Decodes and validates request bodies against those types
- Detects Query/Header annotated parameters and builds dynamic validation structs
- Converts handler return values into proper Response objects based on return type
"""

import inspect
from dataclasses import dataclass, field
from typing import Annotated, Any, get_args, get_origin, get_type_hints

import msgspec

from oberoon.exceptions import ValidationError
from oberoon.requests.params import Header, Query
from oberoon.requests import Request
from oberoon.responses import Response

Field = msgspec.Meta

_MISSING = object()


class BaseModel(msgspec.Struct):
    """Base model for request/response schemas.

    A friendly wrapper around msgspec.Struct with convenience methods.

    Usage::

        from oberoon import BaseModel, Field
        from typing import Annotated

        class CreateUser(BaseModel):
            name: Annotated[str, Field(min_length=1, max_length=100)]
            email: str
            age: Annotated[int, Field(ge=0, le=150)] = 0

    Use ``Annotated[type, Field(...)]`` for constraints (min_length, max_length,
    ge, le, gt, lt, pattern, title, description).
    """

    def to_dict(self) -> dict:
        """Convert this model instance to a plain dictionary."""
        return msgspec.structs.asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create a validated model instance from a dictionary."""
        return msgspec.convert(data, cls)


@dataclass
class HandlerMeta:
    """Metadata extracted from handler signature at registration time."""

    body_param: str | None = None
    body_type: type | None = None
    return_type: Any = None
    query_type: type | None = None
    query_field_names: list[str] = field(default_factory=list)
    header_type: type | None = None
    header_field_names: list[str] = field(default_factory=list)


def _find_marker(annotation, marker_class):
    """Extract a marker instance from an Annotated type, if present.

    Returns (base_type, marker_instance) or (None, None).
    """
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        base_type = args[0]
        for arg in args[1:]:
            if isinstance(arg, marker_class):
                return base_type, arg
    return None, None


def _build_param_struct(name: str, params: list[tuple[str, type, dict, Any]]) -> type:
    """Build a dynamic msgspec Struct from collected parameter definitions.

    Each param is (param_name, base_type, constraints_dict, default_or_MISSING).
    """
    fields = []
    for param_name, base_type, constraints, default in params:
        if constraints:
            annotated_type = Annotated[base_type, msgspec.Meta(**constraints)]
        else:
            annotated_type = base_type

        if default is not _MISSING:
            fields.append((param_name, annotated_type, default))
        else:
            fields.append((param_name, annotated_type))

    return msgspec.defstruct(name, fields)


def inspect_handler_signature(handler, path_param_names: set[str]) -> HandlerMeta:
    """Inspect a handler's signature to extract body, query, header params and return type.

    Returns a HandlerMeta with all extracted metadata.

    Rules:
    - skip path parameters
    - skip `Request` parameters
    - detect `msgspec.Struct` body parameters
    - detect `Annotated[type, Query(...)]` query parameters
    - detect `Annotated[type, Header(...)]` header parameters
    - require return type annotation
    """
    try:
        hints = get_type_hints(handler, include_extras=True)
    except Exception:
        return HandlerMeta()

    sig = inspect.signature(handler)
    meta = HandlerMeta()

    query_params: list[tuple[str, type, dict, Any]] = []
    header_params: list[tuple[str, type, dict, Any]] = []

    body_param = None
    body_type = None

    for name, param in sig.parameters.items():
        if name in path_param_names:
            continue

        annotation = hints.get(name)
        if annotation is None:
            continue

        # Skip Request parameters
        if annotation is Request or (
            isinstance(annotation, type) and issubclass(annotation, Request)
        ):
            continue

        # Check for Query marker
        base_type, query_marker = _find_marker(annotation, Query)
        if query_marker is not None:
            default = (
                _MISSING if param.default is inspect.Parameter.empty else param.default
            )
            query_params.append((name, base_type, query_marker.constraints, default))
            continue

        # Check for Header marker
        base_type, header_marker = _find_marker(annotation, Header)
        if header_marker is not None:
            default = (
                _MISSING if param.default is inspect.Parameter.empty else param.default
            )
            header_params.append((name, base_type, header_marker.constraints, default))
            continue

        # Check for msgspec.Struct body parameter
        if isinstance(annotation, type) and issubclass(annotation, msgspec.Struct):
            if body_param is not None:
                raise TypeError(
                    f"Handler '{handler.__name__}' has multiple body parameters: "
                    f"'{body_param}' and '{name}'"
                )
            body_param = name
            body_type = annotation

    # Build dynamic structs for query/header params
    if query_params:
        meta.query_type = _build_param_struct(
            f"_QueryParams_{handler.__name__}", query_params
        )
        meta.query_field_names = [p[0] for p in query_params]

    if header_params:
        meta.header_type = _build_param_struct(
            f"_HeaderParams_{handler.__name__}", header_params
        )
        meta.header_field_names = [p[0] for p in header_params]

    meta.body_param = body_param
    meta.body_type = body_type

    return_type = hints.get("return", _MISSING)
    if return_type is _MISSING:
        raise TypeError(
            f"Handler '{handler.__name__}' must declare a return type annotation. "
            f"Use '-> None', '-> Response', or '-> YourModel'."
        )
    meta.return_type = return_type

    return meta


async def decode_body(request: Request, body_type: BaseModel) -> Any:
    """Decode and validate the request body against a msgspec.Struct type.

    Raises ValidationError (422) on malformed or invalid JSON.
    """
    raw = await request.body()
    if not raw:
        raise ValidationError(
            errors=[
                {"loc": ["body"], "msg": "Request body is required", "type": "missing"}
            ]
        )

    try:
        return msgspec.json.decode(raw, type=body_type)
    except msgspec.ValidationError as e:
        raise ValidationError(
            errors=[{"loc": ["body"], "msg": str(e), "type": "validation_error"}]
        )
    except msgspec.DecodeError as e:
        raise ValidationError(
            errors=[{"loc": ["body"], "msg": str(e), "type": "decode_error"}]
        )


def serialize_response(result: Any, return_type: Any) -> Response:
    """Convert a handler's return value into a Response object.

    Rules:
    - Response instance → pass through as-is
    - return type is None → 204 No Content
    - return type is a Response subclass → type-check only
    - return type is set → validate/convert result via msgspec, encode to JSON
    """
    if isinstance(result, Response):
        return result

    if return_type is type(None):
        return Response(status_code=204)

    if (
        return_type is not _MISSING
        and isinstance(return_type, type)
        and issubclass(return_type, Response)
    ):
        raise TypeError(
            f"Handler declared return type {return_type.__name__} "
            f"but returned {type(result).__name__}"
        )

    try:
        validated = msgspec.convert(result, return_type)
    except Exception as e:
        raise TypeError(f"Response validation failed for type {return_type}: {e}")

    encoded = msgspec.json.encode(validated)
    resp = Response(status_code=200)
    resp.set_body(encoded, "application/json")
    return resp
