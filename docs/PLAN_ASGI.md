# Oberoon — ASGI-First Rewrite Plan

## Vision

Rewrite Oberoon from the ground up as an ASGI-native framework. No Starlette, no FastAPI scaffolding. Every layer is written by hand so you understand exactly what is happening. WSGI apps are supported as a compatibility shim via `anyio.to_thread.run_sync()`.

Unique differentiators over existing frameworks:
- `msgspec` for validation and serialization (faster than Pydantic v2, zero-copy JSON)
- Dependency injection without a separate library
- Auto OpenAPI schema generation from native type annotations
- ASGI-first, WSGI via thread bridge

---

## What ASGI Actually Is

Before writing a line of code, understand the contract you are implementing.

An ASGI application is a single async callable with this signature:

```python
async def app(scope: dict, receive: Callable, send: Callable) -> None:
    ...
```

- **`scope`**: a dict describing the connection. `scope["type"]` is one of `"http"`, `"websocket"`, or `"lifespan"`. For HTTP: contains `method`, `path`, `query_string`, `headers`, etc. This is the already-parsed request metadata — the ASGI server (uvicorn, hypercorn) did the TCP/HTTP parsing before calling you.
- **`receive`**: an async callable you call to pull messages from the client. For HTTP it yields `{"type": "http.request", "body": b"...", "more_body": False}`.
- **`send`**: an async callable you call to push messages to the client. For HTTP: first call with `{"type": "http.response.start", "status": 200, "headers": [...]}`, then one or more calls with `{"type": "http.response.body", "body": b"...", "more_body": False}`.

You do not call `h11` inside your framework. `h11` is what *uvicorn* uses to parse raw TCP bytes into ASGI messages before handing them to you. Knowing h11 helps you understand what uvicorn does internally — it is a reading exercise, not a direct dependency of your framework.

---

## Dependency Changes

### Remove entirely
| Package | Why |
|---------|-----|
| `webob` | WSGI-only request/response objects |
| `requests-wsgi-adapter` | WSGI-only test adapter, abandoned |
| `requests` | Only present for the adapter |
| `whitenoise` | WSGI static serving (may re-add ASGI version later) |
| `parse` | URL parsing, replace with stdlib `re` |

### Add
| Package | Purpose |
|---------|---------|
| `anyio` | Async runtime abstraction (asyncio + trio), thread bridge for WSGI compat |
| `msgspec` | Validation, serialization, schema introspection |

### Dev only
| Package | Purpose |
|---------|---------|
| `uvicorn` | ASGI server for manual testing |
| `httpx` | Test client via `httpx.ASGITransport` |
| `anyio[trio]` | Run tests on both backends |
| `pytest-anyio` | Async test support |

### Keep
| Package | Why |
|---------|-----|
| `jinja2` | Template rendering, still valid |

---

## Phase 0 — Preparation (do before any code)

### Step 0.1 — Read first

Before writing any code, read these in order. They are short:

1. The ASGI spec itself: https://asgi.readthedocs.io/en/latest/specs/main.html (15 min)
2. The HTTP connection scope spec: https://asgi.readthedocs.io/en/latest/specs/www.html (10 min)
3. A minimal ASGI app written by hand — just 20 lines, teaches the entire protocol:
   ```python
   async def app(scope, receive, send):
       assert scope["type"] == "http"
       await receive()  # consume request body
       await send({"type": "http.response.start", "status": 200,
                   "headers": [[b"content-type", b"text/plain"]]})
       await send({"type": "http.response.body", "body": b"hello"})
   ```
   Run this with `uvicorn app:app` and make a request. This is your foundation.

### Step 0.2 — Strip the old code

Delete `oberoon/app.py`, `oberoon/middleware.py`, `oberoon/response.py`. Keep `oberoon/__init__.py`. Update `pyproject.toml` deps as described above.

---

## Phase 1 — The ASGI Core (~80 lines)

**Goal:** A working ASGI callable that can receive a request and send a response. No routing yet.

### Step 1.1 — `Request` class

Parse the ASGI `scope` and `receive` into a usable object. Do not use `webob`. Do it yourself.

```python
class Request:
    def __init__(self, scope: dict, receive: Callable):
        self._scope = scope
        self._receive = receive

    @property
    def method(self) -> str:
        return self._scope["method"].upper()

    @property
    def path(self) -> str:
        return self._scope["path"]

    @property
    def query_string(self) -> str:
        return self._scope["query_string"].decode()

    @property
    def headers(self) -> dict[str, str]:
        return {k.decode(): v.decode() for k, v in self._scope["headers"]}

    async def body(self) -> bytes:
        # ASGI body may arrive in multiple chunks
        chunks = []
        while True:
            message = await self._receive()
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    async def json(self):
        import msgspec.json
        return msgspec.json.decode(await self.body())
```

