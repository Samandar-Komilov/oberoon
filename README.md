# Oberoon

![purpose](https://img.shields.io/badge/purpose-learning-green)
![PyPI - Version](https://img.shields.io/pypi/v/oberoon)

A lightweight ASGI web framework for Python, inspired by Starlette and FastAPI. Built from scratch as a learning project to understand the internals of modern async web frameworks.

**Source code**: https://github.com/Samandar-Komilov/oberoon

## Features

- Pure ASGI interface — works with Uvicorn, Hypercorn, Daphne
- Async request handlers with automatic JSON serialization via [msgspec](https://jcristharif.com/msgspec/)
- Request body validation with `BaseModel` and `Annotated[type, Field(...)]` constraints
- Query parameter validation with type coercion — `Annotated[int, Query(ge=1)]`
- Header parameter validation — `Annotated[str, Header()]` with underscore-to-hyphen mapping
- Path parameters with type conversion (`{id:int}`, `{name:str}`, `{filepath:path}`)
- Method-based routing (`@app.get`, `@app.post`, etc.)
- Nested routers with prefix mounting (`app.include_router`)
- Exception handler registry (`@app.exception_handler`) with debug mode
- Typed return annotations — auto-serialization for `-> Book`, `-> list[Book]`, `-> dict`, `-> None` (204)
- Zero magic — small codebase, easy to read and learn from

## Installation

```bash
pip install oberoon
```

## Quick Start

```python
from typing import Annotated

from oberoon import Oberoon, BaseModel, Field, Query, Header, Request

app = Oberoon()


class Book(BaseModel):
    id: int
    title: str
    author: str


class CreateBook(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    author: Annotated[str, Field(min_length=1, max_length=100)]


books = {1: Book(id=1, title="Dune", author="Frank Herbert")}
next_id = 2


@app.get("/books")
async def list_books(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[Book]:
    items = list(books.values())
    start = (page - 1) * limit
    return items[start : start + limit]


@app.get("/books/{book_id:int}")
async def get_book(request: Request, book_id: int) -> Book:
    from oberoon import HTTPException
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    return books[book_id]


@app.post("/books")
async def create_book(
    request: Request,
    body: CreateBook,
    authorization: Annotated[str, Header()],
) -> Book:
    global next_id
    book = Book(id=next_id, title=body.title, author=body.author)
    books[next_id] = book
    next_id += 1
    return book


@app.delete("/books/{book_id:int}")
async def delete_book(request: Request, book_id: int) -> None:
    books.pop(book_id, None)
```

Run with any ASGI server:

```bash
uvicorn app:app --reload
```

```bash
# List with pagination
curl "localhost:8000/books?page=1&limit=5"

# Create (body + header validation)
curl -X POST localhost:8000/books \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{"title": "1984", "author": "George Orwell"}'

# Validation error (422)
curl -X POST localhost:8000/books \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{"title": "", "author": "X"}'

# Delete (204 No Content)
curl -X DELETE localhost:8000/books/1
```

## Validation

oberoon uses [msgspec](https://jcristharif.com/msgspec/) for high-performance validation and serialization.

### Request body

```python
class CreateUser(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: str
    age: Annotated[int, Field(ge=0, le=150)] = 0
```

### Query parameters

```python
@app.get("/search")
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1)],
    page: Annotated[int, Query(ge=1)] = 1,
) -> list[dict]:
    ...
```

### Header parameters

```python
@app.get("/protected")
async def protected(
    request: Request,
    authorization: Annotated[str, Header()],
    x_request_id: Annotated[str, Header()] = "",  # maps to x-request-id
) -> dict:
    ...
```

## Error Handling

All errors return consistent JSON responses. Register custom handlers with `@app.exception_handler`:

```python
app = Oberoon(debug=True)  # debug=True includes exception details in 500 responses

class RateLimitError(Exception):
    pass

@app.exception_handler(RateLimitError)
def handle_rate_limit(request, exc):
    return JSONResponse({"error": "Too many requests"}, status_code=429)
```

Default error responses:

| Status | Body |
|--------|------|
| 404 | `{"error": "Not Found"}` |
| 405 | `{"error": "Method Not Allowed"}` |
| 422 | `{"error": "Validation Error", "detail": [...]}` |
| 500 | `{"error": "Internal Server Error"}` |

## Routers

```python
from oberoon import Router

api = Router(prefix="/api")
books = Router(prefix="/books")

@books.get("/")
async def list_books(request: Request) -> list[dict]:
    return [{"title": "Dune"}]

api.include_router(books)    # /api/books/
app.include_router(api)
```

## Roadmap

- [x] ASGI core with lifespan support
- [x] Regex-based routing with path parameter converters
- [x] Structured logging
- [x] Attachable routers with prefix nesting
- [x] msgspec-powered request/response serialization
- [x] Body, query, and header validation with constraints
- [x] Exception handler registry with debug mode
- [ ] Middleware support
- [ ] WebSocket support
- [ ] Static files and templates
- [ ] OpenAPI schema generation

## Development

```bash
git clone https://github.com/Samandar-Komilov/oberoon.git
cd oberoon
pip install -e ".[dev]"
pytest tests/
```
