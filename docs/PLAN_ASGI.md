# Oberoon — ASGI-First Rewrite Plan

## Vision

Oberoon is an ASGI-native web framework built from scratch. No Starlette, no FastAPI scaffolding. Every layer is written by hand for deep understanding of how modern async web frameworks work.

Differentiators:
- `msgspec` for validation and serialization (faster than Pydantic v2, zero-copy JSON)
- Dependency injection without a separate library
- Auto OpenAPI schema generation from native type annotations
- ASGI-first throughout

---

## Progress

| Phase | Status |
|-------|--------|
| 1. ASGI Core | Done |
| 2. Routing + method decorators | Done |
| 3. Attachable routers (recursive) | Done |
| 4. msgspec integration | Next |
| 5. Middleware | Planned |
| 6. Dependency injection | Planned |
| 7. OpenAPI generation | Planned |
| 8. Templates + static files | Planned |
| 9. WSGI bridge | Planned |

---

## Phase 1 — ASGI Core (Done)

`Request`, `Response`, `Oberoon.__call__` with lifespan support. Handlers are async, return `Response` objects. Test client via `httpx.ASGITransport`.

## Phase 2 — Routing (Done)

Regex-based routing via `compile_path()`. Path parameters with type converters (`{id:int}`, `{name:str}`, `{filepath:path}`). Method decorators (`@app.get`, `@app.post`, etc.). Proper 404/405 distinction.

## Phase 3 — Attachable Routers (Done)

`Router` class with prefix mounting via `app.include_router(router)`. Recursive DFS flattening for nested routers. `RoutingMixin` shared between `Oberoon` and `Router`. Deferred compilation — routes compile at mount time when the full prefix is known.

---

## Phase 4 — msgspec Integration

**Goal:** Typed request/response bodies with automatic validation and serialization.

### 4.1 — Typed request bodies

Inspect handler signature, find `msgspec.Struct` parameters, decode request body automatically:

```python
class CreateUser(msgspec.Struct):
    name: str
    age: int

@app.post("/users")
async def create_user(request: Request, body: CreateUser) -> Response:
    # body is already validated and typed
    ...
```

The framework calls `msgspec.json.decode(raw_body, type=CreateUser)`. Validation errors become 422 responses.

### 4.2 — Typed responses

If handler returns a `msgspec.Struct`, the framework encodes it to JSON automatically:

```python
class UserResponse(msgspec.Struct):
    id: int
    name: str

@app.get("/users/{user_id:int}")
async def get_user(request: Request, user_id: int) -> UserResponse:
    return UserResponse(id=user_id, name="Alice")
    # -> {"id": 1, "name": "Alice"} with Content-Type: application/json
```

### 4.3 — Why msgspec

`msgspec` decodes + validates in a single C-extension pass. 2-10x faster than Pydantic v2. Zero runtime dependencies. `msgspec.json.schema()` generates JSON Schema from any Struct — feeds directly into OpenAPI generation later.

---

## Phase 5 — Middleware (ASGI-native)

**Goal:** Composable middleware via the standard ASGI wrapper pattern.

An ASGI middleware wraps another ASGI app:

```python
class CORSMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # modify scope, intercept send, etc.
        await self.app(scope, receive, send)
```

No base class needed. `app.add_middleware(CORSMiddleware)` wraps the app at startup.

Key middleware to ship: error handling (500 responses), CORS, request logging.

---

## Phase 6 — Dependency Injection

**Goal:** Handlers declare dependencies as typed parameters; the framework resolves them via `inspect.signature()`.

### Resolution strategy

```
parameter name in path pattern     -> path param (coerce to annotated type)
parameter type is msgspec.Struct   -> parse request body
parameter name in query string     -> query param (coerce to annotated type)
parameter type is Request          -> inject raw request
parameter default is Depends(fn)   -> resolve sub-dependency recursively
```

### Depends()

```python
def Depends(dependency: Callable):
    return DependsMarker(dependency)
```

When the resolver encounters a `DependsMarker`, it calls the dependency with the same resolution logic recursively. Same pattern as FastAPI.

---

## Phase 7 — OpenAPI Generation

**Goal:** `/openapi.json` generated entirely from type annotations.

For each route, extract:
- Path, method, operation ID
- Path parameters (from `compile_path`)
- Request body schema (from `msgspec.Struct` param via `msgspec.json.schema()`)
- Response schema (from return type annotation)

Serve `/docs` with Swagger UI or Scalar loaded from CDN.

---

## Phase 8 — Templates + Static Files

**Goal:** Jinja2 template rendering and static file serving.

- `app.template("home.html", context={...})` returning a `Response`
- Static file serving as an ASGI app mounted at a prefix
- Already have `jinja2` as a dependency

---

## Phase 9 — WSGI Compatibility Bridge

**Goal:** Accept a legacy WSGI callable and run it inside the async framework via `anyio.to_thread.run_sync()`.

Low priority — only needed if someone wants to mount a Flask/Django app inside Oberoon. Useful as a learning exercise for understanding the WSGI/ASGI boundary.

---

## File Structure

```
oberoon/
    __init__.py          # exports: Oberoon, Request, Response, Router
    core.py              # Oberoon class: __call__, route(), include_router()
    routing/
        __init__.py      # re-exports
        routing.py       # Route, Router, RoutingMixin, compile_path()
    requests/
        __init__.py
        request.py       # Request class
    responses/
        __init__.py
        response.py      # Response class, build_response()
    logging.py           # structured stdout logging
    exceptions.py        # NotFoundException, MethodNotAllowedException
    serialization.py     # msgspec integration (Phase 4)
    middleware.py         # middleware helpers (Phase 5)
    di.py                # Depends(), resolve_handler() (Phase 6)
    schema.py            # OpenAPI generation (Phase 7)
```

---

## Resources

### The spec
- **ASGI spec** — https://asgi.readthedocs.io/en/latest/
- **anyio docs** — https://anyio.readthedocs.io

### Understand the internals
- **h11** — https://h11.readthedocs.io — what uvicorn does before calling you
- **uvicorn h11_impl.py** — https://github.com/encode/uvicorn/blob/master/uvicorn/protocols/http/h11_impl.py
- **msgspec docs** — https://jcristharif.com/msgspec/

### Reference implementations
- **Starlette routing** — https://github.com/encode/starlette/blob/master/starlette/routing.py
- **FastAPI DI** — https://github.com/fastapi/fastapi/blob/master/fastapi/dependencies/utils.py
- **FastAPI OpenAPI** — https://github.com/fastapi/fastapi/blob/master/fastapi/openapi/utils.py

### Specs for later phases
- **OpenAPI 3.1** — https://spec.openapis.org/oas/v3.1.0
- **JSON Schema** — https://json-schema.org/understanding-json-schema/
- **PEP 3333 (WSGI)** — for the Phase 9 bridge
