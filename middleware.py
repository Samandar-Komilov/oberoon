

from typing import Any

from webob import Request


class Middleware:
    """
    Middleware base class for a WSGI application.

    This class serves as a template for creating middleware components that can process requests
    and responses in a WSGI application. Middleware components can be used for tasks such as
    logging, authentication, request modification, response modification, etc.

    Attributes:
        app (Any): The WSGI application or the next middleware in the chain.
    """
    def __init__(self, app) -> None:
        self.app = app

    def add(self, middleware_cls):
        """
        Add a new middleware by wrapping the current app with the provided middleware class.

        Args:
            middleware_cls (Any): The middleware class to wrap around the current app.
        """
        self.app = middleware_cls(self.app)
    
    def process_request(self, request):
        """
        Process the incoming request.

        This method is intended to be overridden in subclasses to add additional functionality
        before the request is handled by the main application. For example, it could be used for
        logging, authentication, modifying request headers, etc.

        Args:
            request (Request): The incoming HTTP request.
        """
        pass

    def process_response(self, request):
        """
        Process the outgoing response.

        This method is intended to be overridden in subclasses to add additional functionality
        after the main application has processed the request and generated a response. For example,
        it could be used for modifying response headers, logging response data, etc.

        Args:
            request (Request): The incoming HTTP request.
            response (Any): The outgoing HTTP response.
        """
        pass

    def handle_request(self, request):
        """
        Handle the middleware functionality for the incoming request and outgoing response.

        This function manages the middleware process by invoking the following steps:
        1. `process_request(request)`: This method is intended to be overridden in the middleware
           class to add additional functionality before the request is handled by the main application.
           For example, it could be used for logging, authentication, modifying request headers, etc.
        
        2. `self.app.handle_request(request)`: The main application or the next middleware in the
           chain processes the request and generates a response.
        
        3. `process_response(request, response)`: This method is intended to be overridden in the
           middleware class to add additional functionality after the main application has processed
           the request and generated a response. For example, it could be used for modifying response
           headers, logging response data, etc.
        """
        self.process_request(request)
        response = self.app.handle_request(request)
        self.process_response(request, response)

        return response
    
    def __call__(self, environ, start_response):
        """
        WSGI callable interface.

        This method allows the Middleware object to be called as a WSGI application,
        processing the request and generating a response.

        Args:
            environ (dict): The WSGI environment dictionary.
            start_response (callable): The WSGI start_response callable.
        
        Returns:
            Any: An iterable yielding the response body bytes.
        """
        request = Request(environ)
        response = self.app.handle_request(request)
        return response(environ, start_response)