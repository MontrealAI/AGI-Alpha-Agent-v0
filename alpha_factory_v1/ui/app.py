# SPDX-License-Identifier: Apache-2.0

import ipaddress
import os
import re
from typing import Any, Callable, TypeVar, cast

from flask import Flask, jsonify, render_template, request, Response

from alpha_factory_v1.backend.memory import Memory

app = Flask(__name__, template_folder="templates", static_folder="static")
mem = Memory()

Handler = TypeVar("Handler", bound=Callable[..., Response])


def route(rule: str, **options: Any) -> Callable[[Handler], Handler]:
    """Typed wrapper around :meth:`Flask.route`."""
    return cast(Callable[[Handler], Handler], app.route(rule, **options))


@route("/")
def index() -> str:
    return cast(str, render_template("index.html"))


@route("/api/logs")
def logs() -> Response:
    limit = int(request.args.get("limit", 100))
    return jsonify(mem.query(limit))


def _bind_host() -> str:
    """Keep log access on loopback unless the operator explicitly configures a host."""
    host = os.getenv("ALPHA_UI_HOST", "127.0.0.1")
    if not host or "%" in host or any(char.isspace() for char in host):
        raise ValueError("ALPHA_UI_HOST must be an IP address or hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if len(host) > 253 or any(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) is None for label in host.split(".")
        ):
            raise ValueError("ALPHA_UI_HOST must be an IP address or hostname") from None
    return host


def main() -> None:
    """Run the existing UI using a safe default bind address."""
    app.run(port=3000, host=_bind_host())


if __name__ == "__main__":
    main()
