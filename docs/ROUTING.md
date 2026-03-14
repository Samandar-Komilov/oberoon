# Routing Flow — State Machine

## Registration Phase (import time)

```
                    @app.get("/users/{id:int}")
                    @app.post("/users")
                              |
                              v
                  +-----------------------+
                  |  compile_path(path)   |
                  |                       |
                  |  "{id:int}" -> regex  |
                  |  extract param_types  |
                  +-----------------------+
                              |
                              v
                  +-----------------------+
                  |  Create Route(        |
                  |    pattern,           |
                  |    param_types,       |
                  |    handler,           |
                  |    methods            |
                  |  )                    |
                  +-----------------------+
                              |
                              v
                  +-----------------------+
                  |  Append to            |
                  |  self._routes         |
                  +-----------------------+
```

## Request Phase (runtime)

```
    ASGI Server (uvicorn)
              |
              |  scope, receive, send
              v
    +-------------------+
    | Oberoon.__call__  |
    |                   |
    | scope["type"] = ? |
    +-------------------+
         |         |          |
    "lifespan" "websocket"  "http"
         |         |          |
         v         v          v
     (startup/  NotImpl    +--------------------------+
      shutdown  Error)     | S1: Build Request        |
                           |                          |
                           | request = Request(       |
                           |   scope, receive         |
                           | )                        |
                           | response = Response()    |
                           +--------------------------+
                                       |
                                       v
                           +--------------------------+
                           | S2: Extract method, path |
                           |                          |
                           | method = request.method  |
                           | path   = request.path    |
                           +--------------------------+
                                       |
                                       v
                           +--------------------------+
                           | S3: Linear scan          |
                           |     self._routes         |
                           +--------------------------+
                                       |
                            +----------+----------+
                            |                     |
                       route found           no route found
                            |                     |
                            v                     v
                  +------------------+    +--------------+
                  | S4: Path match?  |    | S7: 404      |
                  |                  |    | Not Found    |
                  | route.pattern    |    +--------------+
                  |   .match(path)   |            |
                  +------------------+            |
                       |          |               |
                  match=Yes   match=No            |
                       |          |               |
                       |          +---> continue scan (next route)
                       v                if exhausted -> S7
                  +------------------+
                  | S5: Method ok?   |
                  |                  |
                  | method in        |
                  | route.methods?   |
                  +------------------+
                       |          |
                    Yes          No
                       |          |
                       |          v
                       |   +---------------------+
                       |   | S6: 405              |
                       |   | Method Not Allowed   |
                       |   |                      |
                       |   | Allow: GET, POST     |
                       |   | (collect allowed     |
                       |   |  methods from all    |
                       |   |  path-matching       |
                       |   |  routes)             |
                       |   +---------------------+
                       |          |
                       v          |
                  +------------------+
                  | S8: Extract      |
                  | path params      |
                  |                  |
                  | match.groupdict()|
                  | coerce types via |
                  | route.param_types|
                  +------------------+
                       |
                       v
                  +------------------+
                  | S9: Call handler  |
                  |                  |
                  | result = await   |
                  |  handler(request)|
                  +------------------+
                       |
                       v
                  +------------------+
                  | S10: Build       |
                  | response from    |
                  | handler result   |
                  +------------------+
                       |
                       +<-- (S6, S7 also feed here)
                       |
                       v
                  +------------------+
                  | S11: Send        |
                  |                  |
                  | response.send(   |
                  |   send           |
                  | )                |
                  |                  |
                  | -> http.response |
                  |    .start        |
                  | -> http.response |
                  |    .body         |
                  +------------------+
                       |
                       v
                     Done
```

## State Summary

| State | Input | Output | Next |
|-------|-------|--------|------|
| S1 | scope, receive | Request, Response objects | S2 |
| S2 | Request | method, path strings | S3 |
| S3 | method, path, _routes | iteration begins | S4 or S7 |
| S4 | route.pattern, path | regex match or None | S5 (match) / next route (no match) / S7 (exhausted) |
| S5 | route.methods, method | membership check | S8 (yes) / S6 (no) |
| S6 | all path-matching routes | 405 + Allow header | S11 |
| S7 | — | 404 response | S11 |
| S8 | match.groupdict(), param_types | typed path params dict | S9 |
| S9 | handler, request, path_params | handler return value | S10 |
| S10 | handler result | populated Response | S11 |
| S11 | Response, send callable | ASGI messages sent | Done |

## Key Decision Points

**S4 vs S7 — the scan behavior:**
The linear scan must NOT stop at the first path match if the method is wrong. Consider: route A registers `GET /users/{id}`, route B registers `POST /users/{id}`. A `POST /users/42` request must find route B, not stop at route A and return 405.

Two valid strategies:
1. **Continue scanning** after path-match + method-mismatch — find the full match if it exists, collect allowed methods as you go for a potential 405
2. **Separate routes by path** — same path with different methods becomes one Route with a combined method set. Then a path match is always definitive

Strategy 2 is simpler for the lookup but changes how registration works. Strategy 1 is simpler for registration but makes the scan slightly more complex. Pick one.

**S6 — the Allow header:**
RFC 9110 requires `405 Method Not Allowed` responses to include an `Allow` header. This means the scan (S3-S5) must collect all methods registered for the matched path, not just check the first match. This is easy if you chose strategy 2 above (one Route per path). If you chose strategy 1, you need to accumulate methods across multiple path-matching routes.

**S9 — the handler contract:**
What the handler receives and returns determines the shape of S8, S9, and S10. This is where Phase 2 ends and Phase 2.5/4/5 extend. Keep S9 simple now — pass request, get Response back — and expand later.
