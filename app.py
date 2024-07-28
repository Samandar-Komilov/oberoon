from webob import Request
from parse import parse
import inspect
import wsgiadapter
import requests
from jinja2 import Environment, FileSystemLoader
import os
from whitenoise import WhiteNoise

from middleware import Middleware
from response import Response


class Oberoon:
    """
    A custom WSGI framework class for handling HTTP requests and responses, routing, and middleware.

    Attributes:
        routes (dict): A dictionary to store route paths and their handlers.
        template_env (Environment): The Jinja2 environment for template rendering.
        exception_handler (callable): A function to handle exceptions.
        whitenoise (WhiteNoise): WhiteNoise instance for serving static files.
        middleware (Middleware): The middleware manager instance.
    """
    def __init__(self, templates_dir="templates", static_dir="static"):
        """
        Initialize the Oberoon framework with directories for templates and static files.

        Args:
            templates_dir (str): The directory where templates are stored. Defaults to "templates".
            static_dir (str): The directory where static files are stored. Defaults to "static".
        """
        self.routes = dict()

        self.template_env = Environment(
            loader=FileSystemLoader(os.path.abspath(templates_dir))
        )
        self.exception_handler = None
        self.whitenoise = WhiteNoise(self.wsgi_app, root=static_dir, prefix='/static')

        self.middleware = Middleware(self)

    def __call__(self, environ, start_response):
        """
        The WSGI entry point for the application.

        Args:
            environ (dict): The WSGI environment dictionary.
            start_response (callable): The WSGI start_response callable.
        
        Returns:
            iterable: An iterable yielding the response body bytes.
        """
        path_info = environ['PATH_INFO']
        if path_info.startswith("/static"):
            return self.whitenoise(environ, start_response)
        else:
            # Calling middlewares before calling the actual wsgi application
            return self.middleware(environ, start_response)
    
    def wsgi_app(self, environ, start_response):
        """
        The WSGI application callable.
        A pure WSGI application, without Whitenoise wrapping.
        We use it to give Whitenoise while wrapping process.

        Args:
            environ (dict): The WSGI environment dictionary.
            start_response (callable): The WSGI start_response callable.
        
        Returns:
            iterable: An iterable yielding the response body bytes.
        """
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)
    
    def handle_request(self, request):
        """
        Handle the incoming HTTP request and generate an appropriate response.

        Args:
            request (Request): The incoming HTTP request.
        
        Returns:
            Response: The HTTP response object.
        """
        response = Response()
        
        handler_data, kwargs = self.find_handler(request)

        if handler_data:
            handler = handler_data.get("handler")
            allowed_methods = handler_data.get("allowed_methods")
            if inspect.isclass(handler):
                handler_method = getattr(handler(), request.method.lower(), None)
                if handler_method is None:
                    return self.method_not_allowed_response(response)
                handler_method(request, response, **kwargs)
            else:
                if request.method.lower() not in allowed_methods:
                    return self.method_not_allowed_response(response)

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
    
    def method_not_allowed_response(self, response):
        """
        Generate a "Method Not Allowed" response.
        """
        response.text = "Method Not Allowed."
        response.status_code = 405
        return response
    
    def find_handler(self, request):
        """
        Find the handler for the given request path.

        Args:
            request (Request): The incoming HTTP request.
        
        Returns:
            tuple: A tuple containing the handler data and parsed URL arguments.
        """
        for path, handler_data in self.routes.items():
            # parse("It's {}, I love it!", "It's spam, I love it!")
            result_parse = parse(path, request.path)
            if result_parse:
                # named method returns dictionary instead of Result object
                return handler_data, result_parse.named
            
        return None, None

    def default_response(self, response):
        """
        Generate a default "Not Found" response.
        """
        response.status_code = 404
        response.text = "Not found."

    def add_route(self, path, handler, allowed_methods=None):
        """
        Add a new route to the application.

        Args:
            path (str): The URL path for the route.
            handler (callable): The handler function or class for the route.
            allowed_methods (list, optional): The list of allowed HTTP methods for the route.
        """
        assert path not in self.routes, "Duplicate route. Please change the URL."

        if allowed_methods is None:
            allowed_methods = ["get", "post", "put", "patch", "delete", "options", "head", "connect", "trace"]

        self.routes[path] = {"handler": handler, "allowed_methods": allowed_methods}

    def route(self, path, allowed_methods=None):
        """
        A decorator to add a route to the application.

        Args:
            path (str): The URL path for the route.
            allowed_methods (list, optional): The list of allowed HTTP methods for the route.
        
        Returns:
            callable: The decorator function.
        """

        def wrapper(handler):
            self.add_route(path, handler, allowed_methods)
            return handler
        return wrapper

    def test_session(self):
        """
        Create a test session for the application.

        Returns:
            requests.Session: A requests session object configured to use the WSGI adapter.
        """
        session = requests.Session()
        session.mount('http://testserver', wsgiadapter.WSGIAdapter(self))
        return session

    def template(self, template_name, context={}):
        """
        Render a template with the given context.

        Args:
            template_name (str): The name of the template file.
            context (dict, optional): The context dictionary to render the template with.
        
        Returns:
            str: The rendered template as a string.
        """
        return self.template_env.get_template(template_name).render(**context)

    def add_exception_handler(self, handler):
        """
        Add a custom exception handler to the application.

        Args:
            handler (callable): The exception handler function.
        """
        self.exception_handler = handler

    # Middleware
    def add_middleware(self, middleware_cls):
        """
        Add a middleware class to the application.

        Args:
            middleware_cls (type): The middleware class to add.
        """
        self.middleware.add(middleware_cls)