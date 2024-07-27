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


@app.route("/books")
class Books:
    def get(self, request, response):
        response.text = "Books page"
    
    def post(self, request, response):
        response.text = "Endpoint to create a book\n"


def new_handler(request, response):
    response.text = "From new handler"

app.add_route("/new-handler", new_handler)