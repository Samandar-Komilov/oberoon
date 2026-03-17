# Oberoon Framework — Analysis Report

## 1. Overview

Oberoon is a minimal Flask-like WSGI framework built in 2024. It provides routing, class-based and function-based views, middleware, Jinja2 templating, WhiteNoise static file serving, and a test client. The codebase is small (~220 lines across 3 files).

---

## 2. Dependency Analysis

### 2.1 `webob` (>=1.8.9)

**Status:** Mature and actively maintained. Used by the Pyramid ecosystem.

**Concern:** Heavyweight for this use case. Oberoon only uses `webob.Request` (to parse environ) and `webob.Response` (as a WSGI response builder). `werkzeug` provides equivalent functionality with broader community adoption, better type annotations, and is the established standard for WSGI toolkits. Alternatively, Python's stdlib `wsgiref` covers basic needs.

**Risk level:** Low security risk, but represents unnecessary coupling to a large dependency for minimal usage.

---

### 2.2 `requests-wsgi-adapter` (>=0.4.1)

**Status:** Effectively abandoned. Last PyPI release was in 2016. Minimal test coverage. No active maintainer. The import name (`wsgiadapter`) differs from the package name, indicating legacy packaging.

**Concern:** This is the most problematic dependency. It is used exclusively for the `test_session()` method. If a vulnerability is found in it, there is no upstream to fix it. It also drags in the full `requests` stack as a transitive dependency.

**Replacement:** `httpx` with `httpx.WSGITransport` provides the same WSGI testing capability with an actively maintained, well-typed codebase. Alternatively, `werkzeug.test.Client` or `webtest` are purpose-built for WSGI testing.

**Risk level:** High. Abandoned library in a testing-critical path.

---

### 2.3 `parse`

**Status:** Minimally maintained. Not declared in `pyproject.toml` but imported directly in `app.py`. This is a missing dependency declaration — the package will work in development where it happens to be installed but will fail on a clean install.

**Concern:**
- Not listed in `pyproject.toml` `dependencies` — silent breakage risk for consumers.
- `parse` does a linear O(n) scan over all routes on every request: `parse(path, request.path)` is called for each registered route until a match is found. With many routes this degrades performance significantly.
- No support for regex constraints, optional segments, or type converters beyond basic Python format spec.
- Ambiguous matching: `parse("/users/{id}", "/users/foo/bar")` may match when it should not.

**Replacement:** `werkzeug.routing.Map` provides a full-featured, compiled routing system. Alternatively, a simple regex-based router built on `re` eliminates the dependency entirely.

**Risk level:** High. Missing from declared deps is a packaging bug; routing ambiguity is a correctness risk.

---

### 2.4 `whitenoise` (>=6.12.0)

**Status:** Actively maintained, production-grade. Correct choice for static file serving in a WSGI context.

**Concern:** Initialization in `__init__` raises an error if `static_dir` does not exist at startup, which surprises users who have no static directory. Should be made optional or lazy.

**Risk level:** Low.

---

### 2.5 `jinja2` (>=3.1.6)

**Status:** Actively maintained, industry standard. Correct choice.

**Concern:** `autoescape` is not configured. For HTML templates, this is a latent XSS vector (see §3.7).

**Risk level:** Low dependency risk; Medium security risk from misconfiguration.

---

### 2.6 `requests` (transitive, from `requests-wsgi-adapter`)

Pulled in only to support the abandoned WSGI adapter. Would be eliminated by replacing the adapter.

---

## 3. Implementation Bugs and Vulnerabilities

### 3.1 Missing `parse` in declared dependencies [BUG — PACKAGING]

**File:** `pyproject.toml`

`parse` is imported at `oberoon/app.py:2` but absent from `[project] dependencies`. Any user installing from PyPI gets an `ImportError` on first use.

---

### 3.2 `response.text` not encoded to bytes [BUG — RUNTIME CRASH]

**File:** `oberoon/response.py:35`

```python
if self.text is not None:
    self.body = self.text          # BUG: str, not bytes
    self.content_type = "text/plain"
```

WSGI requires the response body to yield `bytes`. The `json` and `html` branches correctly call `.encode()`, but `text` does not. Setting `response.text = "Hello"` produces a `str` body, which causes a `TypeError` in strict WSGI servers or garbled responses in lenient ones.

**Fix:** `self.body = self.text.encode("utf-8")`

---

### 3.3 Response body overwrite order — `if` instead of `elif` [BUG — LOGIC]

**File:** `oberoon/response.py:26-36`

```python
if self.json is not None:
    ...
if self.html is not None:   # should be elif
    ...
if self.text is not None:   # should be elif
    ...
```

