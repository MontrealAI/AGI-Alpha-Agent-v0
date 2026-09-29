# SPDX-License-Identifier: Apache-2.0
"""Small loopback research service with bounded requests and same-origin authorization."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import secrets
from typing import Any

from .delivery import render, strict_json
from .paper import Config, MAX_BYTES, run


def create_server(port: int = 7864) -> HTTPServer:
    """Bind only 127.0.0.1; serve explicit routes, never filesystem paths."""
    token = secrets.token_urlsafe(32)
    page = render({"mode": "local", "token": token}).encode()

    class Handler(BaseHTTPRequestHandler):
        server: HTTPServer
        server_version = "FinanceAlpha/1"

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, format: str, *args: Any) -> None:
            pass  # Do not log imported data or client-controlled paths.

        def reply(self, code: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def allowed(self) -> bool:
            address = f"127.0.0.1:{self.server.server_port}"
            host = self.headers.get("Host")
            return host == address and self.headers.get("Origin") in (None, f"http://{address}")

        def do_GET(self) -> None:
            if not self.allowed():
                self.reply(403, b'{"error":"Use the printed 127.0.0.1 address"}')
            elif self.path == "/":
                self.reply(200, page, "text/html; charset=utf-8")
            elif self.path == "/api/health":
                self.reply(200, b'{"status":"ok","execution":"paper_only"}')
            else:
                self.reply(404, b'{"error":"Not found"}')

        def do_POST(self) -> None:
            supplied = self.headers.get("X-Finance-Token", "")
            if not self.allowed() or not supplied.isascii() or not secrets.compare_digest(supplied, token):
                self.reply(403, b'{"error":"Reload the local app before running"}')
                return
            if self.path != "/api/run":
                self.reply(404, b'{"error":"Not found"}')
                return
            try:
                if self.headers.get("Content-Type") != "application/json" or self.headers.get("Transfer-Encoding"):
                    raise ValueError("Use a bounded application/json request")
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= MAX_BYTES + 10000:
                    raise ValueError("Request must be between 1 byte and 2 MB plus configuration")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete request")
                request = strict_json(raw.decode("utf-8"))
                if not isinstance(request, dict) or set(request) - {"case", "config", "csv"}:
                    raise ValueError("Expected case, config and optional csv")
                config = Config(**request.get("config", {}))
                report = run(request.get("csv"), config, case=request.get("case", "trend"))
                self.reply(200, json.dumps(report, allow_nan=False).encode())
            except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as exc:
                self.reply(400, json.dumps({"error": str(exc)}).encode())
            except TimeoutError:
                self.reply(408, b'{"error":"Request timed out"}')

    # Requests execute sequentially. Work is capped by CSV/Config bounds.
    return HTTPServer(("127.0.0.1", port), Handler)


def serve(port: int = 7864) -> None:
    """Run until Ctrl+C; never open a public tunnel or exchange connection."""
    with create_server(port) as server:
        print(
            f"Finance Alpha · paper research only\nOpen http://127.0.0.1:{server.server_port}\nStop: Ctrl+C", flush=True
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nFinance Alpha stopped.")
