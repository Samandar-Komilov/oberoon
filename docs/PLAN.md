# Oberoon Modernization Plan

This plan is ordered by priority: fix correctness bugs first, eliminate dangerous/abandoned dependencies second, then modernize the architecture.

---

## Phase 1 — Critical Bug Fixes (do first, no API breakage)

### Step 1.1 — Fix `response.text` encoding crash

**File:** `oberoon/response.py:35`

Change:
```python
self.body = self.text
```
To:
```python
self.body = self.text.encode("utf-8") if isinstance(self.text, str) else self.text
```

This prevents `TypeError` from WSGI servers when `response.text` is set.

---

### Step 1.2 — Fix response body `if` chain to `elif`

**File:** `oberoon/response.py:26-36`

Replace the three `if` blocks with `if / elif / elif` so that only the first matching content type wins, not the last.

---

### Step 1.3 — Fix exception handler for class-based views

**File:** `oberoon/app.py:95-99`

Wrap `handler_method(request, response, **kwargs)` in the same `try/except` block that already exists for function-based views:

```python
try:
    handler_method(request, response, **kwargs)
except Exception as e:
    if self.exception_handler:
        self.exception_handler(request, response, e)
    else:
        raise
```

---

### Step 1.4 — Replace `assert` with `raise ValueError`

**File:** `oberoon/app.py:159`

```python
# Before
assert path not in self.routes, "Duplicate route. Please change the URL."

# After
if path in self.routes:
    raise ValueError(f"Route already registered: {path!r}")
```

---

### Step 1.5 — Fix mutable default argument in `template()`

**File:** `oberoon/app.py:194`

```python
# Before
def template(self, template_name, context={}):

# After
def template(self, template_name, context=None):
    if context is None:
        context = {}
```

---

### Step 1.6 — Enable Jinja2 autoescape

**File:** `oberoon/app.py:35-37`

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

self.template_env = Environment(
    loader=FileSystemLoader(os.path.abspath(templates_dir)),
    autoescape=select_autoescape(["html", "htm", "xml"]),
)
```

---

### Step 1.7 — Add `parse` to `pyproject.toml`

**File:** `pyproject.toml`

Add `"parse>=1.20"` to `[project] dependencies` as a short-term fix until it is replaced in Phase 2.

---

## Phase 2 — Dependency Replacement

### Step 2.1 — Replace `requests-wsgi-adapter` with `httpx`

**Rationale:** `requests-wsgi-adapter` has had no release since 2016. `httpx` provides WSGI transport natively and is actively maintained with full type annotations.

1. Add `httpx` to `[dependency-groups] dev` (it is only needed for testing).
2. Rewrite `test_session()` in `app.py`:

```python
def test_client(self):
    import httpx
    transport = httpx.WSGITransport(app=self)
    return httpx.Client(transport=transport, base_url="http://testserver")
```

3. Update all test files: replace `requests.Session` usage with `httpx.Client`. The API is largely compatible (`client.get(url)`, `.text`, `.status_code`, `.json()`).
4. Remove `requests-wsgi-adapter` and `requests` from dependencies.

---

### Step 2.2 — Replace `parse` with `re`-based routing

**Rationale:** `parse` is minimally maintained, not declared in deps, and does O(n) linear matching with ambiguous results.

Design a minimal regex router:

```python
import re

def _compile_route(path: str) -> re.Pattern:
    # Convert "/hello/{name}" -> r"^/hello/(?P<name>[^/]+)$"
    pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path)
    return re.compile(f"^{pattern}$")
