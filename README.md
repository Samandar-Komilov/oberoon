# Oberoon

![purpose](https://img.shields.io/badge/purpose-learning-green)
![PyPI - Version](https://img.shields.io/pypi/v/oberoon)

A lightweight ASGI web framework for Python, inspired by Starlette. Built from scratch as a learning project to understand the internals of modern async web frameworks.

**Source code**: https://github.com/Samandar-Komilov/oberoon

## Features

- Pure ASGI interface — works with Uvicorn, Hypercorn, Daphne
- Async request handlers
- Path parameters with type conversion (`{id:int}`, `{name:str}`, `{filepath:path}`)
- Method-based routing (`@app.get`, `@app.post`, etc.)
- Attachable routers with prefix mounting (WIP)
- Structured stdout logging
- Zero magic — small codebase, easy to read and learn from

## Installation

```bash
pip install oberoon
```

## Quick Start

```python
from oberoon import Oberoon, Request, Response, setup_logging

setup_logging()

app = Oberoon()


@app.get("/hello")
async def hello(request: Request) -> Response:
    return Response(200, body=b"Hello!", content_type="text/plain")


@app.get("/users/{user_id:int}")
async def get_user(request: Request, user_id: int) -> Response:
    return Response(200, body=f"User {user_id}".encode(), content_type="text/plain")
```

Run with any ASGI server:

```bash
uvicorn app:app --reload
```

## Roadmap

- [x] ASGI core with lifespan support
- [x] Regex-based routing with path parameter converters
- [x] Structured logging
- [ ] Attachable routers (`app.include_router`)
- [ ] Middleware support
- [ ] WebSocket support
- [ ] Static files and templates

## Development

```bash
git clone https://github.com/Samandar-Komilov/oberoon.git
cd oberoon
pip install -e ".[dev]"
pytest tests/
```