All three branches are independent. If a handler sets both `response.json` and `response.text`, `text` silently overwrites `json` with no warning. The last setter wins, which is not the intended behaviour. Should use `elif`.

---

### 3.4 Exception handler not invoked for class-based views [BUG — CORRECTNESS]

**File:** `oberoon/app.py:95-99`

```python
if inspect.isclass(handler):
    handler_method = getattr(handler(), request.method.lower(), None)
    if handler_method is None:
        return self.method_not_allowed_response(response)
    handler_method(request, response, **kwargs)   # no try/except here
else:
    ...
    try:
        handler(request, response, **kwargs)
    except Exception as e:
        if self.exception_handler:
            self.exception_handler(request, response, e)
```

The custom exception handler registered via `add_exception_handler` is only invoked for function-based handlers. Exceptions from class-based views propagate unhandled through the middleware and crash with a 500.

---

### 3.5 Mutable default argument in `template()` [BUG — PYTHON ANTI-PATTERN]

**File:** `oberoon/app.py:194`

```python
def template(self, template_name, context={}):
```

The dict `{}` is created once at function definition time and shared across all calls. If any call mutates it, all subsequent calls with no `context` argument see the modified dict.

**Fix:** `context=None`, then `context = context or {}` in the body.

---

### 3.6 `assert` used for runtime route validation [VULNERABILITY]

**File:** `oberoon/app.py:159`

```python
assert path not in self.routes, "Duplicate route. Please change the URL."
```

`assert` is compiled away when Python runs with `-O` (`PYTHONOPTIMIZE=1`), which gunicorn and uWSGI expose via their config. In production, duplicate routes are silently registered and only the first match is ever reachable, with no error surfaced.

**Fix:** `raise ValueError(f"Route already registered: {path!r}")`

---

### 3.7 Jinja2 autoescape disabled — XSS risk [VULNERABILITY]

**File:** `oberoon/app.py:35-37`

```python
self.template_env = Environment(
    loader=FileSystemLoader(os.path.abspath(templates_dir))
)
```

Jinja2 defaults to `autoescape=False`. Any user-controlled data rendered in a template (e.g., `{{ name }}`) is inserted verbatim into HTML, allowing injection of arbitrary HTML/JavaScript.

**Fix:**
```python
from jinja2 import select_autoescape
Environment(
    loader=FileSystemLoader(...),
    autoescape=select_autoescape(['html', 'htm', 'xml'])
)
```

---

### 3.8 Static files bypass the middleware chain [DESIGN ISSUE]

**File:** `oberoon/app.py:54-59`

```python
if path_info.startswith("/static"):
    return self.whitenoise(environ, start_response)
else:
    return self.middleware(environ, start_response)
```

Requests to `/static/*` skip all registered middleware. Authentication middleware, logging middleware, and CORS middleware are all silently bypassed for static assets. This is not documented.

---

### 3.9 No request body size limit [VULNERABILITY — DoS]

There is no limit on request body size. A client can stream an arbitrarily large body and exhaust server memory. WebOb will buffer the entire request body by default.

---

### 3.10 No response headers API [MISSING FEATURE]

`Response` provides no way to set custom HTTP headers. Cookies, CORS headers, cache control, redirects, and content-disposition are all impossible through the public API. The internal `WebResponse` object is not exposed.

---

## 4. Summary Table

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| 3.1 | `pyproject.toml` | `parse` not in declared dependencies | **High** |
| 3.2 | `response.py:35` | `text` body not encoded to bytes — runtime crash | **High** |
| 3.3 | `response.py:26-36` | `if` instead of `elif` — last setter silently wins | Medium |
| 3.4 | `app.py:95-99` | Exception handler skipped for class-based views | Medium |
| 3.5 | `app.py:194` | Mutable default argument `context={}` | Medium |
| 3.6 | `app.py:159` | `assert` removed by `-O`, duplicate routes silently allowed | Medium |
| 3.7 | `app.py:35` | Jinja2 autoescape off — XSS risk in templates | Medium |
| 3.8 | `app.py:54` | Static files bypass middleware chain | Low |
| 3.9 | whole app | No request body size limit — DoS via memory exhaustion | Medium |
| 3.10 | `response.py` | No custom headers API | Low |
| Dep | `requests-wsgi-adapter` | Abandoned since 2016, no security support | **High** |
| Dep | `parse` | Missing from `pyproject.toml`; O(n) routing; ambiguous matching | **High** |
| Dep | `webob` | Heavyweight for the 2 features used; consider lighter alternative | Low |