```

Store compiled patterns alongside handlers:
```python
self.routes[path] = {
    "pattern": _compile_route(path),
    "handler": handler,
    "allowed_methods": allowed_methods,
}
```

Update `find_handler` to use `pattern.match(request.path)` and return `match.groupdict()` as kwargs. This is zero new dependencies, faster, and unambiguous.

---

### Step 2.3 — Replace `webob` with `werkzeug`

**Rationale:** `werkzeug` is the WSGI toolkit used by Flask, has broader adoption, better type stubs, and covers every feature Oberoon uses (`Request`, `Response`). This also future-proofs the framework if ASGI support is ever added.

1. Replace `from webob import Request` → `from werkzeug.wrappers import Request`
2. Replace `from webob import Response as WebResponse` → `from werkzeug.wrappers import Response as WebResponse`
3. Adjust `Response.__call__` to use `werkzeug.wrappers.Response(response=body, status=status_code, content_type=content_type)`.
4. Remove `webob` from dependencies; add `werkzeug`.

Alternatively, if the goal is zero non-stdlib dependencies, implement a minimal request parser using `wsgiref` and `urllib.parse`. This is more work but produces a truly self-contained framework.

---

## Phase 3 — API Improvements (non-breaking additions)

### Step 3.1 — Add response headers API

Extend `Response` to support custom headers:

```python
def __init__(self):
    ...
    self.headers = {}

def __call__(self, environ, start_response):
    self.set_body_and_content_type()
    response = WebResponse(body=self.body, content_type=self.content_type, status_code=self.status_code)
    for key, value in self.headers.items():
        response.headers[key] = value
    return response(environ, start_response)
```

---

### Step 3.2 — Make `static_dir` optional

In `__init__`, check whether `static_dir` exists before initialising WhiteNoise:

```python
import os
if os.path.isdir(static_dir):
    self.whitenoise = WhiteNoise(self.wsgi_app, root=static_dir, prefix="/static")
else:
    self.whitenoise = None
```

Update `__call__` to fall through to middleware if `self.whitenoise is None`.

---

### Step 3.3 — Add request body size limit

Accept a `max_content_length` parameter in `__init__` (default e.g. 16 MB) and enforce it in `handle_request`:

```python
if request.content_length and request.content_length > self.max_content_length:
    response = Response()
    response.status_code = 413
    response.text = "Request Entity Too Large"
    return response
```

---

### Step 3.4 — Middleware chain for static files (optional)

Route static file requests through middleware before passing to WhiteNoise, so logging and auth middleware applies uniformly. This requires restructuring `__call__` to always run middleware first and then dispatch based on path inside the middleware chain.

---

## Phase 4 — Modernization and Type Safety

### Step 4.1 — Add type annotations throughout

Add `from __future__ import annotations` and annotate all public methods:

```python
def route(self, path: str, allowed_methods: list[str] | None = None):
    ...
def handle_request(self, request: Request) -> Response:
    ...
```

### Step 4.2 — Add a `py.typed` marker

Create `oberoon/py.typed` (empty file) and declare it in `pyproject.toml` under `[tool.setuptools.package-data]` so that type checkers recognise the package as typed.

### Step 4.3 — Set up `ruff` for linting and formatting

Add to `pyproject.toml`:
```toml
[dependency-groups]
dev = [
    ...
    "ruff>=0.4",
]

[tool.ruff]
line-length = 100
target-version = "py312"
```

### Step 4.4 — Migrate coverage config from `.coveragerc` to `pyproject.toml`

Move coverage settings into `[tool.coverage]` in `pyproject.toml` to eliminate the separate `.coveragerc` file.

---

## Execution Order Summary

| Phase | Step | Priority | Effort |
|-------|------|----------|--------|
| 1 | 1.1 Fix `text` encoding | Critical | Minutes |
| 1 | 1.2 Fix `if` → `elif` | Critical | Minutes |
| 1 | 1.3 Fix exception handler for CBVs | High | Minutes |
| 1 | 1.4 Replace `assert` with `raise` | High | Minutes |
| 1 | 1.5 Fix mutable default arg | High | Minutes |
| 1 | 1.6 Enable Jinja2 autoescape | High | Minutes |
| 1 | 1.7 Declare `parse` in deps | High | Minutes |
| 2 | 2.1 Replace `requests-wsgi-adapter` → `httpx` | High | Hours |
| 2 | 2.2 Replace `parse` → regex router | High | Hours |
| 2 | 2.3 Replace `webob` → `werkzeug` | Medium | Hours |
| 3 | 3.1 Response headers API | Medium | Hours |
| 3 | 3.2 Optional static dir | Low | Minutes |
| 3 | 3.3 Request body size limit | Medium | Hours |
| 3 | 3.4 Middleware for static files | Low | Hours |
| 4 | 4.1-4.4 Type safety + tooling | Low | Days |
