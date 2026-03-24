"""Book CRUD routes.

Features demonstrated:
- Query params with type coercion and constraints (page, limit, genre, min_rating)
- Header params (authorization, x-request-id)
- Path params with int conversion
- Body validation with Field constraints
- Typed responses (Book, list[Book], dict)
- -> None for 204 No Content
- HTTPException for domain errors
"""

from typing import Annotated

from oberoon import Router, Query, Header, Request, HTTPException

from examples.bookstore import db
from examples.bookstore.models import Book, CreateBook, UpdateBook

router = Router(prefix="/books")


@router.get("/")
async def list_books(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    genre: Annotated[str, Query()] = "",
    min_rating: Annotated[float, Query(ge=0.0, le=5.0)] = 0.0,
    available_only: Annotated[bool, Query()] = False,
) -> list[Book]:
    results = list(db.books.values())
    if genre:
        results = [b for b in results if b.genre == genre]
    if min_rating > 0:
        results = [b for b in results if b.rating >= min_rating]
    if available_only:
        results = [b for b in results if b.available]

    start = (page - 1) * limit
    return results[start : start + limit]


@router.get("/{book_id:int}")
async def get_book(request: Request, book_id: int) -> Book:
    if book_id not in db.books:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return db.books[book_id]


@router.post("/")
async def create_book(
    request: Request,
    body: CreateBook,
    authorization: Annotated[str, Header()],
    x_request_id: Annotated[str, Header()] = "",
) -> Book:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    book = Book(
        id=db.next_book_id,
        title=body.title,
        author=body.author,
        year=body.year,
        genre=body.genre,
        rating=body.rating,
        available=True,
    )
    db.books[db.next_book_id] = book
    db.next_book_id += 1
    return book


@router.put("/{book_id:int}")
async def update_book(
    request: Request,
    book_id: int,
    body: UpdateBook,
    authorization: Annotated[str, Header()],
) -> Book:
    if book_id not in db.books:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    existing = db.books[book_id]
    updated = Book(
        id=existing.id,
        title=body.title if body.title else existing.title,
        author=body.author if body.author else existing.author,
        year=body.year if body.year else existing.year,
        genre=body.genre if body.genre else existing.genre,
        rating=body.rating if body.rating >= 0 else existing.rating,
        available=existing.available,
    )
    db.books[book_id] = updated
    return updated


@router.delete("/{book_id:int}")
async def delete_book(
    request: Request,
    book_id: int,
    authorization: Annotated[str, Header()],
) -> None:
    if book_id not in db.books:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    del db.books[book_id]
