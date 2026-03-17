class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail


class NotFoundException(HTTPException):
    pass


class MethodNotAllowedException(HTTPException):
    pass
