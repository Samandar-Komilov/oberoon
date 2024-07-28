from conftest import app, test_client
import pytest
from middleware import Middleware


def test_basic_route_adding(app):
    @app.route('/home')
    def home(req, resp):
        resp.text = "Hello from Home"


def test_duplicate_routes_throw_exception(app):
    @app.route('/home')
    def home(req, resp):
        resp.text = "Hello from Home"

    with pytest.raises(AssertionError):
        @app.route('/home')
        def home2(req, resp):
            resp.text = "Hello from Home2"

"""
We can test many many features, like parametrized routes, default response and etc.
However, we need to send request to do so. But unittests shouldn't have dependency to gunicorn or any other server. 
So, we need wsgi adapter - requests-wsgi-adapter
"""

def test_requests_can_be_sent_by_test_client(app, test_client):
    @app.route('/home')
    def home(req, resp):
        resp.text = "Hello from Home"

    response = test_client.get("http://testserver/home")
    assert response.text == "Hello from Home"


def test_parametrized_routes(app, test_client):
    @app.route("/hello/{name}")
    def greeting(request, response, name):
        response.text = f"Hello {name}"

    assert test_client.get("http://testserver/hello/Sam").text == "Hello Sam"


def test_default_response(app, test_client):
    response = test_client.get("http://testserver/nonexistent")
    assert response.text == "Not found."
    assert response.status_code == 404


def test_class_based_get(app, test_client):
    @app.route("/books")
    class Books:
        def get(self, request, response):
            response.text = "Books page"

    response = test_client.get("http://testserver/books")
    assert response.text == "Books page"
    assert response.status_code == 200


def test_class_based_post(app, test_client):
    @app.route("/books")
    class Books:
        def post(self, request, response):
            response.text = "Endpoint to create a book\n"

    response = test_client.post("http://testserver/books")
    assert response.text == "Endpoint to create a book\n"
    assert response.status_code == 200


def test_class_based_method_not_allowed(app, test_client):
    @app.route("/books")
    class Books:
        def post(self, request, response):
            response.text = "Endpoint to create a book\n"

    response = test_client.get("http://testserver/books")
    assert response.text == "Method Not Allowed."
    assert response.status_code == 405


# Django-like routes

def test_alternative_route_adding(app, test_client):
    def new_handler(req, resp):
        resp.text = "From new handler"

    app.add_route("/new-handler", new_handler)
    
    assert test_client.get("http://testserver/new-handler").text == "From new handler"


# Templates

def test_template_handler(app, test_client):
    @app.route("/test-template")
    def template(req, resp):
        resp.body = app.template(
            "test.html",
            context = {"new_title": "Test Title", "new_body": "Test Body"}
        ).encode()

    response = test_client.get("http://testserver/test-template")
    assert "Test Title" in response.text
    assert "text/html" in response.headers["Content-Type"]


# Custom Exception Handler

def test_custom_exception_handler(app, test_client):
    def on_exception(req, resp, exc):
        resp.text = "Something bad happened"
    
    app.add_exception_handler(on_exception)

    @app.route("/exception")
    def exception_throwing_handler(req, resp):
        raise AttributeError("Some exception")
    
    response = test_client.get("http://testserver/exception")

    assert response.text == "Something bad happened"


# Static files

def test_non_existent_static_file(test_client):
    assert test_client.get("http://testserver/nonexistent.css").status_code == 404


def test_serving_static_file(test_client):
    response = test_client.get("http://testserver/static/test.css")

    assert response.text == "body { background-color: #fff; }"


# Middleware support

def test_middleware_methods_are_called(app, test_client):
    process_request_called = False
    process_response_called = False


    class SimpleMiddleware(Middleware):
        def __init__(self, app):
            super().__init__(app)

        def process_request(self, request):
            nonlocal process_request_called
            process_request_called = True

        def process_response(self, request, response):
            nonlocal process_response_called
            process_response_called = True

    app.add_middleware(SimpleMiddleware)

    @app.route("/home")
    def index(request, response):
        response.text = "from handler"
    
    test_client.get("http://testserver/home")

    # Checking for middleware handlers are working or not
    assert process_request_called == True
    assert process_response_called == True


# Allowed methods

def test_allowed_methods_for_function_based_handlers(app, test_client):
    @app.route("/home", allowed_methods=["post"])
    def home(request, response):
        response.text = "Hello from the Home Page"

    response = test_client.get("http://testserver/home")

    assert response.status_code == 405
    assert response.text == "Method Not Allowed."


# Custom Responses

def test_json_response_helper(app, test_client):
    @app.route("/json")
    def json_handler(request, response):
        response.json = {"name": "oberoon"}

    response = test_client.get("http://testserver/json")
    resp_json = response.json()

    assert response.headers["Content-Type"] == "application/json"
    assert resp_json["name"] == "oberoon"

def test_text_response_helper(app, test_client):
    @app.route("/text")
    def text_handler(request, response):
        response.text = "Simple text message"

    response = test_client.get("http://testserver/text")
    assert response.text == "Simple text message"
    assert "text/plain" in response.headers["Content-Type"]

def test_html_response_helper(app, test_client):
    @app.route("/html")
    def html_handler(request, response):
        response.html = app.template(
            "test.html",
            context={"new_title": "Best Title", "new_body": "Best Body"}
        )

    response = test_client.get("http://testserver/html")
    assert "Best Body" in response.text
    assert "text/html" in response.headers['Content-Type']