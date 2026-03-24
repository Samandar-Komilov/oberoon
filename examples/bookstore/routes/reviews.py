"""Review routes nested under /books/{book_id}/reviews.

Features demonstrated:
- Nested router composition
- Combined path params + body validation + query params
- Cross-entity validation (book must exist)
"""

from typing import Annotated

from oberoon import Router, Query, Request, HTTPException

from examples.bookstore import db
from examples.bookstore.models import Review, CreateReview

router = Router(prefix="/books")


@router.get("/{book_id:int}/reviews")
async def list_reviews(
    request: Request,
    book_id: int,
    min_stars: Annotated[int, Query(ge=1, le=5)] = 1,
) -> list[Review]:
    if book_id not in db.books:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    results = [r for r in db.reviews.values() if r.book_id == book_id]
    if min_stars > 1:
        results = [r for r in results if r.stars >= min_stars]
    return results


@router.post("/{book_id:int}/reviews")
async def create_review(
    request: Request,
    book_id: int,
    body: CreateReview,
) -> Review:
    if book_id not in db.books:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    review = Review(
        id=db.next_review_id,
        book_id=book_id,
        reviewer=body.reviewer,
        text=body.text,
        stars=body.stars,
    )
    db.reviews[db.next_review_id] = review
    db.next_review_id += 1
    return review
