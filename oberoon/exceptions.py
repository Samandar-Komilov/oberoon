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
