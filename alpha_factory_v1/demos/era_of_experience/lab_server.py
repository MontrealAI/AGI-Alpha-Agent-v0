# SPDX-License-Identifier: Apache-2.0
"""Loopback-only static lab; no execution, upload, credential or filesystem APIs."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

WEB = Path(__file__).with_name("web")
TYPES = {
    ".html": "text/html",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    """Serve only the generated, packaged allowlist; never list a directory."""

    def do_GET(self) -> None:
        self.respond(False)

    def do_HEAD(self) -> None:
        self.respond(True)

    def respond(self, head: bool) -> None:
        port = self.server.server_port  # type: ignore[attr-defined]
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self.send_error(403, "Use the printed loopback address")
            return
        path = urlsplit(self.path).path
        if path == "/__live":
            data, mime = b"OK", "text/plain"
        else:
            if path in ("/", "/era_of_experience/"):
                path = "/era_of_experience/index.html"
            allowed = {
                "/" + file.relative_to(WEB).as_posix(): file
                for file in WEB.rglob("*")
                if file.is_file() and not file.is_symlink()
            }
            file = allowed.get(path)
            if file is None or file.suffix not in TYPES:
                self.send_error(404, "Unknown lab resource")
                return
            data, mime = file.read_bytes(), TYPES[file.suffix]
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def serve(port: int = 7860) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("Port must be from 1 through 65535")
    if not (WEB / "era_of_experience/index.html").is_file():
        raise ValueError("Packaged browser assets are missing; reinstall the complete distribution")
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        server.daemon_threads = True
        print(f"Experience Lab → http://127.0.0.1:{port}/era_of_experience/", flush=True)
        print("Synthetic experiments run in your browser. Press Ctrl+C to stop.", flush=True)
        server.serve_forever()
