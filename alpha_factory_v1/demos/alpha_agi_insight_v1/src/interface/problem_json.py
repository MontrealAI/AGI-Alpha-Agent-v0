# SPDX-License-Identifier: Apache-2.0
"""Helpers for RFC 7807 problem responses."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

__all__ = ["problem_response"]


def problem_response(exc: HTTPException) -> JSONResponse:
    """Return an RFC 7807 compliant response for ``exc``."""

    try:
        title = HTTPStatus(exc.status_code).phrase
    except Exception:  # pragma: no cover - unknown status code
        title = str(exc.status_code)

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail) if exc.detail else ""

    body: dict[str, Any] = {"type": "about:blank", "title": title, "status": exc.status_code}
    if detail:
        body["detail"] = detail

    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )
