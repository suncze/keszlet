"""Separate static frontend server with runtime API configuration."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class FrontendHandler(SimpleHTTPRequestHandler):
    api_port = 8000

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src http://localhost:* http://127.0.0.1:*; frame-ancestors 'none'; base-uri 'self'; form-action 'none'")
        super().end_headers()

    def do_GET(self):
        if urlsplit(self.path).path == "/config.js":
            raw = f'window.APP_CONFIG = {{apiBase: "http://" + window.location.hostname + ":" + {json.dumps(str(self.api_port))}}};'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        return super().do_GET()

    def list_directory(self, path):
        self.send_error(404)


def main():
    parser = argparse.ArgumentParser(description="Készletkezelő frontend")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--api-port", type=int, default=8000)
    args = parser.parse_args()
    FrontendHandler.api_port = args.api_port
    handler = partial(FrontendHandler, directory=str(Path(__file__).resolve().parent / "frontend"))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Felület: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
