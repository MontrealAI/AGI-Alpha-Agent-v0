# SPDX-License-Identifier: Apache-2.0
"""Separate fixed-task output checker; no import of numerics or quality().

Independence means a separately written calculation, not independent ownership,
authentication, beneficiary acceptance, or a proof of the numerical algorithm.
The checker recomputes sparse products by explicit CSR row sums with math.fsum.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import tarfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import mmread
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parent


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def matrix_bytes(name: str) -> tuple[bytes, dict[str, Any]]:
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    rows = [row for row in manifest["matrices"] if row["name"] == name]
    if len(rows) != 1:
        raise ValueError("Checker requires one exact frozen matrix")
    row = rows[0]
    data_root = (ROOT / "data").resolve()
    path = (data_root / row.get("file", f"{name}.tar.gz")).resolve()
    if not path.is_relative_to(data_root) or path.is_symlink() or not path.is_file():
        raise ValueError("Matrix file leaves the frozen data directory")
    raw = path.read_bytes()
    if sha256(raw) != row["archive_sha256"]:
        raise ValueError("Independent checker rejected archive hash")
    if path.name.endswith(".tar.gz"):
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            member = archive.getmember(f"{name}/{name}.mtx")
            if not member.isfile() or member.size > 20_000_000:
                raise ValueError("Unexpected matrix member")
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError("Missing matrix member")
            matrix = handle.read()
    elif path.name.endswith(".gz"):
        matrix = gzip.decompress(raw)
    else:
        matrix = raw
    if sha256(matrix) != row["matrix_sha256"]:
        raise ValueError("Independent checker rejected matrix hash")
    return matrix, row


def inspect_artifact(record: Mapping[str, Any], *, matrix: str, seed: int, q: int) -> dict[str, Any]:
    started, cpu = time.perf_counter(), time.process_time()
    path = Path(record["artifact_path"])
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a retained regular numerical artifact")
    raw = path.read_bytes()
    observed_hash = sha256(raw)
    if observed_hash != record["artifact_sha256"]:
        raise ValueError("Checker examined changed artifact bytes")
    artifact = json.loads(raw)
    if artifact.get("schema") != "writer9-readiness-demo-artifact/v1":
        raise ValueError("Unsupported numerical artifact")
    if (artifact.get("matrix"), artifact.get("seed"), artifact.get("q")) != (matrix, seed, q):
        raise ValueError("Numerical task differs from fixed engineering task")
    payload, metadata = matrix_bytes(matrix)
    if artifact["matrix_sha256"] != metadata["matrix_sha256"]:
        raise ValueError("Artifact names a different frozen matrix")
    if artifact["numerics_source_sha256"] != sha256((ROOT / "numerics.py").read_bytes()):
        raise ValueError("Artifact names a different numerical source")
    a = csr_matrix(mmread(io.BytesIO(payload)), dtype=np.float64)
    a.sum_duplicates()
    a.eliminate_zeros()
    a.sort_indices()
    if a.shape != (metadata["rows"], metadata["rows"]) or a.nnz != metadata["nnz"]:
        raise ValueError("Matrix shape or nonzeros differ from manifest")
    x = np.asarray(artifact["x"], dtype=np.float64)
    if x.shape != (a.shape[0], q) or not np.isfinite(x).all():
        raise ValueError("Output shape or finite-value requirement failed")
    loaded = time.perf_counter()
    # Generate all sixteen columns before taking a prefix, exactly as preregistered.
    truth = np.random.default_rng(seed).standard_normal((a.shape[0], 16))[:, :q]
    tol = json.loads((ROOT / "protocol.json").read_text())["numerical_design"]["acceptance"]
    row_terms = [
        (a.indices[a.indptr[i]:a.indptr[i + 1]], a.data[a.indptr[i]:a.indptr[i + 1]])
        for i in range(a.shape[0])
    ]
    anorm = max(math.fsum(abs(float(v)) for v in values) for _, values in row_terms)
    tiny = np.finfo(np.float64).tiny
    columns = []
    for column in range(q):
        b = [
            math.fsum(float(v) * float(truth[int(k), column]) for k, v in zip(indices, values))
            for indices, values in row_terms
        ]
        ax = [
            math.fsum(float(v) * float(x[int(k), column]) for k, v in zip(indices, values))
            for indices, values in row_terms
        ]
        r = [right - left for right, left in zip(b, ax)]
        residual = math.sqrt(math.fsum(v * v for v in r)) / max(math.sqrt(math.fsum(v * v for v in b)), tiny)
        denominator = anorm * max(abs(float(v)) for v in x[:, column]) + max(abs(v) for v in b)
        backward = max(abs(v) for v in r) / max(denominator, tiny)
        squared_error = math.fsum(
            (float(x[i, column]) - float(truth[i, column])) ** 2 for i in range(a.shape[0])
        )
        truth_norm = math.sqrt(math.fsum(float(v) ** 2 for v in truth[:, column]))
        forward = math.sqrt(squared_error) / max(truth_norm, tiny)
        passed = (
            residual <= tol["relative_residual_l2_max"]
            and backward <= tol["normwise_backward_error_linf_max"]
            and forward <= tol["manufactured_forward_error_l2_max"]
        )
        columns.append({
            "column": column, "relative_residual_l2": residual, "backward_error_linf": backward,
            "manufactured_forward_error_l2": forward, "accepted": bool(passed),
        })
    finished = time.perf_counter()
    return {"artifact_sha256": observed_hash, "matrix_sha256": metadata["matrix_sha256"],
            "accepted": all(row["accepted"] for row in columns),
            "max_residual": repr(max(row["relative_residual_l2"] for row in columns)),
            "threshold": repr(tol["relative_residual_l2_max"]), "thresholds": tol, "columns": columns,
            "method": "Separate CSR row sums with math.fsum; truth regenerated from fixed (n,16) draw",
            "evidence_scope": "Separate implementation under one operator; no independent institution or beneficiary",
            "timing": {
                "artifact_matrix_load_seconds": loaded - started,
                "regeneration_and_check_seconds": finished - loaded,
                "total_seconds": finished - started, "cpu_seconds": time.process_time() - cpu,
            }}
