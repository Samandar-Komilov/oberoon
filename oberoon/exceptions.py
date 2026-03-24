from oberoon.requests import Request
from oberoon.responses import JSONResponse, Response

# Classes


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Not Found"):
        super().__init__(status_code=404, detail=detail)


class MethodNotAllowedException(HTTPException):
    def __init__(self, detail: str = "Method Not Allowed"):
        super().__init__(status_code=405, detail=detail)


class ValidationError(HTTPException):
    """Raised when request body fails msgspec validation.

    Produces a 422 Unprocessable Entity response with structured error details.
    """

    def __init__(self, errors: list[dict]):
        self.errors = errors
        detail = "; ".join(e.get("msg", "") for e in errors)
        super().__init__(status_code=422, detail=detail)


# Handlers


def default_validation_handler(request: Request, exc: ValidationError) -> Response:
    return JSONResponse(
        {"error": "Validation Error", "detail": exc.errors},
        status_code=422,
    )


def default_http_handler(request: Request, exc: HTTPException) -> Response:
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


def default_error_handler(request: Request, exc: Exception) -> Response:
    return JSONResponse({"error": "Internal Server Error"}, status_code=500)


def debug_error_handler(request: Request, exc: Exception) -> Response:
    return JSONResponse(
        {"error": "Internal Server Error", "detail": f"{type(exc).__name__}: {exc}"},
        status_code=500,
    )
