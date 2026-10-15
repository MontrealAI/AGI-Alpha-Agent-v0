# SPDX-License-Identifier: Apache-2.0
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest

from alpha_factory_v1.demos.cross_industry_alpha_factory import queue_cross_alpha


class _Handler(BaseHTTPRequestHandler):
    received_path = None
    received_body = None

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        type(self).received_body = self.rfile.read(length)
        type(self).received_path = self.path
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")


def _start_server() -> tuple[HTTPServer, threading.Thread]:
    server = HTTPServer(("localhost", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class QueueCrossAlphaTest(unittest.TestCase):
    def tearDown(self) -> None:
        if hasattr(self, "server"):
            self.server.shutdown()
            self.thread.join()
            self.server.server_close()

    def test_queue_opportunities(self) -> None:
        self.server, self.thread = _start_server()
        host, port = self.server.server_address
        jobs = queue_cross_alpha.queue_opportunities(1, host=str(host), port=port, dry_run=False, sample=True)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(_Handler.received_path, "/agent/finance/trigger")
        assert _Handler.received_body is not None
        body = json.loads(_Handler.received_body.decode())
        self.assertEqual(body["agent"], "finance")


if __name__ == "__main__":
    unittest.main()
