"""In-memory mock database."""

from examples.bookstore.models import Book, Review

books: dict[int, Book] = {
    1: Book(
        id=1,
        title="Dune",
        author="Frank Herbert",
        year=1965,
        genre="sci-fi",
        rating=4.7,
        available=True,
    ),
    2: Book(
        id=2,
        title="1984",
        author="George Orwell",
        year=1949,
        genre="dystopia",
        rating=4.5,
        available=True,
    ),
    3: Book(
        id=3,
        title="Neuromancer",
        author="William Gibson",
        year=1984,
        genre="sci-fi",
        rating=4.2,
        available=False,
    ),
    4: Book(
        id=4,
        title="The Great Gatsby",
        author="F. Scott Fitzgerald",
        year=1925,
        genre="classic",
        rating=4.0,
        available=True,
    ),
    5: Book(
        id=5,
        title="Brave New World",
        author="Aldous Huxley",
        year=1932,
        genre="dystopia",
        rating=4.3,
        available=True,
    ),
}

reviews: dict[int, Review] = {
    1: Review(
        id=1,
        book_id=1,
        reviewer="Alice",
        text="A masterpiece of science fiction.",
        stars=5,
    ),
    2: Review(id=2, book_id=1, reviewer="Bob", text="Dense but rewarding.", stars=4),
    3: Review(
        id=3, book_id=2, reviewer="Charlie", text="Terrifyingly relevant.", stars=5
    ),
}

next_book_id = 6
next_review_id = 4
