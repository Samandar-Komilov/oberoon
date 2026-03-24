"""Custom domain exceptions and handlers.

Features demonstrated:
- @app.exception_handler() for domain-specific exceptions
- Standard error envelope across all error types
"""

from oberoon import Oberoon, JSONResponse


class BookstoreError(Exception):
    """Base for all bookstore domain errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code


class OutOfStockError(BookstoreError):
    def __init__(self, book_title: str):
        super().__init__(
            message=f"'{book_title}' is currently unavailable",
            code="OUT_OF_STOCK",
        )


class DuplicateBookError(BookstoreError):
    def __init__(self, title: str):
        super().__init__(
            message=f"A book titled '{title}' already exists",
            code="DUPLICATE_BOOK",
        )


def register_error_handlers(app: Oberoon):
    @app.exception_handler(BookstoreError)
    def handle_bookstore_error(request, exc):
        return JSONResponse(
            {"error": exc.message, "code": exc.code},
            status_code=409,
        )
