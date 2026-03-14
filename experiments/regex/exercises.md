# Regex Exercises: Capturing Groups for Routing & Validators

Work through these 20 exercises in order. Each one builds on concepts from the previous. Write your regex, then test it against every listed test case — all must pass (match/no-match and captured groups must be correct).

**Notation used below:**

- ✅ `"/users/alice"` → `["alice"]` means the string should match and the captured groups (in order) should be `alice`.
- ❌ `"/users/"` means the string should **not** match.
- `[undefined]` means the group exists but did not participate in the match (optional group).

---

## Part 1 — Routing Foundations

### Exercise 1: Basic Path Segment Capture

Match `/users/alice` and capture the username (lowercase letters only).

```
✅ "/users/alice"    → ["alice"]
✅ "/users/bob"      → ["bob"]
❌ "/users/"
❌ "/items/alice"
```

<details><summary>Hint</summary>Literal prefix + one capturing group: <code>[a-z]+</code></details>
<details><summary>Solution</summary><code>^\/users\/([a-z]+)$</code></details>

---

### Exercise 2: Numeric ID Capture

Match `/orders/12345` and capture the order ID (digits only).

```
✅ "/orders/12345"   → ["12345"]
✅ "/orders/7"       → ["7"]
❌ "/orders/abc"
❌ "/orders/"
```

<details><summary>Hint</summary>Use <code>\d+</code> inside a capturing group.</details>
<details><summary>Solution</summary><code>^\/orders\/(\d+)$</code></details>

---

### Exercise 3: Multiple Path Parameters

Match `/users/42/posts/99` and capture both the user ID and post ID.

```
✅ "/users/42/posts/99"    → ["42", "99"]
✅ "/users/1/posts/300"    → ["1", "300"]
❌ "/users/abc/posts/99"
❌ "/users/42/comments/99"
```

<details><summary>Hint</summary>Two literal segments with two capturing groups.</details>
<details><summary>Solution</summary><code>^\/users\/(\d+)\/posts\/(\d+)$</code></details>

---

### Exercise 4: Optional Trailing Slash

Match `/api/items` with or without a trailing slash. Capture the resource name (lowercase letters).

```
✅ "/api/items"   → ["items"]
✅ "/api/items/"  → ["items"]
✅ "/api/users"   → ["users"]
❌ "/api/"
❌ "/api/Items"
```

<details><summary>Hint</summary><code>\/?</code> makes the trailing slash optional. <code>?</code> means 0 or 1.</details>
<details><summary>Solution</summary><code>^\/api\/([a-z]+)\/?$</code></details>

---

## Part 2 — Advanced Routing

### Exercise 5: Named Capturing Groups

Match `/products/shoes/size/10`. Use **named groups** to capture `category` (lowercase letters) and `size` (digits).

```
✅ "/products/shoes/size/10"  → category="shoes", size="10"
✅ "/products/hats/size/7"    → category="hats", size="7"
❌ "/products//size/10"
❌ "/products/SHOES/size/10"
```

<details><summary>Hint</summary>Named group syntax: <code>(?&lt;name&gt;pattern)</code>.</details>
<details><summary>Solution</summary><code>^\/products\/(?&lt;category&gt;[a-z]+)\/size\/(?&lt;size&gt;\d+)$</code></details>

---

### Exercise 6: Slug-Style Path Parameter

Match `/blog/my-first-post` and capture the slug. A slug is lowercase letters, digits, and hyphens, but must **not** start or end with a hyphen.

```
✅ "/blog/my-first-post"  → ["my-first-post"]
✅ "/blog/hello123"       → ["hello123"]
✅ "/blog/a"              → ["a"]
❌ "/blog/-bad-slug"
❌ "/blog/bad-slug-"
```

