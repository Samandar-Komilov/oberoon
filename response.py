from webob import Response as WebResponse
import json

class Response:
    """
    Custom Response class for a WSGI framework.

    This class helps in generating HTTP responses with different content types,
    including JSON, HTML, and plain text.
    """
    def __init__(self):
        self.json = None
        self.html = None
        self.text = None
        self.content_type = None
        self.body = b''
        self.status_code = 200
    
    def set_body_and_content_type(self):
        """
        Sets the response body and content type based on the provided data. (Filter)

        This method checks the json, html, and text attributes in order and
        sets the response body and content type accordingly.
        """
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
        """
        WSGI callable interface.

        This method allows the Response object to be called as a WSGI application,
        setting the response headers and body appropriately.

        Args:
            environ (dict): The WSGI environment dictionary.
            start_response (callable): The WSGI start_response callable.
        
        Returns:
            iterable: An iterable yielding the response body bytes.
        """
        self.set_body_and_content_type()
        response = WebResponse(
            body=self.body, content_type=self.content_type, status_code=self.status_code
        )

        return response(environ, start_response)