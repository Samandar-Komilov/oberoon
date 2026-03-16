# Plan: Attachable Routers (`app.include_router`)

## Context

All prerequisite routing bugs are fixed. The goal is to add FastAPI-style attachable routers so routes can be organized in separate modules and mounted with a prefix via `app.include_router(router, prefix="/api")`.

---

## Design

- **Deferred compilation**: `Router` stores raw path strings + handler refs. Regex compilation happens at `include_router()` time when the full prefix is known.
- **Shared decorator API**: Extract decorator methods (`route/get/post/put/patch/delete`) into a `RoutingMixin` — both `Oberoon` and `Router` inherit it, eliminating duplication.
- **Nesting**: `router.include_router(sub_router, prefix="/v1")` stores a reference; recursive flattening happens when the top-level app mounts it.

---

## Step 1: Add `RouteRecord` and `RoutingMixin` to `oberoon/routing.py`

**`RouteRecord`** — new dataclass storing uncompiled route info:
```
path: str, handler: Callable, methods: set[str]
```

**`RoutingMixin`** — provides shared decorator registration:
- `_route_records: list[RouteRecord]` — routes registered directly
- `_sub_routers: list[tuple[str, RoutingMixin]]` — nested routers with their prefix
- `__init_routing__()` — initializes both lists (called from subclass `__init__`)
- `route(path, methods)` — creates `RouteRecord`, appends to `_route_records`
- `get/post/put/patch/delete(path)` — convenience wrappers calling `route()`
- `include_router(router, prefix="")` — appends `(prefix, router)` to `_sub_routers`

## Step 2: Add `Router` class to `oberoon/routing.py`

```python
class Router(RoutingMixin):
    def __init__(self):
        self.__init_routing__()
```

Minimal — just a container with the inherited decorator API.

## Step 3: Add `_collect_routes()` to `oberoon/routing.py`

Recursive function that flattens a `RoutingMixin` tree into compiled `Route` objects:

```
_collect_routes(mixin, prefix="") -> list[Route]
```

- For each `RouteRecord` in `mixin._route_records`: compile `prefix + record.path` via existing `compile_path()`, produce a `Route`
- For each `(sub_prefix, sub_router)` in `mixin._sub_routers`: recurse with `prefix + sub_prefix`
- Prefix normalization: `prefix.rstrip("/") + path` (path always starts with `/`)

## Step 4: Modify `Oberoon` in `oberoon/core.py`

- Inherit from `RoutingMixin`
- Call `self.__init_routing__()` in `__init__`
- Keep `self._routes: list[Route]` for compiled routes (used by `find_handler`)
- **Override `route()`** to both store a `RouteRecord` AND eagerly compile + append to `_routes` (preserves current direct-decorator behavior)
- **Override `include_router()`** to call `_collect_routes(router, prefix)` and extend `self._routes`
- Remove the duplicate `get/post/put/patch/delete` methods — inherited from `RoutingMixin`

## Step 5: Update exports in `oberoon/__init__.py`

Add `Router` to imports and `__all__`.

## Step 6: Update `examples/initial.py`

Demonstrate router usage with prefix mounting.

## Step 7: Add tests in `tests/test_router.py`

- Router with prefix: `GET /api/hello`
- Nested routers: `GET /api/v1/users`
- Empty prefix
- Direct app routes still work alongside included routers
- Path params through router prefix
- 404/405 on router routes

---

## Files to modify

| File | Change |
|------|--------|
| `oberoon/routing.py` | Add `RouteRecord`, `RoutingMixin`, `Router`, `_collect_routes` |
| `oberoon/core.py` | Inherit `RoutingMixin`, override `route()` + `include_router()`, remove duplicate decorators |
| `oberoon/__init__.py` | Export `Router` |
| `examples/initial.py` | Add router demo |
| `tests/test_router.py` | New test file for router features |

## Verification

```bash
pytest tests/ -v
```