Key insight: `body()` must loop because ASGI allows streaming bodies in multiple `http.request` messages.

### Step 1.2 — `Response` class

```python
class Response:
    def __init__(self):
        self.status_code: int = 200
        self.headers: dict[str, str] = {}
        self._body: bytes = b""

    def set_body(self, body: bytes, content_type: str):
        self._body = body
        self.headers["content-type"] = content_type

    async def send(self, send: Callable) -> None:
        encoded_headers = [
            [k.encode(), v.encode()] for k, v in self.headers.items()
        ]
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": encoded_headers,
        })
        await send({
            "type": "http.response.body",
            "body": self._body,
            "more_body": False,
        })
```

Note: headers are `list[list[bytes]]` in ASGI, not a dict. Multiple headers with the same name are valid (e.g., `Set-Cookie`).

### Step 1.3 — The `Oberoon` ASGI callable

```python
class Oberoon:
    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
        elif scope["type"] == "http":
            request = Request(scope, receive)
            response = Response()
            await self.handle_request(request, response)
            await response.send(send)

    async def _handle_lifespan(self, receive, send):
        # ASGI lifespan: startup/shutdown events
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
```

The `lifespan` scope is for startup/shutdown hooks (database connections, etc.). Handling it is required for uvicorn compatibility even if you do nothing with it.

---

## Phase 2 — Routing (~60 lines)

**Goal:** Regex-based O(1)-per-match routing. No `parse` library.

### Step 2.1 — Route compilation

Convert path patterns like `/users/{user_id:int}` into named regex groups:

```python
import re

CONVERTERS = {
    "str": r"[^/]+",
    "int": r"[0-9]+",
    "path": r".+",
}

def compile_path(path: str) -> tuple[re.Pattern, dict[str, type]]:
    """
    "/users/{user_id:int}" -> (re.compile(r"^/users/(?P<user_id>[0-9]+)$"), {"user_id": int})
    "/items/{name}"        -> (re.compile(r"^/items/(?P<name>[^/]+)$"), {"name": str})
    """
    param_types = {}
    def replace(match):
        name, _, converter = match.group(1).partition(":")
        converter = converter or "str"
        param_types[name] = int if converter == "int" else str
        return f"(?P<{name}>{CONVERTERS[converter]})"
    pattern = re.sub(r"\{([^}]+)\}", replace, path)
    return re.compile(f"^{pattern}$"), param_types
```

This gives you typed path parameters for free, which feeds directly into schema generation later.

### Step 2.2 — Route registry and lookup

```python
@dataclass
class Route:
    pattern: re.Pattern
    param_types: dict[str, type]
    handler: Callable
    methods: set[str]

def find_handler(self, method: str, path: str) -> tuple[Route | None, dict]:
    for route in self._routes:
        match = route.pattern.match(path)
        if match:
            if method not in route.methods:
                return None, {}  # matched path, wrong method -> 405
            return route, match.groupdict()
    return None, {}  # no match -> 404
```

### Step 2.3 — `route()` decorator

```python
def route(self, path: str, methods: list[str] = None):
    def decorator(handler):
        pattern, param_types = compile_path(path)
        self._routes.append(Route(
            pattern=pattern,
            param_types=param_types,
            handler=handler,
            methods={m.upper() for m in (methods or ["GET"])},
        ))
        return handler
    return decorator
```

---

## Phase 3 — WSGI Compatibility Bridge

**Goal:** Accept a legacy WSGI callable and run it inside the async framework.

The bridge converts an ASGI call into a WSGI call run in a thread pool:

```python
import anyio

class WSGIMiddleware:
    def __init__(self, wsgi_app):
        self._app = wsgi_app

    async def __call__(self, scope, receive, send):
        # Read entire body first (WSGI is synchronous and blocking)
        body_chunks = []
        message = await receive()
        body_chunks.append(message.get("body", b""))
        while message.get("more_body"):
            message = await receive()
            body_chunks.append(message.get("body", b""))
        body = b"".join(body_chunks)

        environ = build_environ(scope, body)  # convert ASGI scope -> WSGI environ
        response_started = False
        response_body = []

        def start_response(status, headers, exc_info=None):
            nonlocal response_started
            response_started = True
            # store for later send()
            ...

        # Run the blocking WSGI app in a thread
        result = await anyio.to_thread.run_sync(
            lambda: self._app(environ, start_response)
        )
        ...
```

