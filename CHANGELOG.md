# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-03-24

### Added

- **msgspec-powered validation** — request body, query params, and header validation using [msgspec](https://jcristharif.com/msgspec/) Structs
- `BaseModel` base class (backed by `msgspec.Struct`) for request/response models
- `Annotated[type, Field(...)]` constraints on body fields (`min_length`, `max_length`, `ge`, `le`, etc.)
- `Annotated[type, Query(...)]` for individual query parameter validation with type coercion
- `Annotated[type, Header()]` for header parameter extraction with underscore-to-hyphen mapping
- Typed return annotations — auto-serialization for `-> Model`, `-> list[Model]`, `-> dict`, `-> None` (204)
- Mandatory return type enforcement at decoration time (`TypeError` if missing)
- **Exception handler registry** — `@app.exception_handler(ExcClass)` with MRO-based lookup
- `Oberoon(debug=True)` flag to expose exception details in 500 responses
- Standardized JSON error envelope across all error types (404, 405, 422, 500)
- `HTTPException`, `ValidationError`, `NotFoundException`, `MethodNotAllowedException` hierarchy
- `JSONResponse` helper for structured JSON responses
- Bookstore example app showcasing all features

### Changed

- Response serialization rewritten to use `msgspec.json.encode` instead of `json.dumps`
- Request body decoding uses `msgspec.json.decode` with schema validation
- Path parameter type conversion errors now return 422 instead of 500

## [0.2.0] - 2026-03-17

### Added

- Pure ASGI interface — full rewrite from WSGI/webob to native ASGI protocol
- Async request handlers (`async def`)
- Regex-based routing with path parameter converters (`{id:int}`, `{name:str}`, `{filepath:path}`)
- Method-based routing decorators (`@app.get`, `@app.post`, `@app.put`, `@app.delete`)
- Attachable `Router` class with prefix mounting (`app.include_router`)
- Recursive nested routers (`api.include_router(books_router)`)
- `Request` wrapper with headers, body, query string parsing
- 404 Not Found and 405 Method Not Allowed handling
- CI/CD pipeline with GitHub Actions
- Structured logging
- Test suite with pytest + anyio

### Changed

- Complete architecture rewrite — WSGI to ASGI
- Dropped webob, whitenoise, and gunicorn dependencies
- Works with any ASGI server (Uvicorn, Hypercorn, Daphne)

### Removed

- WSGI interface and all WSGI-era code
- Django-like route syntax
- Class-based views
- Whitenoise static file serving
- Jinja2 template engine (to be re-added later)
- webob request/response wrappers

## [0.1.3] - 2024-07-29

### Added

- Initial PyPI release
- WSGI framework with webob request/response wrappers
- Basic and parameterized routing
- Class-based routes
- Django-like URL patterns
- Jinja2 template support
- Custom exception handlers
- Static file serving via Whitenoise
- Middleware support
- Allowed methods enforcement
- Custom `Response` wrapper class

[0.3.0]: https://github.com/Samandar-Komilov/oberoon/releases/tag/v0.3.0
[0.2.0]: https://github.com/Samandar-Komilov/oberoon/releases/tag/v0.2.0
[0.1.3]: https://github.com/Samandar-Komilov/oberoon/releases/tag/v0.1.3
