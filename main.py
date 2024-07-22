def app(environ, start_response):
    status = "200 OK"
    headers = [("Content-type", "text/plain")]
    start_response(status, headers)

    return [b'Hello World']


# gunicorn main:app - running wsgi server using gunicorn