Implementing `build_environ` teaches you exactly what WSGI expects — it maps ASGI scope fields to CGI-style environ keys (`REQUEST_METHOD`, `PATH_INFO`, `wsgi.input`, etc.).

---

## Phase 4 — msgspec Integration

**Goal:** Handlers declare typed inputs and outputs; msgspec validates and serializes.

### Step 4.1 — Typed request bodies

```python
import msgspec

class CreateUser(msgspec.Struct):
    name: str
    age: int

@app.route("/users", methods=["POST"])
async def create_user(request: Request, body: CreateUser) -> dict:
    ...
```

The framework inspects the handler signature with `inspect.get_annotations()`, sees `body: CreateUser` where `CreateUser` is a `msgspec.Struct` subclass, reads the request body, and calls `msgspec.json.decode(raw_body, type=CreateUser)`. Validation errors from msgspec become 422 responses automatically.

### Step 4.2 — Typed responses

If the handler return type annotation is a `msgspec.Struct`, the framework calls `msgspec.json.encode(result)` and sets `Content-Type: application/json`.

### Step 4.3 — Why msgspec over Pydantic

`msgspec` uses a compiled C extension for JSON decode+validate in a single pass. Benchmarks show 2-10x faster than Pydantic v2. It also has zero runtime dependencies. The `msgspec.Struct` type carries field metadata that is directly usable for schema generation in Phase 6.

---

## Phase 5 — Dependency Injection

**Goal:** Handlers declare their dependencies as typed parameters; the framework resolves them.

### Step 5.1 — What dependency injection is here

FastAPI's `Depends()` system at its core is just:
1. Inspect the handler's signature with `inspect.signature()`.
2. For each parameter, determine its source: path param, query param, header, body, or a sub-dependency.
3. Resolve each source from the request and pass the resolved value to the handler.

You do not need a DI container library. `inspect` is sufficient.

### Step 5.2 — Parameter resolution strategy

```
handler parameter name in path pattern  ->  path param (coerce to annotated type)
parameter type is a msgspec.Struct      ->  parse request body
parameter name in query string          ->  query param (coerce to annotated type)
parameter type is Request               ->  inject raw request
```

### Step 5.3 — `Depends()` for reusable dependencies

```python
def Depends(dependency: Callable):
    # Returns a marker object that the resolver recognises
    return DependsMarker(dependency)
```

When the resolver encounters a `DependsMarker`, it calls `dependency()` recursively with the same resolution logic. This is exactly what FastAPI does — no magic.

### Step 5.4 — Implementation skeleton

```python
import inspect

async def resolve_handler(handler, request, path_params):
    sig = inspect.signature(handler)
    kwargs = {}
    for name, param in sig.parameters.items():
        annotation = param.annotation
        if name in path_params:
            kwargs[name] = annotation(path_params[name]) if annotation != inspect.Parameter.empty else path_params[name]
        elif annotation == Request:
            kwargs[name] = request
        elif isinstance(param.default, DependsMarker):
            kwargs[name] = await resolve_handler(param.default.dependency, request, path_params)
        elif issubclass(annotation, msgspec.Struct):
            raw = await request.body()
            kwargs[name] = msgspec.json.decode(raw, type=annotation)
        # ... query params, headers, etc.
    return await handler(**kwargs)
```

---

## Phase 6 — Auto Schema Generation

**Goal:** `/openapi.json` generated entirely from type annotations, no decorators needed.

### Step 6.1 — What you need to generate

OpenAPI 3.1 schema is a JSON document. For each route, you need:
- Path, method, operation ID
- Path parameters (name, type)
- Request body schema (if handler has a `msgspec.Struct` body param)
- Response schema (from return type annotation)

### Step 6.2 — msgspec schema introspection

`msgspec` provides `msgspec.json.schema()` which generates a JSON Schema dict from any `Struct` type:

```python
import msgspec.json

class CreateUser(msgspec.Struct):
    name: str
    age: int

schema = msgspec.json.schema(CreateUser)
# {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, ...}
```

This is the hard part of schema generation solved for free by msgspec.

### Step 6.3 — Schema assembly

Walk `self._routes` at startup (or lazily on first `/openapi.json` request), inspect each handler's signature, and assemble the OpenAPI dict. Serve it as JSON. Then serve a `/docs` route that returns a static HTML page loading Swagger UI or Scalar from a CDN.

---

## Phase 7 — Middleware (ASGI-native)

