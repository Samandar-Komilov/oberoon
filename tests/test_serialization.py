"""Tests for msgspec integration: typed request bodies, auto response serialization, validation."""

from typing import Annotated

import httpx
import pytest

from oberoon import (
    Oberoon,
    BaseModel,
    Field,
    Request,
    Response,
    JSONResponse,
    TextResponse,
)

pytestmark = pytest.mark.anyio


# ── Models ──────────────────────────────────────────────────────────────────


class CreateUser(BaseModel):
    name: str
    email: str
    age: int = 0


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


class ConstrainedModel(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=50)]
    score: Annotated[int, Field(ge=0, le=100)]


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    app = Oberoon()

    # Return a Struct → auto JSON
    @app.get("/users/{user_id:int}")
    async def get_user(request: Request, user_id: int) -> UserResponse:
        return UserResponse(id=user_id, name="Alice", email="alice@example.com")

    # Body param + Struct return
    @app.post("/users")
    async def create_user(request: Request, body: CreateUser) -> UserResponse:
        return UserResponse(id=1, name=body.name, email=body.email)

    # Return a dict with typed return annotation
    @app.get("/dict-typed")
    async def dict_typed(request: Request) -> dict:
        return {"key": "value"}

    # Return a list with typed annotation
    @app.get("/users-list")
    async def users_list(request: Request) -> list[UserResponse]:
        return [
            UserResponse(id=1, name="Alice", email="a@b.com"),
            UserResponse(id=2, name="Bob", email="b@b.com"),
        ]

    # Return a Response directly (passthrough)
    @app.get("/raw-response")
    async def raw_response(request: Request) -> Response:
        return JSONResponse({"raw": True}, status_code=200)

    # Return TextResponse
    @app.get("/text")
    async def text(request: Request) -> TextResponse:
        return TextResponse("hello")

    # Return None → 204
    @app.post("/fire-and-forget")
    async def fire_and_forget(request: Request) -> None:
        pass

    # Body with constraints
    @app.post("/constrained")
    async def constrained(request: Request, body: ConstrainedModel) -> dict:
        return {"name": body.name, "score": body.score}

    # Return dict from Struct return type (validates dict → Struct)
    @app.get("/dict-as-struct")
    async def dict_as_struct(request: Request) -> UserResponse:
        return {"id": 42, "name": "Bob", "email": "bob@example.com"}

    return app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Response serialization tests ───────────────────────────────────────────


class TestAutoResponse:
    async def test_struct_return_encodes_json(self, client):
        resp = await client.get("/users/42")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        data = resp.json()
        assert data == {"id": 42, "name": "Alice", "email": "alice@example.com"}

    async def test_dict_typed_return(self, client):
        resp = await client.get("/dict-typed")
        assert resp.status_code == 200
        assert resp.json() == {"key": "value"}

    async def test_untyped_handler_rejected_at_registration(self):
        app = Oberoon()
        with pytest.raises(TypeError, match="return type"):

            @app.get("/untyped")
            async def untyped(request: Request):
                return {"key": "value"}

    async def test_list_of_structs(self, client):
        resp = await client.get("/users-list")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Alice"
        assert data[1]["name"] == "Bob"

    async def test_response_passthrough(self, client):
        resp = await client.get("/raw-response")
        assert resp.status_code == 200
        assert resp.json() == {"raw": True}

    async def test_text_response_passthrough(self, client):
        resp = await client.get("/text")
        assert resp.status_code == 200
        assert resp.text == "hello"
        assert "text/plain" in resp.headers["content-type"]

    async def test_none_return_204(self, client):
        resp = await client.post("/fire-and-forget")
        assert resp.status_code == 204

    async def test_dict_validated_as_struct(self, client):
        resp = await client.get("/dict-as-struct")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"id": 42, "name": "Bob", "email": "bob@example.com"}


# ── Request body decoding tests ────────────────────────────────────────────


class TestBodyDecoding:
    async def test_valid_body(self, client):
        resp = await client.post(
            "/users",
            json={"name": "Charlie", "email": "charlie@example.com", "age": 25},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Charlie"
        assert data["email"] == "charlie@example.com"

    async def test_body_with_defaults(self, client):
        resp = await client.post(
            "/users",
            json={"name": "Charlie", "email": "charlie@example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Charlie"

    async def test_missing_required_field(self, client):
        resp = await client.post(
            "/users",
            json={"name": "Charlie"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"] == "Validation Error"

    async def test_wrong_field_type(self, client):
        resp = await client.post(
            "/users",
            json={"name": "Charlie", "email": "c@b.com", "age": "not-a-number"},
        )
        assert resp.status_code == 422

    async def test_empty_body(self, client):
        resp = await client.post(
            "/users",
            content=b"",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_invalid_json(self, client):
        resp = await client.post(
            "/users",
            content=b"not json at all",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_extra_fields_ignored(self, client):
        resp = await client.post(
            "/users",
            json={"name": "Alice", "email": "a@b.com", "extra": "ignored"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "extra" not in data


# ── Constraint validation tests ─────────────────────────────────────────────


class TestConstraints:
    async def test_valid_constrained(self, client):
        resp = await client.post(
            "/constrained",
            json={"name": "Alice", "score": 85},
        )
        assert resp.status_code == 200
        assert resp.json() == {"name": "Alice", "score": 85}

    async def test_name_too_short(self, client):
        resp = await client.post(
            "/constrained",
            json={"name": "", "score": 50},
        )
        assert resp.status_code == 422

    async def test_name_too_long(self, client):
        resp = await client.post(
            "/constrained",
            json={"name": "x" * 51, "score": 50},
        )
        assert resp.status_code == 422

    async def test_score_below_min(self, client):
        resp = await client.post(
            "/constrained",
            json={"name": "Alice", "score": -1},
        )
        assert resp.status_code == 422

    async def test_score_above_max(self, client):
        resp = await client.post(
            "/constrained",
            json={"name": "Alice", "score": 101},
        )
        assert resp.status_code == 422


# ── Model helper tests ──────────────────────────────────────────────────────


class TestModel:
    def test_to_dict(self):
        user = UserResponse(id=1, name="Alice", email="a@b.com")
        d = user.to_dict()
        assert d == {"id": 1, "name": "Alice", "email": "a@b.com"}
        assert isinstance(d, dict)

    def test_from_dict(self):
        user = UserResponse.from_dict({"id": 1, "name": "Alice", "email": "a@b.com"})
        assert isinstance(user, UserResponse)
        assert user.id == 1
        assert user.name == "Alice"

    def test_from_dict_validation_error(self):
        with pytest.raises(Exception):
            UserResponse.from_dict(
                {"id": "not-int", "name": "Alice", "email": "a@b.com"}
            )

    def test_struct_equality(self):
        a = UserResponse(id=1, name="Alice", email="a@b.com")
        b = UserResponse(id=1, name="Alice", email="a@b.com")
        assert a == b

    def test_defaults(self):
        user = CreateUser(name="Alice", email="a@b.com")
        assert user.age == 0
