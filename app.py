from webob import Request, Response
from parse import parse


class Oberoon:
    def __init__(self):
        self.routes = dict()

    def __call__(self, environ, start_response, *args, **kwargs):
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)
    
    def handle_request(self, request):
        response = Response()
        handler, kwargs = self.find_handler(request)
        if handler:
            handler(request, response, **kwargs)
        else:
            self.default_response(response)

        return response
    
    def find_handler(self, request):
        for path, handler in self.routes.items():
            # parse("It's {}, I love it!", "It's spam, I love it!")
            result_parse = parse(path, request.path)
            if result_parse:
                # named method returns dictionary instead of Result object
                return handler, result_parse.named
            
        return None, None

    def default_response(self, response):
        response.status_code = 404
        response.text = "Not found."

    def route(self, path):
        def wrapper(handler):
            self.routes[path] = handler
            return handler
        return wrapper