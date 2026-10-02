# SPDX-License-Identifier: Apache-2.0
"""Start the minimal research API with configuration supplied by Docker's env file."""

from __future__ import annotations

import os
from io import StringIO
import sys
import urllib.request

from dotenv import dotenv_values


def configure(template: str = "/app/.env.sample") -> None:
    """Normalize documented dotenv settings and validate before importing services."""
    # Docker's --env-file preserves dotenv quotes/inline comments literally.
    # Normalize only project configuration, leaving Docker's PATH and other
    # execution environment untouched. Do not expand ${...} references.
    names = dotenv_values(template, interpolate=False)
    for key in names:
        if key in os.environ:
            value = dotenv_values(stream=StringIO(f"{key}={os.environ[key]}"), interpolate=False).get(key)
            if value is not None:
                os.environ[key] = value
    for key in ("API_TOKEN", "NEO4J_PASSWORD"):
        value = os.environ.get(key, "").strip()
        if not value or value.startswith("REPLACE_ME"):
            raise SystemExit(f"Configure {key} in the root .env, then rerun ./run_quickstart.sh")
    # The launcher publishes this fixed container port; caller configuration
    # cannot silently make the advertised URL unreachable.
    os.environ["PORT"] = "8000"
    os.environ["AF_MEMORY_DIR"] = "/data/memory"


def main() -> None:
    """Start or probe the API without printing credentials."""
    configure()
    if sys.argv[1:] == ["--healthcheck"]:
        request = urllib.request.Request(
            "http://127.0.0.1:8000/healthz", headers={"Authorization": "Bearer " + os.environ["API_TOKEN"]}
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            if response.status != 200:
                raise SystemExit("API is not healthy")
        return
    from alpha_factory_v1.run import run

    sys.argv = ["alpha-factory"]
    run()


if __name__ == "__main__":
    main()
