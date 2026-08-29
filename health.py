import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import PORT

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Pharma Pro bot is running".encode("utf-8"))

    def log_message(self, format, *args):
        return


def run_health_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    logger.info("Health server started on port %s", PORT)
    server.serve_forever()