ASGI middleware is simpler than WSGI middleware. A middleware is just an ASGI app that wraps another ASGI app:

```python
class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        print(f"{scope['method']} {scope['path']}")
        await self.app(scope, receive, send)
```

No base class needed. No special protocol. Just `__init__(self, app)` and `async __call__(self, scope, receive, send)`.

---

## Phase 8 — Test Client

Replace `requests` + `requests-wsgi-adapter` with `httpx.ASGITransport`:

```python
def test_client(self) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=self),
        base_url="http://testserver",
    )
```

Tests become:
```python
async def test_home(app):
    async with app.test_client() as client:
        response = await client.get("/home")
        assert response.status_code == 200
```

Use `anyio.pytest_plugin` so tests run on both asyncio and trio backends.

---

## File Structure After Rewrite

```
oberoon/
    __init__.py          # exports: Oberoon, Request, Response, Depends
    app.py               # Oberoon class: __call__, route(), add_middleware()
    routing.py           # compile_path(), Route, find_handler()
    requests_.py         # Request class
    responses.py         # Response class
    middleware.py        # base middleware helpers
    wsgi.py              # WSGIMiddleware (anyio bridge)
    di.py                # Depends(), resolve_handler()
    schema.py            # OpenAPI generation
    exceptions.py        # HTTPException, validation error handling
```

---

## Build Order

| Phase | Deliverable | Test it by |
|-------|------------|------------|
| 0 | Read ASGI spec + run 20-line ASGI app | `uvicorn` + `curl` |
| 1 | `Request`, `Response`, `Oberoon.__call__` | `httpx.ASGITransport` in pytest |
| 2 | Regex router, `@route()` decorator | Route to handlers, check 404/405 |
| 3 | WSGI bridge via `anyio.to_thread.run_sync` | Wrap a tiny Flask app and call it |
| 4 | msgspec body decode, typed responses | POST with JSON body |
| 5 | Dependency injection via `inspect` | Inject path params, body, sub-deps |
| 6 | OpenAPI schema at `/openapi.json` | Check against https://editor.swagger.io |
| 7 | ASGI middleware | Add a logging middleware |
| 8 | Lifespan events (startup/shutdown hooks) | Connect to a DB on startup |

---

## Resources

### Must read (the spec and the protocol)
- **ASGI spec** — https://asgi.readthedocs.io/en/latest/ — the ground truth for everything you are implementing
- **PEP 3333** — WSGI spec — understand what you are bridging from
- **anyio docs** — https://anyio.readthedocs.io — task groups, thread bridge, backend abstraction

### Must read (understand what's under your dependencies)
- **h11 README** — https://h11.readthedocs.io — how raw HTTP/1.1 bytes become structured data; what uvicorn does before calling you
- **uvicorn source, `protocols/http/h11_impl.py`** — https://github.com/encode/uvicorn/blob/master/uvicorn/protocols/http/h11_impl.py — ~400 lines showing exactly how ASGI messages are produced from TCP
- **msgspec docs** — https://jcristharif.com/msgspec/ — Struct, JSON decode/encode, schema generation
- **msgspec benchmarks** — https://jcristharif.com/msgspec/benchmarks.html — why it beats Pydantic v2

### Read the source of what you are building toward
- **Starlette routing** — https://github.com/encode/starlette/blob/master/starlette/routing.py — ~600 lines; how routes compile, how middleware wraps, how lifespan works
- **Starlette requests** — https://github.com/encode/starlette/blob/master/starlette/requests.py — how scope/receive become a usable Request object
- **FastAPI dependency injection** — https://github.com/fastapi/fastapi/blob/master/fastapi/dependencies/utils.py — the real implementation; complex but the concepts are all in Phase 5 above
- **FastAPI schema generation** — https://github.com/fastapi/fastapi/blob/master/fastapi/openapi/utils.py

### Background reading
- **"How Python ASGI Works"** — https://www.encode.io/articles/working-with-http-connections-in-ASGI — by Tom Christie (Starlette author)
- **OpenAPI 3.1 spec** — https://spec.openapis.org/oas/v3.1.0 — what `/openapi.json` must conform to
- **JSON Schema** — https://json-schema.org/understanding-json-schema/ — the format msgspec generates for your types

### With Claude
When building each phase, share the actual code you wrote and ask "what is wrong with this implementation of X". Do not ask "how do I implement X" — write it first, even if wrong, then debug together. You will understand it far better. Specifically useful phases to do this on: the WSGI bridge (step 3), the dependency resolver (step 5), and the OpenAPI assembler (step 6).
