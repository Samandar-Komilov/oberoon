from oberoon import Oberoon, Request, Router, TextResponse

from examples.routers import users_router

app = Oberoon()


@app.get("/hello")
async def hello(request: Request) -> TextResponse:
    return TextResponse("Hello!")


@app.get("/hello/{id}")
async def hello2(request: Request, id: int) -> dict:
    return {"message": "Hello!", "id": id}


v1Router = Router(prefix="/v1")


@v1Router.get("/health")
async def health(request: Request) -> dict:
    return {"status": "ok"}


v1Router.include_router(users_router)

app.include_router(v1Router)
