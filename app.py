from webob import Request, Response
from parse import parse
import inspect
import wsgiadapter
import requests
from jinja2 import Environment, FileSystemLoader
import os
from whitenoise import WhiteNoise


class Oberoon:
    def __init__(self, templates_dir="templates", static_dir="static"):
        self.routes = dict()

        self.template_env = Environment(
            loader=FileSystemLoader(os.path.abspath(templates_dir))
        )
        self.exception_handler = None
        self.whitenoise = WhiteNoise(self.wsgi_app, root=static_dir)

    def __call__(self, environ, start_response, *args, **kwargs):
        return self.whitenoise(environ, start_response)
    
    def wsgi_app(self, environ, start_response):
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
                try:
                    handler(request, response, **kwargs)
                except Exception as e:
                    if self.exception_handler:
                        self.exception_handler(request, response, e)
                    else:
                        raise e
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

    def add_route(self, path, handler):
        assert path not in self.routes, "Duplicate route. Please change the URL."
        self.routes[path] = handler

    def route(self, path):

        def wrapper(handler):
            self.add_route(path, handler)
            return handler
        return wrapper

    def test_session(self):
        session = requests.Session()
        session.mount('http://testserver', wsgiadapter.WSGIAdapter(self))
        return session

    def template(self, template_name, context={}):
        return self.template_env.get_template(template_name).render(**context)

    def add_exception_handler(self, handler):
        self.exception_handler = handler