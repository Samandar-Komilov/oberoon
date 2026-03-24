"""
Bookstore API — a single app showcasing all oberoon features.

    uvicorn examples.bookstore.app:app --reload

Features demonstrated:
─────────────────────────────────────────────────────────────────

1. Body validation       POST /api/books with CreateBook (Field constraints)
2. Query params          GET  /api/books?genre=sci-fi&min_rating=4.0&page=1&limit=5
3. Header params         POST /api/books with Authorization + X-Request-Id headers
4. Path params           GET  /api/books/1, DELETE /api/books/1
5. Typed responses       -> Book, -> list[Book], -> dict, -> None (204)
6. Router composition    books_router + reviews_router under /api prefix
7. Exception handlers    BookstoreError -> 409, HTTPException -> 4xx, unhandled -> 500
8. Debug mode            debug=True exposes exception details in 500 responses

Example requests:
─────────────────────────────────────────────────────────────────

# List books with filters
curl "localhost:8000/api/books?genre=sci-fi&min_rating=4.0"
curl "localhost:8000/api/books?available_only=true&limit=3"

# Get a single book
curl localhost:8000/api/books/1

# Create a book (auth required)
curl -X POST localhost:8000/api/books \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer secret" \\
  -H "X-Request-Id: req-123" \\
  -d '{"title": "Snow Crash", "author": "Neal Stephenson", "year": 1992, "genre": "sci-fi"}'

# Update a book
curl -X PUT localhost:8000/api/books/1 \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer secret" \\
  -d '{"rating": 4.9}'

# Delete a book (returns 204)
curl -X DELETE localhost:8000/api/books/3 -H "Authorization: Bearer secret"

# Add a review
curl -X POST localhost:8000/api/books/1/reviews \\
  -H "Content-Type: application/json" \\
  -d '{"reviewer": "Dave", "text": "The spice must flow!", "stars": 5}'

# List reviews with filter
curl "localhost:8000/api/books/1/reviews?min_stars=4"

# Validation errors (422)
curl -X POST localhost:8000/api/books \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer secret" \\
  -d '{"title": "", "author": "X", "year": 1200, "genre": "a"}'

# Missing auth header (422)
curl -X POST localhost:8000/api/books \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Test", "author": "X", "year": 2000, "genre": "a"}'

# Domain error (409 via custom exception handler)
curl localhost:8000/api/borrow/3

# Not found (404)
curl localhost:8000/api/books/999

# Unhandled crash (500 with debug detail)
curl localhost:8000/api/crash
"""

from typing import Annotated

from oberoon import Oberoon, Router, Query, Request, HTTPException

from examples.bookstore import db
from examples.bookstore.errors import OutOfStockError, register_error_handlers
from examples.bookstore.routes import books_router, reviews_router

app = Oberoon(debug=True)

# Register custom exception handlers
register_error_handlers(app)


# ── Top-level routes ────────────────────────────────────────────────────────


@app.get("/health")
async def health(request: Request) -> dict:
    return {"status": "ok", "books": len(db.books), "reviews": len(db.reviews)}


# ── API router (composes sub-routers) ──────────────────────────────────────

api = Router(prefix="/api")


@api.get("/borrow/{book_id:int}")
async def borrow_book(request: Request, book_id: int) -> dict:
    """Demonstrates custom domain exception -> custom handler."""
    if book_id not in db.books:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    book = db.books[book_id]
    if not book.available:
        raise OutOfStockError(book.title)

    return {"message": f"'{book.title}' borrowed successfully"}


@api.get("/search")
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1)],
    field: Annotated[str, Query()] = "title",
) -> list[dict]:
    """Search books by title or author — demonstrates required query param."""
    results = []
    for book in db.books.values():
        value = getattr(book, field, "")
        if q.lower() in str(value).lower():
            results.append({"id": book.id, "title": book.title, "author": book.author})
    return results


@api.get("/crash")
async def crash(request: Request) -> dict:
    """Demonstrates 500 with debug=True showing exception details."""
    raise RuntimeError("this is an unhandled error")


# ── Mount routers ──────────────────────────────────────────────────────────

api.include_router(books_router)
api.include_router(reviews_router)
app.include_router(api)
