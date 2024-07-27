from webob import Request, Response
from parse import parse
import inspect
import wsgiadapter
import requests


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
            if inspect.isclass(handler):
                handler_method = getattr(handler(), request.method.lower(), None)
                if handler_method is None:
                    response.text = "Method Not Allowed."
                    response.status_code = 405
                    return response
                handler_method(request, response, **kwargs)
            else:
                handler(request, response, **kwargs)
        else:
            self.default_response(response)

        return response
    
    def find_handler(self, request):
        for path, handler in self.routes.items():
            # parse("It's {}, I love it!", "It's spam, I love it!")
            print(path, request.path)
            result_parse = parse(path, request.path)
            print(result_parse)
            if result_parse:
                # named method returns dictionary instead of Result object
                return handler, result_parse.named
            
        return None, None

    def default_response(self, response):
        response.status_code = 404
        response.text = "Not found."

    def route(self, path):
        assert path not in self.routes, f"Duplicate route {path}. Please change the URL."

        def wrapper(handler):
            self.routes[path] = handler
            return handler
        return wrapper

    def test_session(self):
        session = requests.Session()
        session.mount('http://testserver', wsgiadapter.WSGIAdapter(self))
        return session