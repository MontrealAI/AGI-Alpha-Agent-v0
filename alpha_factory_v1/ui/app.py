# SPDX-License-Identifier: Apache-2.0

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


if __name__ == "__main__":
    app.run(port=3000, host="0.0.0.0")
