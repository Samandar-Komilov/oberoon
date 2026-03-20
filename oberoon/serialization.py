"""Handler introspection, request body decoding, and response processing.

This module powers the automatic msgspec integration:
- Inspects handler signatures to find body parameters (msgspec.Struct types)
- Decodes and validates request bodies against those types
- Converts handler return values into proper Response objects based on return type
"""

import inspect
import warnings
from typing import Any, get_type_hints

import msgspec
import msgspec.json

from oberoon.exceptions import ValidationError
from oberoon.requests import Request
from oberoon.responses import Response

# Sentinel for "no return type annotation"
_MISSING = object()


def inspect_handler(
    handler, path_param_names: set[str]
) -> tuple[str | None, type | None, Any]:
    """Inspect a handler's signature to extract body param and return type.

    Returns:
        (body_param_name, body_type, return_type_or_MISSING)
    """
    try:
        hints = get_type_hints(handler, include_extras=True)
    except Exception:
        return None, None, _MISSING

    sig = inspect.signature(handler)

    body_param = None
    body_type = None

    for name, _param in sig.parameters.items():
        # Skip path parameters
        if name in path_param_names:
            continue

        ann = hints.get(name)
        if ann is None:
            continue

        # Skip Request parameters
        if ann is Request or (isinstance(ann, type) and issubclass(ann, Request)):
            continue

        # Detect msgspec.Struct body parameters
        if isinstance(ann, type) and issubclass(ann, msgspec.Struct):
            if body_param is not None:
                raise TypeError(
                    f"Handler '{handler.__name__}' has multiple body parameters: "
                    f"'{body_param}' and '{name}'"
                )
            body_param = name
            body_type = ann

    return_type = hints.get("return", _MISSING)
    return body_param, body_type, return_type


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
    - no return type annotation → warn, encode to JSON without validation
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

    # No return type annotation → warn, encode as-is
    if return_type is _MISSING:
        if result is not None:
            warnings.warn(
                f"Handler returned {type(result).__name__} without a return type "
                "annotation. Add a return type hint for automatic validation.",
                UserWarning,
                stacklevel=2,
            )
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
