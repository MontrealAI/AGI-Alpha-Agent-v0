# SPDX-License-Identifier: Apache-2.0
"""Simple NSGA-II evolution worker.

This service exposes a ``/mutate`` endpoint that accepts an uploaded tarball
or a repository URL. It runs a single NSGA-II step on a dummy fitness function
and returns the resulting child genome. The goal is to demonstrate how a
self-improving agent could be evolved inside a container.
"""

from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import List, Tuple

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from contextlib import asynccontextmanager
from pydantic import BaseModel

from alpha_factory_v1.core.simulation import mats


def _safe_extract(tf: tarfile.TarFile, target_dir: Path) -> None:
    """Safely extract tar members inside ``target_dir``."""
    base = target_dir.resolve()
    for member in tf.getmembers():
        if member.issym() or member.islnk():
            raise HTTPException(status_code=400, detail="Unsafe link in archive")

        name = os.path.normpath(member.name)
        if os.path.isabs(name) or ".." in Path(name).parts:
            raise HTTPException(status_code=400, detail="Unsafe path in archive")

        dest = (base / name).resolve()
        if not str(dest).startswith(str(base)):
            raise HTTPException(status_code=400, detail="Unsafe path in archive")

        tf.extract(member, base)


GPU_TYPE = os.getenv("GPU_TYPE", "cpu")
MAX_GENERATIONS = int(os.getenv("MAX_GENERATIONS", "10"))
STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/tmp/evolution"))

app = FastAPI(title="Evolution Worker")


class MutationResponse(BaseModel):  # type: ignore[misc]
    child: List[float]


@asynccontextmanager
async def lifespan(_: FastAPI):
    STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    yield


app.router.lifespan_context = lifespan


@app.post("/mutate", response_model=MutationResponse)  # type: ignore[misc]
async def mutate(
    tar: UploadFile | None = File(None),
    repo_url: str | None = Form(None),
) -> MutationResponse:
    """Return a mutated child from one evolution step."""

    if tar is None and not repo_url:
        raise HTTPException(status_code=400, detail="tar or repo_url required")

    tmp = tempfile.mkdtemp(dir=STORAGE_PATH)
    tmp_path = Path(tmp)
    try:
        if tar is not None:
            with tarfile.open(fileobj=tar.file) as tf:
                _safe_extract(tf, tmp_path)
        if repo_url:
            (tmp_path / "repo.txt").write_text(repo_url)

        pop = mats.run_evolution(
            lambda g: (g[0] ** 2, g[1] ** 2),
            2,
            population_size=4,
            generations=1,
            seed=42,
        )
        child = pop[0].genome
        return MutationResponse(child=child)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


@app.get("/healthz")  # type: ignore[misc]
async def healthz() -> str:
    """Liveness probe."""

    return "ok"
