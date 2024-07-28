

from typing import Any

from webob import Request


class Middleware:
    def __init__(self, app) -> None:
        self.app = app

    def add(self, middleware_cls):
        """Adding a new middleware, means wrapping app class with our middleware class"""
        self.app = middleware_cls(self.app)
    
    def process_request(self, request):
        pass

    def process_response(self, request):
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
        request = Request(environ)
        response = self.app.handle_request(request)
        return response(environ, start_response)