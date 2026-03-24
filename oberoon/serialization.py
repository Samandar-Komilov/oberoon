"""Handler introspection, request body decoding, and response processing.

This module powers the automatic msgspec integration:
- Inspects handler signatures to find body, query, and header parameters
- Decodes and validates request bodies against msgspec.Struct types
- Converts handler return values into proper Response objects based on return type
"""

import inspect
import types
import typing
from typing import Any, Union, get_type_hints

import msgspec
import msgspec.json

from oberoon.exceptions import ValidationError
from oberoon.params import _HeaderMarker
from oberoon.requests import Request
from oberoon.responses import Response

# Sentinel for "no return type annotation"
_MISSING = object()

# Sentinel for "required parameter" (no default)
REQUIRED = object()

# Types that are auto-detected as query parameters
_SIMPLE_TYPES = (str, int, float, bool)


def _unwrap_optional(ann: Any) -> type | None:
    """If ann is Optional[X] (Union[X, None]), return X. Otherwise return None."""
    origin = typing.get_origin(ann)
    # Handle both typing.Union and Python 3.10+ X | None
    if origin is Union or origin is types.UnionType:
        args = [a for a in typing.get_args(ann) if a is not type(None)]
        if len(args) == 1 and args[0] in _SIMPLE_TYPES:
            return args[0]
    return None


def inspect_handler(
    handler, path_param_names: set[str]
) -> tuple[
    str | None,  # body_param
    type | None,  # body_type
    Any,  # return_type
    dict[str, tuple[type, Any]],  # query_params: {name: (type, default)}
    dict[
        str, tuple[type, str, Any]
    ],  # header_params: {name: (type, header_name, default)}
]:
    """Inspect a handler's signature to extract parameter metadata.

    Resolution order per parameter:
    1. Type is Request → skip
    2. Name is in path_param_names → skip
    3. Default is Header() marker → header param
    4. Type is msgspec.Struct subclass → body param
    5. Type is simple (str/int/float/bool/Optional) → query param
    """
    try:
        hints = get_type_hints(handler, include_extras=True)
    except Exception:
        return None, None, _MISSING, {}, {}

    sig = inspect.signature(handler)

    body_param = None
    body_type = None
    query_params: dict[str, tuple[type, Any]] = {}
    header_params: dict[str, tuple[type, str, Any]] = {}

    for name, param in sig.parameters.items():
        # Skip path parameters
        if name in path_param_names:
            continue

        ann = hints.get(name)
        if ann is None:
            continue

        # 1. Skip Request parameters
        if ann is Request or (isinstance(ann, type) and issubclass(ann, Request)):
            continue

        # 3. Header parameters (detected by default value)
        if isinstance(param.default, _HeaderMarker):
            marker = param.default
            header_name = marker.alias or name.replace("_", "-")
            param_type = ann if ann in _SIMPLE_TYPES else str
            header_params[name] = (param_type, header_name, marker.default)
            continue

        # 4. Body parameters (msgspec.Struct subclass)
        if isinstance(ann, type) and issubclass(ann, msgspec.Struct):
            if body_param is not None:
                raise TypeError(
                    f"Handler '{handler.__name__}' has multiple body parameters: "
                    f"'{body_param}' and '{name}'"
                )
            body_param = name
            body_type = ann
            continue

        # 5. Query parameters (simple types)
        base_type = None
        if ann in _SIMPLE_TYPES:
            base_type = ann
        else:
            base_type = _unwrap_optional(ann)

        if base_type is not None:
            default = param.default
            if default is inspect.Parameter.empty:
                query_params[name] = (base_type, REQUIRED)
            else:
                query_params[name] = (base_type, default)

    return_type = hints.get("return", _MISSING)
    return body_param, body_type, return_type, query_params, header_params


async def decode_body(request: Request, body_type: type) -> Any:
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


def process_response(result: Any, return_type: Any) -> Response:
    """Convert a handler's return value into a Response object.

    Rules:
    - Response instance → pass through as-is
    - return type is None → 204 No Content
    - return type is a Response subclass → type-check only
    - return type is set → validate/convert result via msgspec, encode to JSON
    - no return type annotation → encode to JSON without validation
    """
    # Already a Response? Pass through.
    if isinstance(result, Response):
        return result

    # Return type is NoneType (-> None) → 204 No Content
    if return_type is type(None):
        return Response(status_code=204)

    # Return type is a Response subclass → handler should have returned one
    if (
        return_type is not _MISSING
        and isinstance(return_type, type)
        and issubclass(return_type, Response)
    ):
        raise TypeError(
            f"Handler declared return type {return_type.__name__} "
            f"but returned {type(result).__name__}"
        )

    # No return type annotation → encode as-is (like FastAPI)
    if return_type is _MISSING:
        encoded = msgspec.json.encode(result)
        resp = Response(status_code=200)
        resp.set_body(encoded, "application/json")
        return resp

    # Has a return type → validate via msgspec.convert, then encode
    try:
        validated = msgspec.convert(result, return_type)
    except Exception as e:
        raise TypeError(f"Response validation failed for type {return_type}: {e}")

    encoded = msgspec.json.encode(validated)
    resp = Response(status_code=200)
    resp.set_body(encoded, "application/json")
    return resp
