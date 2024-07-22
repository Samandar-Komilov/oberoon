from app import Oberoon


app = Oberoon()


@app.route("/home")
def home(request, response):
    response.text = "Hello from the Home Page"


@app.route("/about")
def about(request, response):
    response.text = "Hello from the About Page"


@app.route("/hello/{name}")
def greeting(request, response, name):
    response.text = f"Hello {name}"