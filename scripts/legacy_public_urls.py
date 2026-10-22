# SPDX-License-Identifier: Apache-2.0
"""Preserve historical public URLs without freezing evolving HTML or following redirects.

The manifest is a floor, not a replacement site. This checker never copies files,
rewrites pages, launches a browser, or downloads model bodies. Public observations
are evidence, not signatures; their exact source, inventory and scope are rechecked
when admitted by packaging/finalization.

Local acceptance hashes every candidate file. Public GET observations verify exact
HTML, PDF and historical-receipt bytes; HEAD observations for other assets prove
only direct availability, media type and size, not public byte identity. This is
not a browser-execution check and does not detect JavaScript-driven navigation.
"""

from __future__ import annotations

# Exact builtin schema types reject numeric coercion and subclasses (E721 sites below).

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
import tomllib
from typing import Any
from urllib.parse import quote
import urllib.error
import urllib.request

from scripts import release_packs

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "docs/agent/legacy-public-urls-20261021.json"
MANIFEST_SHA256 = "307197d0b68e511bca6311b6b86aeb73feb485a3ec9b55366886145a26731cda"
ORIGIN = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
SCHEMA = "agialpha.legacy-public-urls.acceptance.v1"
MAX_JSON = 64 * 1024 * 1024
MAX_BODY = 32 * 1024 * 1024


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _ordinary(root: Path, name: str) -> Path:
    release_packs.safe_name(name)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Not an ordinary directory: {root}")
    current = root
    for part in name.split("/"):
        current /= part
        if current.is_symlink():
            raise ValueError(f"Symbolic link is not an original path: {name}")
    if not current.is_file():
        raise ValueError(f"Missing original path: {name}")
    return current


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON:
        raise ValueError("JSON evidence must be an ordinary bounded file")
    result = json.loads(path.read_bytes(), object_pairs_hook=release_packs.unique_object)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def _manifest(root: Path) -> dict[str, Any]:
    path = _ordinary(root, MANIFEST)
    if release_packs.digest(path) != MANIFEST_SHA256:
        raise ValueError("Pinned historical manifest changed")
    return _json(path)


def _record(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "sha256": release_packs.digest(path)}


def _sources(root: Path, manifest: dict[str, Any]) -> None:
    for name, row in manifest["source_originals"].items():
        if _record(_ordinary(root, name)) != {key: row[key] for key in ("bytes", "sha256")}:
            raise ValueError(f"Original paper source changed: {name}")


def _inventory(site: Path) -> dict[str, dict[str, Any]]:
    if site.is_symlink() or not site.is_dir():
        raise ValueError("Site must be an ordinary directory")
    result = {}
    folded = set()
    for path in sorted(site.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"Site contains a symbolic link or special entry: {path}")
        if path.is_file():
            name = release_packs.safe_name(path.relative_to(site).as_posix())
            if name.casefold() in folded:
                raise ValueError(f"Case-ambiguous site path: {name}")
            folded.add(name.casefold())
            result[name] = _record(path)
    return result


