from oberoon import Oberoon, Request, Response, setup_logging

setup_logging()

app = Oberoon()


@app.get("/hello")
async def hello(request: Request) -> Response:
    response = Response(200)
    response.set_body(b"Hello!", content_type="text/plain")
    return response


@app.get("/hello/{id}")
async def hello2(request: Request, id: int) -> Response:
    response = Response(200)
    response.set_body(b"Hello 1!", content_type="text/plain")
    return response
