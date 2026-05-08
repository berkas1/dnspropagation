import http.server
import socketserver
import threading
from contextlib import contextmanager

import pytest


@contextmanager
def serve_yaml(content: bytes):
    """Start a local HTTP server that serves `content` for any GET request."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/yaml")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            yield f"http://127.0.0.1:{port}/list.yaml"
        finally:
            server.shutdown()
