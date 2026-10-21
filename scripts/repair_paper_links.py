# SPDX-License-Identifier: Apache-2.0
"""One-shot additive PDF repair of the verified public 1.36.0 Pages artifact.

This does not build, qualify or publish software. The deployed software identity,
all 991 baseline paths and every baseline byte are retained. Only five original
PDF paths and an explicitly separate repair receipt may be added.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts import release_packs

REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
SITE = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
API = f"https://api.github.com/repos/{REPOSITORY}/"
RELEASE = f"https://github.com/{REPOSITORY}/releases/download/v1.36.0/"
BASELINE_COMMIT = "a6d20a93c7c5b7430bf42d2367701b350513e90d"
PAPER_COMMIT = "6ab02a24b1f59306fb25e0e8da73b6210a2fe363"
INDEX_SHA256 = "31fb7ee47f7842cc19b70c3376482bd5dbf69beddcd498518c2e0f675134655f"
INDEX_BYTES = 466282
BASELINE_DEPLOYMENT = 7212863284
BASELINE_RUN = 39484204330
BASELINE_JOB = 118928852841
BASELINE_ARTIFACT = 12304509777
BASELINE_ARTIFACT_SHA256 = "bdada0066e1d69530d45e40d291eb3020b8ef37b18ec55254ece12d04b8c7867"
RECEIPT = "paper-link-repair-20261021.json"
PDFS = {
    "Transformational_Intelligence.pdf": (305040, "d7170e8217e3bf6aa1b84868c1c76c5994c6995c5297ed092d7e72a6430c664f"),
    "Out_Learn.pdf": (337128, "01a8ea668f4c75cd0b5fafe3c5720e445bab7986abf27baee5bbba7d5e77febb"),
    "Out_Think.pdf": (175327, "22280da9d3c74b995b0770b3b1a633924a0849d4f72fad51facd8f78c0336029"),
    "Out_Design.pdf": (165614, "65849e2f872b2dcdbc4a57baabb63e6a2644208c68dcc7c23ec0ee11ac1fe5dd"),
    "Out_Strategise.pdf": (180818, "8a848150f14c578106633324edb54bc59713a579c1318d9ea872d3d5b3ec7e77"),
    "Out_Execute.pdf": (180239, "85c6834e2dd496748f72a9099d3a70cb13047b49e09e3ed84ce911e1f1c530f3"),
    "Out_Evolve.pdf": (399909, "5979bcaf704934ba42e4722389cbb1a9ef0cbc889e1b286428615a82a31e99bc"),
}
ADDITIONS = tuple(name for name in PDFS if name not in {"Transformational_Intelligence.pdf", "Out_Evolve.pdf"})
CRITICAL_PATHS = (
    "release.json",
    "index.html",
    "service-worker.js",
    "assets/service-worker.js",
    "alpha_agi_insight_v1/service-worker.js",
    "alpha_agi_insight_v1/sw.js",
    "alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_bytes(data: bytes, size: int, digest: str) -> None:
    if len(data) != size or sha256(data) != digest:
        raise ValueError("Exact byte identity mismatch")


def read_url(url: str, *, limit: int = 2_000_000) -> tuple[bytes, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "AGIAlpha-Public-PDF-Repair", "Cache-Control": "no-cache"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise ValueError("Expected HTTP 200")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Response exceeds bounded size")
        return data, response.headers


def api(path: str) -> Any:
    return json.loads(read_url(API + path, limit=5_000_000)[0])


def live(path: str) -> tuple[bytes, Any]:
    return read_url(SITE + urllib.parse.quote(path, safe="/") + f"?pdf-repair={time.time_ns()}")


def absent(path: str) -> None:
    try:
        live(path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return
        raise
    raise ValueError(f"Existing overlay requires separate review: {path}")


def load_index(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    require_bytes(data, INDEX_BYTES, INDEX_SHA256)
    index: dict[str, Any] = json.loads(data)
    if (
        index["schema"] != release_packs.SCHEMA
        or index["commit"] != BASELINE_COMMIT
        or index["version"] != "1.36.0"
        or len(index["files"]) != 991
        or len(index["packs"]) != 5
    ):
        raise ValueError("Unexpected published baseline")
    return index


def download_exact(url: str, path: Path, size: int, digest: str) -> None:
    if path.exists():
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != size
            or release_packs.digest(path) != digest
        ):
            raise ValueError("Existing download differs from immutable public asset")
        return
    partial = path.with_suffix(path.suffix + ".partial")
    if partial.exists():
        raise ValueError("Interrupted download retained; use a fresh preparation directory")
    request = urllib.request.Request(url, headers={"User-Agent": "AGIAlpha-Public-PDF-Repair"})
    count = 0
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("xb") as output:
        if response.status != 200:
            raise ValueError("Asset download was not HTTP 200")
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > size:
                raise ValueError("Asset exceeded pinned size")
            output.write(chunk)
    if count != size or release_packs.digest(partial) != digest:
        raise ValueError("Public asset digest mismatch; partial retained")
    partial.rename(path)


def repair_receipt(source: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Repair source must be an exact commit")
    return {
        "schema": "agialpha.paper-link-repair.v1",
        "repair_source_commit": source,
        "scope": "Five original public PDFs only; no software qualification or release",
        "software": {"version": "1.36.0", "commit": BASELINE_COMMIT},
        "baseline": {
            "site_packs_sha256": INDEX_SHA256,
            "deployment_id": BASELINE_DEPLOYMENT,
            "run_id": BASELINE_RUN,
            "artifact_id": BASELINE_ARTIFACT,
            "artifact_sha256": BASELINE_ARTIFACT_SHA256,
            "preserved_files": 991,
        },
        "paper_source_commit": PAPER_COMMIT,
        "added": [{"path": name, "bytes": PDFS[name][0], "sha256": PDFS[name][1]} for name in ADDITIONS],
    }


def receipt_bytes(source: str) -> bytes:
    return (json.dumps(repair_receipt(source), indent=2, sort_keys=True) + "\n").encode()


def verify_inventory(site: Path, index: dict[str, Any], source: str, *, repaired: bool) -> None:
    expected = {entry["path"]: (entry["bytes"], entry["sha256"]) for entry in index["files"]}
    if len(expected) != len(index["files"]) or any(name in expected for name in (*ADDITIONS, RECEIPT)):
        raise ValueError("Baseline collision or duplicate path")
    if repaired:
        expected.update({name: PDFS[name] for name in ADDITIONS})
        receipt = receipt_bytes(source)
        expected[RECEIPT] = (len(receipt), sha256(receipt))
    actual = set()
    for path in site.rglob("*"):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise ValueError("Non-ordinary site entry")
        if path.is_file():
            name = path.relative_to(site).as_posix()
            actual.add(name)
            if name not in expected or (path.stat().st_size, release_packs.digest(path)) != expected[name]:
                raise ValueError(f"Unexpected or modified site bytes: {name}")
    if actual != set(expected):
        raise ValueError("Missing or extra site path")


def overlay(site: Path, docs: Path, index: dict[str, Any], source: str) -> None:
    verify_inventory(site, index, source, repaired=False)
    # Validate all originals before writing anything; an interrupted result is
    # not a deployable result and cannot pass the complete inventory check.
    for name, (size, digest) in PDFS.items():
        original = docs / name
        if original.is_symlink():
            raise ValueError("Original PDF must not be a symlink")
        data = original.read_bytes()
        require_bytes(data, size, digest)
        if not data.startswith(b"%PDF-"):
            raise ValueError("Original is not a PDF")
        if name not in ADDITIONS:
            require_bytes((site / name).read_bytes(), size, digest)
    for name in ADDITIONS:
        with (site / name).open("xb") as output, (docs / name).open("rb") as original_stream:
            shutil.copyfileobj(original_stream, output)
    with (site / RECEIPT).open("xb") as output:
        output.write(receipt_bytes(source))
    verify_inventory(site, index, source, repaired=True)


def prepare(work: Path, docs: Path, source: str) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    index_path = work / "site-packs.json"
    download_exact(RELEASE + "site-packs.json", index_path, INDEX_BYTES, INDEX_SHA256)
    index = load_index(index_path)
    for pack in index["packs"]:
        name = release_packs.safe_name(pack["name"])
        if "/" in name:
            raise ValueError("Unexpected pack name")
        download_exact(RELEASE + name, work / name, pack["bytes"], pack["sha256"])
    site = work / "site"
    release_packs.restore(index_path, site)
    overlay(site, docs, index, source)
    return {
        "baseline_files": 991,
        "added_pdfs": list(ADDITIONS),
        "final_files": 997,
        "receipt_sha256": sha256(receipt_bytes(source)),
        "repair_source_commit": source,
    }


def require_context() -> str:
    source = os.environ.get("GITHUB_SHA", "")
    if (
        os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or not re.fullmatch(r"[0-9a-f]{40}", source)
    ):
        raise ValueError("Repair publication requires this repository's exact main")
    ref = api("git/ref/heads/main")
    if ref.get("ref") != "refs/heads/main" or ref.get("object", {}).get("sha") != source:
        raise ValueError("Main advanced; refusing superseded repair")
    return source


def require_baseline_deployment(source: str) -> None:
    # Environment entry for this pending repair can already exist. No other
    # newer deployment, even one with the same version string, is accepted.
    deployments = api("deployments?environment=github-pages&per_page=100")
    found = False
    for deployment in deployments:
        statuses = api(f"deployments/{deployment['id']}/statuses?per_page=100")
        if not statuses:
            raise ValueError("Deployment has no verifiable state")
        latest = statuses[0]
        if deployment["id"] == BASELINE_DEPLOYMENT:
            expected_log = f"https://github.com/{REPOSITORY}/actions/runs/{BASELINE_RUN}/job/{BASELINE_JOB}"
            if (
                deployment["sha"] != BASELINE_COMMIT
                or latest["state"] != "success"
                or latest.get("log_url") != expected_log
                or latest.get("environment_url") != SITE
            ):
                raise ValueError("Pinned deployment is no longer the successful live baseline")
            found = True
            break
        if deployment["sha"] != source or latest["state"] not in {"queued", "pending", "waiting", "in_progress"}:
            raise ValueError("A later deployment exists; refusing baseline rollback")
        log = latest.get("log_url", "")
        run = os.environ.get("GITHUB_RUN_ID", "")
        if not run.isdigit() or not log.startswith(f"https://github.com/{REPOSITORY}/actions/runs/{run}/"):
            raise ValueError("Pending deployment is not this repair run")
    if not found:
        raise ValueError("Pinned deployment absent from recent history")


def verify_live_baseline(index: dict[str, Any]) -> None:
    entries = {entry["path"]: entry for entry in index["files"]}
    for name in CRITICAL_PATHS:
        entry = entries[name]
        require_bytes(live(name)[0], entry["bytes"], entry["sha256"])
    absent("paper-publication.json")


def guard(index: dict[str, Any]) -> dict[str, Any]:
    source = require_context()
    require_baseline_deployment(source)
    verify_live_baseline(index)
    absent(RECEIPT)
    # The two original PDFs are part of the pinned baseline; missing additions
    # must still be absent, not untracked data that could be replaced.
    for name, (size, digest) in PDFS.items():
        if name in ADDITIONS:
            absent(name)
        else:
            require_bytes(live(name)[0], size, digest)
    # Check again after the HTTP probes, immediately before deploy-pages.
    require_context()
    require_baseline_deployment(source)
    return {"baseline_deployment": BASELINE_DEPLOYMENT, "source": source, "guard": "passed"}


def verify_live(index: dict[str, Any], source: str) -> dict[str, Any]:
    verify_live_baseline(index)
    require_bytes(live(RECEIPT)[0], len(receipt_bytes(source)), sha256(receipt_bytes(source)))
    results = []
    for name, (size, digest) in PDFS.items():
        data, headers = live(name)
        require_bytes(data, size, digest)
        if (
            headers.get_content_type() != "application/pdf"
            or not data.startswith(b"%PDF-")
            or "attachment" in headers.get("Content-Disposition", "").lower()
        ):
            raise ValueError(f"Not an inline PDF response: {name}")
        results.append({"path": name, "sha256": digest, "status": 200, "content_type": "application/pdf"})
    return {"software_identity_unchanged": True, "papers": results, "repair_source_commit": source}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "guard", "verify-live"))
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        result = prepare(args.work, args.docs, args.source)
    else:
        index_path = args.work / "site-packs.json"
        args.work.mkdir(parents=True, exist_ok=True)
        download_exact(RELEASE + "site-packs.json", index_path, INDEX_BYTES, INDEX_SHA256)
        index = load_index(index_path)
        if args.mode == "guard":
            if require_context() != args.source:
                raise ValueError("Guard source differs from prepared source")
            result = guard(index)
        else:
            result = verify_live(index, args.source)
    report = args.work / f"{args.mode}-report.json"
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(report.read_text())


if __name__ == "__main__":
    main()
