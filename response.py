from webob import Response as WebResponse
import json

class Response:
    def __init__(self):
        self.json = None
        self.html = None
        self.text = None
        self.content_type = None
        self.body = b''
        self.status_code = 200
    
    def set_body_and_content_type(self):
        if self.json is not None:
            self.body = json.dumps(self.json).encode()
            self.content_type = "application/json"

        if self.html is not None:
            self.body = self.html.encode()
            self.content_type = "text/html"
        
        if self.text is not None:
            self.body = self.text
            self.content_type = "text/plain"
    
    def __call__(self, environ, start_response):
        # We are including filter that what is the response type
        self.set_body_and_content_type()
        response = WebResponse(
            body=self.body, content_type=self.content_type, status_code=self.status_code
        )

        return response(environ, start_response)