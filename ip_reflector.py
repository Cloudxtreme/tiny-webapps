#!/usr/bin/env python2.6


def reflector_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return environ['REMOTE_ADDR']


if __name__ == "__main__":
    from flup.server.fcgi_fork import WSGIServer
    WSGIServer(reflector_app, maxSpare=1).run()