<details><summary>Hint</summary>Bookend the slug with <code>[a-z0-9]</code> and allow <code>[a-z0-9-]*</code> in between. Handle the single-char edge case with <code>?</code>.</details>
<details><summary>Solution</summary><code>^\/blog\/([a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)$</code></details>

---

### Exercise 7: Optional Sub-Resource with Non-Capturing Group

Match `/users/42` or `/users/42/profile`. Always capture the user ID. Capture `profile` only if present (otherwise the group should be `undefined`).

```
✅ "/users/42"          → ["42", undefined]
✅ "/users/42/profile"  → ["42", "profile"]
❌ "/users/42/settings"
❌ "/users/abc"
```

<details><summary>Hint</summary>Wrap the optional segment in a non-capturing group <code>(?:...)?</code> containing a capturing group for just the word <code>profile</code>.</details>
<details><summary>Solution</summary><code>^\/users\/(\d+)(?:\/(profile))?$</code></details>

---

### Exercise 8: HTTP Method + Path Routing

Match routing strings like `GET /api/users`. Capture the method (GET, POST, PUT, DELETE, or PATCH) and the full path (starting with `/api/`).

```
✅ "GET /api/users"       → ["GET", "/api/users"]
✅ "POST /api/items/5"    → ["POST", "/api/items/5"]
✅ "DELETE /api/users/1"  → ["DELETE", "/api/users/1"]
❌ "OPTIONS /api/users"
❌ "GET /home"
```

<details><summary>Hint</summary>Use alternation for methods: <code>(GET|POST|PUT|DELETE|PATCH)</code>, then <code>\s</code> and a group for the path.</details>
<details><summary>Solution</summary><code>^(GET|POST|PUT|DELETE|PATCH)\s(\/api\/\S+)$</code></details>

---

### Exercise 9: Query String Extraction

Match a path with an optional query string like `/search?q=hello&page=2`. Capture the path (before `?`) and the query string (after `?`, without the `?` itself). If no query string, the second group should be `undefined`.

```
✅ "/search?q=hello&page=2"  → ["/search", "q=hello&page=2"]
✅ "/api/data?format=json"   → ["/api/data", "format=json"]
✅ "/home"                   → ["/home", undefined]
❌ "?q=hello"
```

<details><summary>Hint</summary>Path: <code>(\/[^?]*)</code>. Optional query: <code>(?:\?(.+))?</code>.</details>
<details><summary>Solution</summary><code>^(\/[^?]*)(?:\?(.+))?$</code></details>

---

### Exercise 10: Route Template Token Compiler

Match route template tokens like `{user_id:int}` or `{slug:str}`. Capture the parameter name (letters and underscores) and the type constraint (`int` or `str`).

```
✅ "{user_id:int}"   → ["user_id", "int"]
✅ "{slug:str}"      → ["slug", "str"]
✅ "{page_num:int}"  → ["page_num", "int"]
❌ "{123:int}"
❌ "{slug:float}"
```

<details><summary>Hint</summary>Escape the braces. Name: <code>[a-zA-Z_]+</code>. Type: <code>(int|str)</code>.</details>
<details><summary>Solution</summary><code>^\{([a-zA-Z_]+):(int|str)\}$</code></details>

---

## Part 3 — Phone Number Validators

### Exercise 11: Simple US Phone Format

Match `(555) 123-4567`. Capture area code, exchange, and subscriber as 3 groups.

```
✅ "(555) 123-4567"  → ["555", "123", "4567"]
✅ "(212) 999-0000"  → ["212", "999", "0000"]
❌ "555-123-4567"
❌ "(55) 123-4567"
```

<details><summary>Hint</summary>Literal parens around <code>\d{3}</code>, then space, <code>\d{3}</code>, hyphen, <code>\d{4}</code>.</details>
<details><summary>Solution</summary><code>^\((\d{3})\)\s(\d{3})-(\d{4})$</code></details>

---

### Exercise 12: Flexible US Phone (Backreference)

Match three formats: `555-123-4567`, `(555) 123-4567`, and `555.123.4567`. The separator between exchange and subscriber must be consistent with the separator between area code and exchange (for the non-parenthesized formats). Capture area code, exchange, and subscriber.

```
✅ "555-123-4567"    → groups include "555", "123", "4567"
✅ "(555) 123-4567"  → groups include "555", "123", "4567"
✅ "555.123.4567"    → groups include "555", "123", "4567"
❌ "555-123.4567"
❌ "5551234567"
```

<details><summary>Hint</summary>Use alternation with two branches. For the non-paren branch, capture the separator and use a backreference <code>\N</code> to enforce consistency. Group numbering across alternation branches is tricky — count carefully.</details>
<details><summary>Solution</summary><code>^(?:\((\d{3})\)\s(\d{3})-(\d{4})|(\d{3})([-.])(\d{3})\5(\d{4}))$</code>

Note: Groups 1-3 fire for the parenthesized format; groups 4, 6, 7 fire for the other format (group 5 is the separator). In real code you'd normalize the output.</details>

---

### Exercise 13: International Phone with Country Code

Match `+1-555-123-4567` or `+44-20-7946-0958`. Capture: country code (1–3 digits after `+`) and the remaining number body (digit groups separated by hyphens, at least 2 groups).

```
✅ "+1-555-123-4567"     → ["1", "555-123-4567"]
✅ "+44-20-7946-0958"    → ["44", "20-7946-0958"]
✅ "+998-71-123-4567"    → ["998", "71-123-4567"]
❌ "+1234-555-1234"
❌ "1-555-123-4567"
```

<details><summary>Hint</summary>After <code>\+</code>, capture 1–3 digits. Then a hyphen. Then the body: <code>(\d+(?:-\d+)+)</code> ensures at least two digit-groups.</details>
<details><summary>Solution</summary><code>^\+(\d{1,3})-(\d+(?:-\d+)+)$</code></details>

---

## Part 4 — Email Validators

### Exercise 14: Basic Email

Match `user@example.com`. Capture the local part and domain separately. The domain must contain at least one dot.

```
✅ "user@example.com"           → ["user", "example.com"]
✅ "first.last@company.co.uk"   → ["first.last", "company.co.uk"]
❌ "@example.com"
❌ "user@.com"
❌ "user@com"
```

<details><summary>Hint</summary>Local: <code>[a-zA-Z0-9._-]+</code>. Domain needs at least one dot: <code>[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+</code>.</details>
<details><summary>Solution</summary><code>^([a-zA-Z0-9._-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+)$</code></details>

---

### Exercise 15: Email with Plus Addressing (Optional Subgroup)

Match `user+tag@example.com`. Capture three groups: the base local part, the optional tag (without the `+`), and the domain. If no tag, that group should be `undefined`.

```
✅ "user+shopping@example.com"  → ["user", "shopping", "example.com"]
✅ "user@example.com"           → ["user", undefined, "example.com"]
✅ "a.b+test@mail.co"           → ["a.b", "test", "mail.co"]
❌ "+tag@example.com"
```

<details><summary>Hint</summary>Make the <code>+tag</code> part optional: wrap it in a non-capturing group containing a capturing group: <code>(?:\+([a-zA-Z0-9._-]+))?</code>.</details>
<details><summary>Solution</summary><code>^([a-zA-Z0-9._-]+)(?:\+([a-zA-Z0-9._-]+))?@([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+)$</code></details>

---

## Part 5 — Custom Validators

### Exercise 16: Semantic Version

Match semver strings like `1.2.3`. Capture major, minor, and patch.

```
✅ "1.2.3"    → ["1", "2", "3"]
✅ "0.10.99"  → ["0", "10", "99"]
❌ "1.2"
❌ "v1.2.3"
❌ "1.2.3.4"
```

<details><summary>Hint</summary>Three groups of <code>\d+</code> separated by literal dots, anchored.</details>
<details><summary>Solution</summary><code>^(\d+)\.(\d+)\.(\d+)$</code></details>

---

### Exercise 17: Semver with Optional Pre-release Tag

Extend semver to also match `1.2.3-beta.1`. Capture major, minor, patch, and the optional pre-release label (everything after the hyphen). Pre-release contains letters, digits, and dots.

```
✅ "1.2.3-beta.1"  → ["1", "2", "3", "beta.1"]
✅ "2.0.0-rc.2"    → ["2", "0", "0", "rc.2"]
✅ "1.0.0"         → ["1", "0", "0", undefined]
❌ "1.2.3-"
```

<details><summary>Hint</summary>Append an optional non-capturing group: <code>(?:-([a-zA-Z0-9.]+))?</code>.</details>
<details><summary>Solution</summary><code>^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?$</code></details>

---

### Exercise 18: IPv4 Address (Structural)

Match an IPv4 address and capture all four octets. Each octet is 1–3 digits (don't validate the 0–255 range, just the structure).

```
✅ "192.168.1.1"   → ["192", "168", "1", "1"]
✅ "10.0.0.255"    → ["10", "0", "0", "255"]
❌ "192.168.1"
❌ "1234.1.1.1"
❌ "192.168.1.1.1"
```

<details><summary>Hint</summary>Four groups of <code>\d{1,3}</code> separated by escaped dots.</details>
<details><summary>Solution</summary><code>^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$</code></details>

---

### Exercise 19: Password Strength with Lookaheads

Validate that a password has at least 8 characters, at least one uppercase letter, one lowercase letter, and one digit. Use **lookaheads**. Capture the entire password as group 1.

```
✅ "Abcdef1x"    → ["Abcdef1x"]
✅ "MyP4ssword"  → ["MyP4ssword"]
❌ "abcdefgh"
❌ "ABCDEFG1"
❌ "Abc1"
```

<details><summary>Hint</summary>Stack lookaheads at the start: <code>(?=.*[A-Z])(?=.*[a-z])(?=.*\d)</code>, then capture <code>.{8,}</code>.</details>
<details><summary>Solution</summary><code>^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(.{8,})$</code></details>

---

## Part 6 — Capstone

### Exercise 20: Full ASGI Route Definition Parser

Match a full ASGI-style route definition like `GET /api/v{version:\d+}/users/{id:\d+}/posts`. Capture three things: the HTTP method (uppercase letters), the full path template (starting with `/`), and the **first** path parameter name found inside `{name:...}`.

```
✅ "GET /api/v{version:\d+}/users/{id:\d+}/posts"
   → ["GET", "/api/v{version:\d+}/users/{id:\d+}/posts", "version"]

✅ "POST /items/{item_id:\d+}"
   → ["POST", "/items/{item_id:\d+}", "item_id"]

❌ "get /api/test"     (lowercase method)
❌ "GET api/test"      (path missing leading /)
```

<details><summary>Hint</summary>Capture the method <code>([A-Z]+)</code>, then the full path. Within the path, find the first <code>{name:...}</code> and capture <code>name</code>. You need the path group to contain a nested <code>\{([a-zA-Z_]+):[^}]+\}</code> somewhere.</details>
<details><summary>Solution</summary><code>^([A-Z]+)\s(\/\S*\{([a-zA-Z_]+):[^}]+\}\S*)$</code></details>

---

## Concepts Covered

| Concept | Exercises |
|---|---|
| Basic capturing groups `()` | 1–4, 11 |
| Multiple captures | 3, 8, 9, 11, 16 |
| Named groups `(?<n>...)` | 5 |
| Non-capturing groups `(?:...)` | 6, 7, 9, 15, 17 |
| Optional groups with `?` | 4, 7, 9, 15, 17 |
| Alternation `\|` | 8, 10, 12 |
| Backreferences `\N` | 12 |
| Lookaheads `(?=...)` | 19 |
| Character classes and quantifiers | All |
| Anchors `^` `$` | All |
| Escaping special chars `\.` `\/` `\{` | 6, 10, 13, 16–18, 20 |
| Nested groups | 6, 13, 17, 20 |