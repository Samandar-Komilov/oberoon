from webob import Request, Response

from typing import Any


class Oberoon:
    def __call__(self, environ, start_response, *args, **kwargs):
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)
    
    def handle_request(self, request):
        user_agent = request.environ.get("HTTP_USER_AGENT", "User Agent not found")
        response = Response()
        response.text = "Hello World!"
        return response