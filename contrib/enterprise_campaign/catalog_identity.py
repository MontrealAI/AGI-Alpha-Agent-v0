# SPDX-License-Identifier: Apache-2.0
"""Exact source closure for the separately retained catalogue producer."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import catalog_product

UPSTREAM_GIT_BLOB = "9f22a4448fa7bbd949b54c4c0d9b61936f49d549"


def assert_upstream_identity() -> None:
    """Refuse dependency drift; a source hash is not a claim of correctness."""
    data = Path(catalog_product.__file__).read_bytes()
    identity = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if identity != UPSTREAM_GIT_BLOB:
        raise ValueError("Native dependency differs from tested PR #5011; requalification required")
