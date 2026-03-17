import httpx
import pytest

from oberoon import Oberoon, HTTPException, Request, Response


@pytest.fixture
def app():
    app = Oberoon()

    @app.get("/hello")
    async def hello(request: Request) -> Response:
        response = Response(200)
        response.set_body(b"Hello!", content_type="text/plain")
        return response

    @app.get("/users/{user_id:int}")
    async def get_user(request: Request, user_id: int) -> Response:
        response = Response(200)
        response.set_body(
            f'{{"user_id": {user_id}, "type": "{type(user_id).__name__}"}}'.encode(),
            content_type="application/json",
        )
        return response

    @app.post("/users")
    async def create_user(request: Request) -> Response:
        response = Response(201)
        response.set_body(b'{"created": true}', content_type="application/json")
        return response

    @app.get("/items/{name}")
    async def get_item(request: Request, name: str) -> Response:
        response = Response(200)
        response.set_body(name.encode(), content_type="text/plain")
        return response

    @app.route("/multi", methods=["GET", "POST"])
    async def multi(request: Request) -> Response:
        response = Response(200)
        response.set_body(request.method.encode(), content_type="text/plain")
        return response

    @app.get("/forbidden")
    async def forbidden(request: Request) -> Response:
        raise HTTPException(403, "Access denied")

    @app.get("/teapot")
    async def teapot(request: Request) -> Response:
        raise HTTPException(418, "I'm a teapot")

    @app.get("/no-detail")
    async def no_detail(request: Request) -> Response:
        raise HTTPException(500)

    return app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
