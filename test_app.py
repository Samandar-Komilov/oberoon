from conftest import app, test_client
import pytest


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
    response = test_client.get("http://testserver/test.css")

    assert response.text == "body { background-color: #fff; }"