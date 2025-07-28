# SPDX-License-Identifier: Apache-2.0

import asyncio
import importlib
import os
from pathlib import Path
import hashlib

import pytest

pytest.importorskip("fastapi")


_DEF_CFG = {
    "horizon": 1,
    "pop_size": 2,
    "generations": 1,
    "seed": 42,
}


def _dir_checksum(path: Path) -> str:
    hasher = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_file():
            hasher.update(file.relative_to(path).as_posix().encode())
            hasher.update(file.read_bytes())
    return hasher.hexdigest()


def _hamming_dist(a: bytes, b: bytes) -> int:
    diff = 0
    for x, y in zip(a, b):
        diff += (x ^ y).bit_count()
    diff += 8 * abs(len(a) - len(b))
    return diff


@pytest.mark.parametrize("cfg", [_DEF_CFG])
def test_results_checksum(tmp_path: Path, cfg: dict[str, int]) -> None:
    os.environ["SIM_RESULTS_DIR"] = str(tmp_path)
    os.environ.setdefault("API_TOKEN", "test-token")
    from alpha_factory_v1.core.interface import api_server

    api = importlib.reload(api_server)
    req = api.SimRequest(**cfg)
    asyncio.run(api._background_run("chk", req))

    checksum = _dir_checksum(tmp_path)
    golden = Path(__file__).with_name("golden_checksum.txt").read_text().strip()

    diff_bits = _hamming_dist(bytes.fromhex(checksum), bytes.fromhex(golden))
    max_bits = max(len(checksum), len(golden)) * 4
    diff_ratio = diff_bits / max_bits
    assert diff_ratio <= 0.001, f"Checksum differs by {diff_ratio*100:.3f}% (threshold 0.1%)"
