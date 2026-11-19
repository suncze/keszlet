"""HTTP JSON API. Run from project root: python3 -m backend.server."""
import argparse
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from .database import Inventory, AppError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def handler_for(inventory, origins):
    class Handler(BaseHTTPRequestHandler):
        server_version = "KeszletAPI/1.0"

        def send_json(self, status, payload):
            raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            origin = self.headers.get("Origin")
            if origin in origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(raw)

        def body(self):
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise AppError("application/json tartalomtípus szükséges.", 415)
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError as exc:
                raise AppError("Érvénytelen kérésméret.") from exc
            if not 0 < length <= 16384:
                raise AppError("A kérés üres vagy túl nagy.", 413)
            self.connection.settimeout(10)
            try:
                return json.loads(self.rfile.read(length))
            except (ValueError, UnicodeDecodeError) as exc:
                raise AppError("Hibás JSON-adatok.") from exc

        def do_OPTIONS(self):
            if self.headers.get("Origin") not in origins:
                return self.send_json(403, {"error": "Nem engedélyezett eredet."})
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def dispatch(self):
            try:
                if self.headers.get("Origin") and self.headers["Origin"] not in origins:
                    raise AppError("Nem engedélyezett eredet.", 403)
                url = urlsplit(self.path)
                path = url.path.rstrip("/")
                query = {k: v[-1] for k, v in parse_qs(url.query).items()}
                method = self.command
                if method == "GET" and path == "/api/health":
                    with inventory.connection() as db:
                        db.execute("SELECT 1").fetchone()
                    return self.send_json(200, {"status": "ok", "version": "1.1.0"})
                if path == "/api/products":
                    if method == "GET":
                        return self.send_json(200, {"items": inventory.products()})
                    if method == "POST":
                        return self.send_json(201, inventory.create(self.body()))
                parts = path.split("/")
                if len(parts) == 4 and parts[1:3] == ["api", "products"] and parts[3].isascii() and parts[3].isdigit():
                    if method == "GET":
                        return self.send_json(200, inventory.product(int(parts[3])))
                    if method == "PUT":
                        return self.send_json(200, inventory.update(int(parts[3]), self.body()))
                if path == "/api/movements":
                    if method == "GET":
                        return self.send_json(200, inventory.movements(query))
                    if method == "POST":
                        result = inventory.move(self.body())
                        return self.send_json(200 if result["replayed"] else 201, result)
                raise AppError("A végpont nem található.", 404)
            except AppError as exc:
                self.send_json(exc.status, {"error": str(exc), "field": exc.field})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                logging.exception("API hiba")
                self.send_json(500, {"error": "A művelet nem sikerült. Próbáld újra később."})

        do_GET = do_POST = do_PUT = dispatch
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Készletkezelő backend")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=os.environ.get("INVENTORY_DB", os.path.join(ROOT, "data", "inventory.sqlite3")))
    parser.add_argument("--frontend-port", type=int, default=8080)
    args = parser.parse_args()
    origins = {f"http://{host}:{args.frontend_port}" for host in ("localhost", "127.0.0.1")}
    origins.update(filter(None, os.environ.get("ALLOWED_ORIGINS", "").split(",")))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(Inventory(args.db), origins))
    print(f"API: http://127.0.0.1:{args.port}/api/health", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
