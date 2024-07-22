from webob import Request, Response


class Oberoon:
    def __init__(self):
        self.routes = dict()

    def __call__(self, environ, start_response, *args, **kwargs):
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)
    
    def handle_request(self, request):
        response = Response()
        handler = self.find_handler(request)
        if handler:
            handler(request, response)
        else:
            self.default_response(response)

        return response
    
    def find_handler(self, request):
        for path, handler in self.routes.items():
            if path == request.path:
                return handler

    def default_response(self, response):
        response.status_code = 404
        response.text = "Not found."

    def route(self, path):
        def wrapper(handler):
            self.routes[path] = handler
            return handler
        return wrapper