def _pack(path: Path, manifest: dict[str, Any], commit: str, version: str) -> dict[str, dict[str, Any]]:
    data = _json(path)
    if (
        not re.fullmatch(r"[0-9a-f]{40}", commit)
        or not re.fullmatch(r"\d+\.\d+\.\d+", version)
        or data.get("schema") != release_packs.SCHEMA
        or data.get("commit") != commit
        or data.get("version") != version
    ):
        raise ValueError("Exact candidate pack commit and version are required")
    rows = data.get("files")
    if not isinstance(rows, list) or not 1 <= len(rows) <= release_packs.MAX_ENTRIES:
        raise ValueError("Invalid candidate inventory")
    files: dict[str, dict[str, Any]] = {}
    folded = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid candidate file record")
        name = release_packs.safe_name(row.get("path"))
        size, digest = row.get("bytes"), row.get("sha256")
        if (
            name.casefold() in folded
            or type(size) is not int  # noqa: E721
            or not 0 <= size <= release_packs.MAX_TOTAL_BYTES
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ValueError(f"Invalid or duplicate candidate path: {name}")
        folded.add(name.casefold())
        files[name] = {"bytes": size, "sha256": digest}
    if sum(row["bytes"] for row in files.values()) > release_packs.MAX_TOTAL_BYTES:
        raise ValueError("Candidate inventory exceeds bounded total size")
    missing = sorted(set(manifest["paths"]) - files.keys())
    if missing:
        raise ValueError("Missing legacy public paths: " + ", ".join(missing))
    immutable = {
        **manifest["pdfs"],
        manifest["receipt"]["path"]: {key: manifest["receipt"][key] for key in ("bytes", "sha256")},
    }
    for name, row in immutable.items():
        if files.get(name) != row:
            raise ValueError(f"Original public PDF or historical receipt changed: {name}")
    # Additional same-named PDF/TEX locations must remain copies, never replacements.
    originals = {
        Path(name).name: {k: row[k] for k in ("bytes", "sha256")} for name, row in manifest["source_originals"].items()
    }
    for name, row in files.items():
        if Path(name).name in originals and row != originals[Path(name).name]:
            raise ValueError(f"Additional paper location is not an original-byte copy: {name}")
    return dict(sorted(files.items()))


class _HTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: set[str] = set()
        self.refresh: list[str] = []
        self.document = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.document = True
        for key in ("id", "name") if tag == "a" else ("id",):
            value = values.get(key)
            if value and not value.startswith("__"):
                self.anchors.add(value)
        if tag == "meta" and (values.get("http-equiv") or "").strip().lower() == "refresh":
            self.refresh.append(values.get("content") or "")


def _html(raw: bytes, name: str, manifest: dict[str, Any]) -> dict[str, Any]:
    if len(raw) > MAX_BODY:
        raise ValueError(f"HTML exceeds bounded size: {name}")
    parser = _HTML()
    parser.feed(raw.decode("utf-8"))
    if not parser.document:
        raise ValueError(f"Expected an HTML document, not a replacement: {name}")
    missing = set(manifest["anchors"].get(name, [])) - parser.anchors
    if missing:
        raise ValueError(f"Removed legacy anchors in {name}: " + ", ".join(sorted(missing)))
    if parser.refresh != manifest["meta_refresh"].get(name, []):
        raise ValueError(f"New or changed meta refresh substitution: {name}")
    return {"anchors": sorted(parser.anchors), "meta_refresh": parser.refresh}


def _routes(files: dict[str, Any]) -> dict[str, str]:
    result = {name: name for name in files}
    result.update({name[:-10]: name for name in files if name == "index.html" or name.endswith("/index.html")})
    return dict(sorted(result.items()))


def _base(
    files: dict[str, Any], manifest: dict[str, Any], pack_manifest: Path, commit: str, version: str, mode: str
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "commit": commit,
        "version": version,
        "mode": mode,
        "origin": ORIGIN,
        "manifest_sha256": MANIFEST_SHA256,
        "site_packs_sha256": release_packs.digest(pack_manifest),
        "legacy_paths": manifest["paths"],
        "index_routes": manifest["index_routes"],
        "immutable_pdfs": manifest["pdfs"],
        "historical_receipt": manifest["receipt"],
        "source_originals": manifest["source_originals"],
        "candidate_files": files,
    }


def check_site(site: Path, pack_manifest: Path, commit: str, version: str, *, root: Path = ROOT) -> dict[str, Any]:
    """Check every candidate byte plus original sources, URL floors and HTML anchors."""
    manifest = _manifest(root)
    _sources(root, manifest)
    files = _pack(pack_manifest, manifest, commit, version)
    actual = _inventory(site)
    if actual != files:
        missing = sorted(files.keys() - actual.keys())
        extra = sorted(actual.keys() - files.keys())
        changed = sorted(name for name in files.keys() & actual.keys() if actual[name] != files[name])
        raise ValueError(f"Site differs from exact candidate pack: missing={missing}, extra={extra}, changed={changed}")
    html = {}
    for name in files:
        path = site / name
        if name.lower().endswith((".html", ".htm")):
            html[name] = _html(path.read_bytes(), name, manifest)
        else:
            with path.open("rb") as stream:
                prefix = stream.read(4096).lstrip().lower()
            if name.lower().endswith(".pdf") and not prefix.startswith(b"%pdf-"):
                raise ValueError(f"Original PDF replaced with a non-PDF: {name}")
            if prefix.startswith((b"<!doctype html", b"<html")):
                raise ValueError(f"Public asset replaced with HTML: {name}")
    observations = [
        {"path": route, "target": name, "method": "LOCAL", "status": "present", **files[name], **html.get(name, {})}
        for route, name in _routes(files).items()
    ]
    return {
        **_base(files, manifest, pack_manifest, commit, version, "local"),
        "observations": observations,
        "passed": True,
        "errors": [],
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _fetch(url: str, method: str, size: int) -> tuple[int, str, dict[str, str], bytes]:
    request = urllib.request.Request(
        url,
        method=method,
        headers={
            "User-Agent": "AGIAlpha-Legacy-URL-Acceptance",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
        },
    )
    try:
        for attempt in range(1, 4):
            try:
                response = urllib.request.build_opener(_NoRedirect()).open(request, timeout=60)
            except urllib.error.HTTPError as exc:
                exc.close()
                if exc.code != 503:
                    raise
                print(f"Legacy URL HTTP 503: {method} {url} (attempt {attempt}/3)", file=sys.stderr, flush=True)
                if attempt == 3:
                    raise
                time.sleep(attempt)
                continue
            with response:
                headers = {key.lower(): value for key, value in response.headers.items()}
                raw = response.read(size + 1) if method == "GET" else b""
                return response.status, response.geturl(), headers, raw
    except (OSError, http.client.HTTPException) as exc:
        raise RuntimeError(f"{method} {url}: public request failed: {exc}") from exc
    raise RuntimeError(f"{method} {url}: public request attempts exhausted")


def _observe(route: str, name: str, row: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    html = name.lower().endswith((".html", ".htm"))
    pdf = name.lower().endswith(".pdf")
    method = "GET" if html or pdf or name == manifest["receipt"]["path"] else "HEAD"
    url = ORIGIN + quote(route, safe="/")
    if method == "GET" and row["bytes"] > MAX_BODY:
        raise ValueError(f"{method} {url}: Public body exceeds bounded size: {name}")
    status, final_url, headers, raw = _fetch(url, method, row["bytes"])
    if status != 200 or final_url != url or "location" in headers or "refresh" in headers:
        raise ValueError(f"{method} {url}: Expected direct HTTP 200 without redirection: {route}")
    if headers.get("content-encoding", "identity").lower() not in {"identity", ""}:
        raise ValueError(f"{method} {url}: Unexpected transformed response: {route}")
    length = headers.get("content-length", "")
    if not re.fullmatch(r"\d+", length) or int(length) != row["bytes"]:
        raise ValueError(f"{method} {url}: Exact Content-Length required: {route}")
    content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if (html and content_type != "text/html") or (pdf and content_type != "application/pdf"):
        raise ValueError(f"{method} {url}: Wrong public content type: {route}")
    if not html and (not content_type or content_type in {"text/html", "application/xhtml+xml"}):
        raise ValueError(f"{method} {url}: Non-HTML asset substituted or missing content type: {route}")
    observation = {
        "path": route,
        "target": name,
        "method": method,
        "status": status,
        "url": final_url,
        "content_type": content_type,
        "content_length": int(length),
    }
    if method == "GET":
        if len(raw) != row["bytes"] or _sha(raw) != row["sha256"]:
            raise ValueError(f"{method} {url}: Public bytes differ from the candidate: {route}")
        if pdf and not raw.startswith(b"%PDF-"):
            raise ValueError(f"{method} {url}: Expected original PDF bytes: {route}")
        observation.update(bytes=len(raw), sha256=_sha(raw))
        if html:
            try:
                observation.update(_html(raw, name, manifest))
            except ValueError as exc:
                raise ValueError(f"{method} {url}: {exc}") from exc
    return observation


def check_public(
    site: Path, pack_manifest: Path, commit: str, version: str, *, root: Path = ROOT, origin: str = ORIGIN
) -> dict[str, Any]:
    """Check all candidate paths/index routes directly, with bounded read-only requests."""
    if origin != ORIGIN:
        raise ValueError("Public compatibility requires the exact canonical origin")
    local = check_site(site, pack_manifest, commit, version, root=root)
    manifest = _manifest(root)
    files = local["candidate_files"]
    routes = list(_routes(files).items())
    with ThreadPoolExecutor(max_workers=8) as pool:
        observations = list(pool.map(lambda item: _observe(item[0], item[1], files[item[1]], manifest), routes))
    return {
        **_base(files, manifest, pack_manifest, commit, version, "public"),
        "observations": observations,
        "passed": True,
        "errors": [],
    }


def _same_json(actual: Any, expected: Any) -> bool:
    """Compare evidence without Python's bool/int or int/float equality coercion."""
    return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)


def verify_report(
    report: dict[str, Any], commit: str, version: str, pack_manifest: Path, *, mode: str, root: Path = ROOT
) -> None:
    """Recheck pinned originals and exact pack identity; reject partial or stale evidence."""
    if mode not in {"local", "public"}:
        raise ValueError("Compatibility mode must be local or public")
    manifest = _manifest(root)
    _sources(root, manifest)
    files = _pack(pack_manifest, manifest, commit, version)
    expected = _base(files, manifest, pack_manifest, commit, version, mode)
    if (
        not isinstance(report, dict)
        or set(report) != set(expected) | {"observations", "passed", "errors"}
        or report.get("passed") is not True
        or report.get("errors") != []
        or any(not _same_json(report.get(key), value) for key, value in expected.items())
    ):
        raise ValueError("Compatibility report differs from the exact source, manifest, origin, mode or pack")
    observations = report["observations"]
    routes = _routes(files)
    if not isinstance(observations, list) or len(observations) != len(routes):
        raise ValueError("Incomplete public path/index-route observations")
    seen = set()
    for item in observations:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("Invalid compatibility observation")
        route = item["path"]
        if route in seen or route not in routes:
            raise ValueError("Duplicate or unexpected compatibility route")
        seen.add(route)
        name = routes[route]
        row = files[name]
        html = name.lower().endswith((".html", ".htm"))
        pdf = name.lower().endswith(".pdf")
        fields: dict[str, Any] = {"path": route, "target": name}
        if mode == "local":
            fields.update(method="LOCAL", status="present", **row)
        else:
            method = "GET" if html or pdf or name == manifest["receipt"]["path"] else "HEAD"
            fields.update(method=method, status=200, url=ORIGIN + quote(route, safe="/"), content_length=row["bytes"])
            content_type = item.get("content_type")
            if (
                not isinstance(content_type, str)
                or not content_type
                or (html and content_type != "text/html")
                or (pdf and content_type != "application/pdf")
                or (not html and content_type in {"text/html", "application/xhtml+xml"})
            ):
                raise ValueError("Missing or substituted public content type")
            fields["content_type"] = content_type
            if method == "GET":
                fields.update(row)
        if html:
            anchors = item.get("anchors")
            if (
                not isinstance(anchors, list)
                or any(not isinstance(anchor, str) for anchor in anchors)
                or anchors != sorted(set(anchors))
                or not set(manifest["anchors"].get(name, [])) <= set(anchors)
            ):
                raise ValueError(f"Missing legacy anchor observations: {name}")
            fields.update(anchors=anchors, meta_refresh=manifest["meta_refresh"].get(name, []))
        if not _same_json(item, fields):
            raise ValueError(f"Incomplete, stale or redirected compatibility observation: {route}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--pack-manifest", "--site-packs", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--version", default=tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--origin", default=ORIGIN)
    args = parser.parse_args()
    if args.public:
        report = check_public(args.site, args.pack_manifest, args.commit, args.version, origin=args.origin)
    else:
        if args.origin != ORIGIN:
            parser.error("Only the canonical origin is supported")
        report = check_site(args.site, args.pack_manifest, args.commit, args.version)
    verify_report(report, args.commit, args.version, args.pack_manifest, mode=report["mode"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": True,
                "mode": report["mode"],
                "paths": len(report["observations"]),
                "report": str(args.output),
                "site_packs_sha256": report["site_packs_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
