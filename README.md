# Oberoon: Python Web Framework

![Oberoon logo](./oberoon.png)

![purpose](https://img.shields.io/badge/purpose-learning-green)

![PyPI - Version](https://img.shields.io/pypi/v/oberoon)

Oberoon is a WSGI framework for Python, written for mainly learning purposes. Can be used with any WSGI server such as Gunicorn. 

Soon, the author is planning to release his own WSGI server - Obicorn, then you can easily integrate the framework with it.

**Source code**: https://github.com/Samandar-Komilov/oberoon

## Installation

```bash
  pip install oberoon
```

## How to use it

### Basic Usage

```python
from oberoon.app import Oberoon


app = Oberoon()


# Simple text response handlers
@app.route("/home", allowed_methods=["get"])
def home(request, response):
    response.text = "Hello from the Home Page"


# Parametrized handlers
@app.route("/hello/{name}")
def greeting(request, response, name):
    response.text = f"Hello {name}"


# Class-based handlers
@app.route("/books")
class Books:
    def get(self, request, response):
        response.text = "Books page"
    
    def post(self, request, response):
        response.text = "Endpoint to create a book\n"


# Explicit addition of handlers
def new_handler(request, response):
    response.text = "From new handler"

app.add_route("/new-handler", new_handler)


# Templates support
@app.route("/template")
def template(req, resp):
    resp.body = app.template(
        "home.html",
        context = {"new_title": "Best Title", "new_body": "Best Body"}
    ).encode()


# JSON response handlers
@app.route("/json")
def json_handler(request, response):
    response_data = {"name": "some name", "type": "json"}
    response.json = response_data
```

## Unit Tests

The recommended way of writing unit tests is with [pytest](https://docs.pytest.org/en/stable/). Here is an example:

```python
def test_basic_route_adding(app):
    @app.route('/home')
    def home(req, resp):
        resp.text = "Hello from Home"


def test_parametrized_routes(app, test_client):
    @app.route("/hello/{name}")
    def greeting(request, response, name):
        response.text = f"Hello {name}"

    assert test_client.get("http://testserver/hello/Sam").text == "Hello Sam"


def test_class_based_get(app, test_client):
    @app.route("/books")
    class Books:
        def get(self, request, response):
            response.text = "Books page"

    response = test_client.get("http://testserver/books")
    assert response.text == "Books page"
    assert response.status_code == 200
```
