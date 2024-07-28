from app import Oberoon
from middleware import Middleware


app = Oberoon()


@app.route("/home", allowed_methods=["get"])
def home(request, response):
    response.text = "Hello from the Home Page"


@app.route("/about")
def about(request, response):
    response.text = "Hello from the About Page"


@app.route("/hello/{name}")
def greeting(request, response, name):
    response.text = f"Hello {name}"


@app.route("/books")
class Books:
    def get(self, request, response):
        response.text = "Books page"
    
    def post(self, request, response):
        response.text = "Endpoint to create a book\n"


def new_handler(request, response):
    response.text = "From new handler"

app.add_route("/new-handler", new_handler)


@app.route("/template")
def template(req, resp):
    resp.body = app.template(
        "home.html",
        context = {"new_title": "Best Title", "new_body": "Best Body"}
    ).encode()


def on_exception(req, resp, exc):
    resp.text = str(exc)

app.add_exception_handler(on_exception)

@app.route("/exception")
def exception_throwing_handler(req, resp):
    raise AttributeError("Some exception")


# Static files support using Whitenoise - we'll use the /template endpoint, but only link static css to the html file


# Middleware support

class LoggingMiddleware(Middleware):
    def process_request(self, request):
        print("Before request: do something:", request.url)
    
    def process_response(self, request, response):
        print("After response: do something:", request.url)

app.add_middleware(LoggingMiddleware)