# SPDX-License-Identifier: Apache-2.0
"""Offline, adversarial coverage of the historical public URL acceptance floor."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest

from scripts import legacy_public_urls as checker
from scripts import release_packs

COMMIT = "a" * 40
VERSION = "1.37.0"


def record(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(root: Path, name: str, raw: bytes) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    root, site = tmp_path / "repo", tmp_path / "site"
    pdf, tex, receipt = b"%PDF-1.7\noriginal paper\n", b"original TeX source\n", b'{"historic": true}\n'
    bodies = {
        "index.html": b'<html><h1 id="old">New wording</h1><a name="old-name"></a></html>',
        "guide/index.html": b'<html><p id="guide">Guide</p></html>',
        "gallery.html": b'<html><meta http-equiv="refresh" content="0; url=index.html"></html>',
        "paper.pdf": pdf,
        "paper.tex": tex,
        "paper-link-repair-20261021.json": receipt,
        "models/model.onnx": b"\x00model bytes\x01",
        "assets/a space.svg": b"<svg></svg>",
    }
    sources = {"docs/paper.pdf": pdf, "docs/paper.tex": tex}
    manifest = {
        "schema": "agialpha.legacy-public-urls.manifest.v1",
        "origin": checker.ORIGIN,
        "paths": sorted(bodies),
        "index_routes": ["", "guide/"],
        "pdfs": {"paper.pdf": record(pdf)},
        "receipt": {"path": "paper-link-repair-20261021.json", **record(receipt)},
        "source_originals": {name: {**record(raw), "public_paths": [Path(name).name]} for name, raw in sources.items()},
        "anchors": {"index.html": ["old", "old-name"], "guide/index.html": ["guide"]},
        "meta_refresh": {"gallery.html": ["0; url=index.html"]},
    }
    for name, raw in sources.items():
        write(root, name, raw)
    for name, raw in bodies.items():
        write(site, name, raw)
    manifest_path = write(root, checker.MANIFEST, json.dumps(manifest).encode())
    monkeypatch.setattr(checker, "MANIFEST_SHA256", release_packs.digest(manifest_path))
    pack = release_packs.pack(site, tmp_path / "packs", "site", commit=COMMIT, version=VERSION)
    return root, site, pack, manifest


def local(candidate):
    root, site, pack, _ = candidate
    return checker.check_site(site, pack, COMMIT, VERSION, root=root)


def verify(candidate, report, mode="local"):
    root, _, pack, _ = candidate
    checker.verify_report(report, COMMIT, VERSION, pack, mode=mode, root=root)


def fake_public(candidate, monkeypatch, mutate=None):
    _, site, _, _ = candidate
    calls = []

    def fetch(url, method, size):
        route = unquote(url.removeprefix(checker.ORIGIN))
        name = route + "index.html" if not route or route.endswith("/") else route
        raw = (site / name).read_bytes()
        media = "text/html" if name.endswith(".html") else "application/pdf" if name.endswith(".pdf") else "text/plain"
        headers = {"content-type": media, "content-length": str(len(raw))}
        result = (200, url, headers, raw if method == "GET" else b"")
        calls.append((route, method, size))
        return mutate(result) if mutate else result

    monkeypatch.setattr(checker, "_fetch", fetch)
    return calls


def public(candidate):
    root, site, pack, _ = candidate
    return checker.check_public(site, pack, COMMIT, VERSION, root=root)


def test_real_manifest_pin_sources_and_history_are_intact():
    manifest = checker._manifest(checker.ROOT)
    checker._sources(checker.ROOT, manifest)
    assert len(manifest["paths"]) == 997
    assert len(manifest["pdfs"]) == 28
    assert len(manifest["source_originals"]) == 50
    assert manifest["receipt"]["sha256"] == "a5fdf39d4b8e3b76d3b1d908a9309b5cc173106cba47259f09c14f6941408158"
    assert manifest["receipt"]["path"] in manifest["paths"]
    assert set(manifest["index_routes"]) <= set(checker._routes(dict.fromkeys(manifest["paths"])))
    for name, row in manifest["source_originals"].items():
        for public_path in row["public_paths"]:
            assert public_path in manifest["paths"]
            if public_path in manifest["pdfs"]:
                assert manifest["pdfs"][public_path] == {key: row[key] for key in ("bytes", "sha256")}


def test_local_roundtrip_covers_file_and_directory_urls(candidate):
    report = local(candidate)
    verify(candidate, report)
    paths = {item["path"] for item in report["observations"]}
    assert {"", "index.html", "guide/", "guide/index.html"} <= paths
    assert len(paths) == len(report["candidate_files"]) + 2


def test_public_get_bytes_and_head_scope_are_explicit(candidate, monkeypatch):
    calls = fake_public(candidate, monkeypatch)
    report = public(candidate)
    verify(candidate, report, "public")
    assert len(calls) == len(report["observations"])
    for item in report["observations"]:
        should_get = item["target"].endswith((".html", ".pdf")) or item["target"] == candidate[3]["receipt"]["path"]
        assert item["method"] == ("GET" if should_get else "HEAD")
        assert ("sha256" in item) is should_get
    assert next(item for item in report["observations"] if "space" in item["path"])["url"].endswith("a%20space.svg")


def test_html_evolution_and_additional_original_copies_are_allowed(candidate, tmp_path):
    root, site, _, manifest = candidate
    write(
        site, "index.html", b'<html><h1 id="old">Completely revised</h1><a name="old-name"></a><p id="new"></p></html>'
    )
    write(site, "new/index.html", b"<html><h1>Additional content</h1></html>")
    write(site, "copies/paper.pdf", (root / "docs/paper.pdf").read_bytes())
    pack = release_packs.pack(site, tmp_path / "repacked", "site", commit=COMMIT, version=VERSION)
    report = checker.check_site(site, pack, COMMIT, VERSION, root=root)
    checker.verify_report(report, COMMIT, VERSION, pack, mode="local", root=root)
    assert "new/" in {item["path"] for item in report["observations"]}
    assert manifest["anchors"]["index.html"] == ["old", "old-name"]


@pytest.mark.parametrize("name", ["paper.pdf", "paper-link-repair-20261021.json", "paper.tex"])
def test_changed_original_or_history_rejected_even_if_repacked(candidate, tmp_path, name):
    root, site, _, _ = candidate
    write(site, name, b"replacement")
    pack = release_packs.pack(site, tmp_path / "repacked", "site", commit=COMMIT, version=VERSION)
    with pytest.raises(ValueError, match="changed|original-byte"):
        checker.check_site(site, pack, COMMIT, VERSION, root=root)


def test_additional_copy_cannot_replace_original(candidate, tmp_path):
    root, site, _, _ = candidate
    (site / "paper.pdf").rename(site / "new-paper.pdf")
    pack = release_packs.pack(site, tmp_path / "repacked", "site", commit=COMMIT, version=VERSION)
    with pytest.raises(ValueError, match="Missing legacy public paths"):
        checker.check_site(site, pack, COMMIT, VERSION, root=root)


@pytest.mark.parametrize("damage", ["missing", "extra", "changed", "source", "manifest", "symlink", "case"])
def test_local_tampering_fails(candidate, damage):
    root, site, _, _ = candidate
    if damage == "missing":
        (site / "models/model.onnx").unlink()
    elif damage == "extra":
        write(site, "unpacked.txt", b"extra")
    elif damage == "changed":
        write(site, "models/model.onnx", b"changed model")
    elif damage == "source":
        write(root, "docs/paper.tex", b"changed original")
    elif damage == "manifest":
        with (root / checker.MANIFEST).open("ab") as stream:
            stream.write(b" ")
    elif damage == "symlink":
        (site / "models/model.onnx").unlink()
        (site / "models/model.onnx").symlink_to(site / "paper.pdf")
    else:
        write(site, "INDEX.html", b"case collision")
    with pytest.raises(ValueError):
        local(candidate)


@pytest.mark.parametrize(
    "raw",
    [
        b'<html><h1 id="new">old anchor removed</h1></html>',
        b'<html><h1 id="old"></h1><a name="old-name"></a><meta http-equiv="refresh" content="0;url=other"></html>',
        b'<html><h1 id="old"></h1><a name="old-name"></a><meta http-equiv=" Refresh " content="0;url=other"></html>',
        b"not an HTML document",
    ],
)
def test_missing_anchor_or_redirect_substitution_rejected(candidate, raw):
    with pytest.raises(ValueError):
        checker._html(raw, "index.html", candidate[3])


@pytest.mark.parametrize(
    "damage", ["commit", "version", "schema", "duplicate", "case", "traversal", "bool-size", "hash"]
)
def test_invalid_pack_inventory_rejected(candidate, damage):
    _, _, pack, _ = candidate
    data = json.loads(pack.read_bytes())
    if damage in {"commit", "version", "schema"}:
        data[damage] = "wrong"
    elif damage == "duplicate":
        data["files"].append(data["files"][0])
    elif damage == "case":
        duplicate = deepcopy(data["files"][0])
        duplicate["path"] = duplicate["path"].upper()
        data["files"].append(duplicate)
    elif damage == "traversal":
        data["files"][0]["path"] = "../escape"
    elif damage == "bool-size":
        data["files"][0]["bytes"] = True
    else:
        data["files"][0]["sha256"] = "bad"
    pack.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        local(candidate)


@pytest.mark.parametrize("damage", ["302", "final-url", "location", "refresh", "encoding", "length", "type", "bytes"])
def test_public_substitution_or_redirect_rejected(candidate, monkeypatch, damage):
    def mutate(result):
        status, url, headers, raw = result
        if damage == "302":
            status = 302
        elif damage == "final-url":
            url += "?redirected=1"
        elif damage in {"location", "refresh"}:
            headers[damage] = "https://example.invalid/replacement"
        elif damage == "encoding":
            headers["content-encoding"] = "gzip"
        elif damage == "length":
            headers["content-length"] = "0"
        elif damage == "type":
            headers["content-type"] = "application/xhtml+xml"
        elif raw:
            raw = b"X" + raw[1:]
        return status, url, headers, raw

    fake_public(candidate, monkeypatch, mutate)
    with pytest.raises(ValueError):
        public(candidate)


@pytest.mark.parametrize(
    "damage",
    ["mode", "commit", "origin", "pack-hash", "partial", "duplicate", "extra", "anchor", "status-type", "size-type"],
)
@pytest.mark.parametrize("mode", ["local", "public"])
def test_report_replay_or_incomplete_evidence_rejected(candidate, monkeypatch, damage, mode):
    fake_public(candidate, monkeypatch)
    report = public(candidate) if mode == "public" else local(candidate)
    if damage in {"mode", "commit", "origin"}:
        report[damage] = "wrong"
    elif damage == "pack-hash":
        report["site_packs_sha256"] = "0" * 64
    elif damage == "partial":
        report["observations"].pop()
    elif damage == "duplicate":
        report["observations"][-1] = report["observations"][0]
    elif damage == "extra":
        report["observations"][0]["redirected"] = False
    elif damage == "anchor":
        report["observations"][0]["anchors"] = []
    elif damage == "status-type":
        report["observations"][0]["status"] = 200.0 if mode == "public" else True
    else:
        field = "content_length" if mode == "public" else "bytes"
        report["observations"][0][field] = float(report["observations"][0][field])
    with pytest.raises(ValueError):
        verify(candidate, report, mode)


def test_report_is_bound_to_pack_file_not_just_file_inventory(candidate):
    report = local(candidate)
    pack = candidate[2]
    pack.write_bytes(pack.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="exact source"):
        verify(candidate, report)


def test_public_rejects_other_origin_without_fetch(candidate, monkeypatch):
    monkeypatch.setattr(checker, "_fetch", lambda *args: pytest.fail("unexpected network attempt"))
    root, site, pack, _ = candidate
    with pytest.raises(ValueError, match="canonical origin"):
        checker.check_public(site, pack, COMMIT, VERSION, root=root, origin="https://example.invalid/")


def test_fetch_disables_redirects_and_never_reads_head_bodies(monkeypatch):
    class Response:
        status = 200
        headers = {"Content-Type": "application/octet-stream"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def geturl(self):
            return checker.ORIGIN + "model.onnx"

        def read(self, size):
            reads.append(size)
            return b"abc"

    class Opener:
        def open(self, request, timeout):
            assert request.get_header("Accept-encoding") == "identity"
            assert timeout == 60
            return Response()

    def build(handler):
        assert isinstance(handler, checker._NoRedirect)
        assert handler.redirect_request(None, None, 302, "Found", {}, "https://example.invalid/") is None
        return Opener()

    reads = []
    monkeypatch.setattr(checker.urllib.request, "build_opener", build)
    assert checker._fetch(checker.ORIGIN + "model.onnx", "HEAD", 10)[3] == b""
    assert reads == []
    assert checker._fetch(checker.ORIGIN + "model.onnx", "GET", 10)[3] == b"abc"
    assert reads == [11]


def test_duplicate_json_keys_are_not_admitted(tmp_path):
    path = write(tmp_path, "report.json", b'{"passed": false, "passed": true}')
    with pytest.raises(ValueError):
        checker._json(path)


def test_bounded_html_and_public_get_reject_before_fetch(candidate, monkeypatch):
    monkeypatch.setattr(checker, "MAX_BODY", 1)
    monkeypatch.setattr(checker, "_fetch", lambda *args: pytest.fail("oversized GET attempted"))
    with pytest.raises(ValueError, match="bounded size"):
        checker._html(b"<html></html>", "index.html", candidate[3])
    with pytest.raises(ValueError, match="bounded size"):
        checker._observe("paper.pdf", "paper.pdf", candidate[3]["pdfs"]["paper.pdf"], candidate[3])


@pytest.mark.parametrize("damage", ["short", "oversized", "same-sized"])
def test_public_pdf_body_must_match_exact_original(candidate, monkeypatch, damage):
    row = candidate[3]["pdfs"]["paper.pdf"]
    raw = (candidate[1] / "paper.pdf").read_bytes()
    body = raw[:-1] if damage == "short" else raw + b"x" if damage == "oversized" else raw[:-1] + b"x"
    monkeypatch.setattr(
        checker,
        "_fetch",
        lambda url, *args: (200, url, {"content-length": str(len(raw)), "content-type": "application/pdf"}, body),
    )
    with pytest.raises(ValueError, match="bytes differ"):
        checker._observe("paper.pdf", "paper.pdf", row, candidate[3])


def test_repack_with_changed_additional_copy_is_rejected(candidate, tmp_path):
    root, site, _, _ = candidate
    write(site, "copies/paper.pdf", b"%PDF-1.7\nnot original\n")
    pack = release_packs.pack(site, tmp_path / "repacked", "site", commit=COMMIT, version=VERSION)
    with pytest.raises(ValueError, match="original-byte copy"):
        checker.check_site(site, pack, COMMIT, VERSION, root=root)


def test_source_symlink_is_not_an_original(candidate):
    root, site, _, _ = candidate
    source = root / "docs/paper.pdf"
    source.unlink()
    source.symlink_to(site / "paper.pdf")
    with pytest.raises(ValueError, match="Symbolic link"):
        local(candidate)


def test_existing_refresh_cannot_change_or_disappear(candidate):
    with pytest.raises(ValueError, match="meta refresh"):
        checker._html(b"<html>Removed old redirect</html>", "gallery.html", candidate[3])


def test_report_rejects_json_numeric_coercion_inside_candidate_inventory(candidate):
    report = local(candidate)
    row = report["candidate_files"]["paper.pdf"]
    row["bytes"] = float(row["bytes"])
    with pytest.raises(ValueError, match="exact source"):
        verify(candidate, report)


def test_candidate_inventory_rejects_integer_subclasses(candidate: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    class IntegerSubclass(int):
        pass

    root, _, pack, manifest = candidate
    data = json.loads(pack.read_bytes())
    data["files"][0]["bytes"] = IntegerSubclass(data["files"][0]["bytes"])
    monkeypatch.setattr(checker, "_json", lambda path: data)
    with pytest.raises(ValueError, match="Invalid or duplicate candidate path"):
        checker._pack(pack, manifest, COMMIT, VERSION)


@pytest.fixture
def fetch_sequence(monkeypatch):
    """Exercise the real fetch/observe path without networking or sleeping."""
    from io import BytesIO
    from urllib.error import HTTPError

    calls, sleeps, responses, errors = [], [], [], []
    outcomes = []
    url = checker.ORIGIN + "paper.pdf"
    raw = b"%PDF-1.7\noriginal paper\n"

    class Response:
        status = 200
        headers = {"Content-Length": str(len(raw)), "Content-Type": "application/pdf"}
        closed = False

        def __init__(self, outcome):
            self.outcome = outcome
            self.reads = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def geturl(self):
            return url

        def read(self, size):
            self.reads.append(size)
            if self.outcome == "read-timeout":
                raise TimeoutError("body stalled")
            return self.outcome

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, request.get_method(), timeout))
            outcome = outcomes.pop(0)
            if isinstance(outcome, int):
                error = HTTPError(url, outcome, "HTTP failure", {}, BytesIO(b"error body"))
                errors.append(error)
                raise error
            if isinstance(outcome, Exception):
                raise outcome
            response = Response(outcome)
            responses.append(response)
            return response

    def build(handler):
        assert isinstance(handler, checker._NoRedirect)
        return Opener()

    monkeypatch.setattr(checker.urllib.request, "build_opener", build)
    monkeypatch.setattr(checker.time, "sleep", sleeps.append)
    return outcomes, calls, sleeps, responses, errors, url, raw


@pytest.mark.parametrize("status", [429, 502, 503, 504])
@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_fetch_retries_only_transient_http_statuses(fetch_sequence, status, method):
    outcomes, calls, sleeps, responses, errors, url, raw = fetch_sequence
    outcomes.extend([status, status, raw])
    assert checker._fetch(url, method, len(raw))[3] == (raw if method == "GET" else b"")
    assert calls == [(url, method, 60)] * 3
    assert sleeps == [1, 2]
    assert all(error.fp.closed for error in errors)
    assert all(response.closed for response in responses)
    assert responses[0].reads == ([len(raw) + 1] if method == "GET" else [])


@pytest.mark.parametrize("failure", ["open-timeout", "wrapped-timeout", "read-timeout"])
def test_fetch_retries_timeouts_without_partial_body(fetch_sequence, failure):
    from urllib.error import URLError

    outcomes, calls, sleeps, responses, _, url, raw = fetch_sequence
    error = TimeoutError("connection stalled")
    outcome = error if failure == "open-timeout" else URLError(error) if failure == "wrapped-timeout" else failure
    outcomes.extend([outcome, raw])
    assert checker._fetch(url, "GET", len(raw))[3] == raw
    assert len(calls) == 2
    assert sleeps == [1]
    assert all(response.closed for response in responses)


@pytest.mark.parametrize("failure", [429, 502, 503, 504, "open-timeout", "wrapped-timeout", "read-timeout"])
def test_fetch_retry_exhaustion_is_bounded_and_diagnostic(fetch_sequence, failure):
    from urllib.error import URLError

    outcomes, calls, sleeps, responses, errors, url, raw = fetch_sequence
    outcome = TimeoutError("stalled") if failure == "open-timeout" else failure
    if failure == "wrapped-timeout":
        outcome = URLError(TimeoutError("stalled"))
    outcomes.extend([outcome] * 3 + [raw])
    with pytest.raises(ValueError) as caught:
        checker._fetch(url, "GET", len(raw))
    status = failure if isinstance(failure, int) else 200 if failure == "read-timeout" else "unavailable"
    assert f"method=GET url={url} status={status} attempts=3" in str(caught.value)
    assert len(calls) == 3
    assert sleeps == [1, 2]
    assert outcomes == [raw]
    assert all(error.fp.closed for error in errors)
    assert all(response.closed for response in responses)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308, 400, 401, 403, 404, 410, 500])
def test_fetch_permanent_http_failure_is_not_retried(fetch_sequence, status):
    outcomes, calls, sleeps, _, errors, url, raw = fetch_sequence
    outcomes.extend([status, raw])
    with pytest.raises(ValueError, match=f"status={status} attempts=1"):
        checker._fetch(url, "GET", len(raw))
    assert len(calls) == 1
    assert sleeps == []
    assert errors[0].fp.closed


def test_fetch_non_timeout_network_failure_is_not_retried(fetch_sequence):
    from ssl import SSLCertVerificationError
    from urllib.error import URLError

    outcomes, calls, sleeps, _, _, url, raw = fetch_sequence
    outcomes.extend([URLError(SSLCertVerificationError("invalid certificate")), raw])
    with pytest.raises(ValueError, match="status=unavailable attempts=1"):
        checker._fetch(url, "GET", len(raw))
    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("damage", ["short", "oversized", "same-sized"])
def test_transient_retry_does_not_mask_body_integrity(candidate, fetch_sequence, damage):
    outcomes, calls, sleeps, _, _, _, raw = fetch_sequence
    body = raw[:-1] if damage == "short" else raw + b"x" if damage == "oversized" else raw[:-1] + b"x"
    outcomes.extend([503, body, raw])
    with pytest.raises(ValueError, match="bytes differ"):
        checker._observe("paper.pdf", "paper.pdf", record(raw), candidate[3])
    assert len(calls) == 2
    assert sleeps == [1]
    assert outcomes == [raw]


@pytest.mark.parametrize("status", [302, 404])
def test_transient_retry_does_not_mask_later_permanent_failure(fetch_sequence, status):
    outcomes, calls, sleeps, _, _, url, raw = fetch_sequence
    outcomes.extend([503, status, raw])
    with pytest.raises(ValueError, match=f"status={status} attempts=2"):
        checker._fetch(url, "GET", len(raw))
    assert len(calls) == 2
    assert sleeps == [1]
    assert outcomes == [raw]


@pytest.mark.smoke
@pytest.mark.parametrize("name", ["evidence/frozen/index.html.txt", "evidence/frozen/template.htm.txt"])
def test_archived_html_text_is_preserved_by_real_pack_and_direct_public_get(candidate, tmp_path, monkeypatch, name):
    root, site, _, _ = candidate
    raw = b"<!doctype html>\r\n<html><body>Frozen source, not a rendered page.</body></html>\n"
    write(site, name, raw)
    pack = release_packs.pack(site, tmp_path / "with-source", "site", commit=COMMIT, version=VERSION)
    report = checker.check_site(site, pack, COMMIT, VERSION, root=root)
    checker.verify_report(report, COMMIT, VERSION, pack, mode="local", root=root)
    patched = (root, site, pack, candidate[3])
    calls = fake_public(patched, monkeypatch)
    original_fetch = checker._fetch

    def fetch(url, method, size):
        status, final_url, headers, body = original_fetch(url, method, size)
        if url.endswith(name):
            headers["content-type"] = "text/plain"
        return status, final_url, headers, body

    monkeypatch.setattr(checker, "_fetch", fetch)
    public_report = checker.check_public(site, pack, COMMIT, VERSION, root=root)
    checker.verify_report(public_report, COMMIT, VERSION, pack, mode="public", root=root)
    observed = next(item for item in public_report["observations"] if item["target"] == name)
    assert observed["method"] == "GET"
    assert observed["bytes"] == len(raw) and observed["sha256"] == hashlib.sha256(raw).hexdigest()
    assert observed["content_type"] == "text/plain"
    assert "anchors" not in observed and "meta_refresh" not in observed
    assert (site / name).read_bytes() == raw
    assert any(call[0].endswith(name) and call[1] == "GET" for call in calls)
    write(site, name, raw + b"changed")
    with pytest.raises(ValueError, match="exact candidate pack"):
        checker.check_site(site, pack, COMMIT, VERSION, root=root)


@pytest.mark.smoke
@pytest.mark.parametrize("content_type", ["text/html", "application/xhtml+xml", "application/octet-stream"])
def test_archived_html_source_refuses_a_rendered_or_untyped_response(monkeypatch, content_type):
    name = "evidence/frozen/index.html.txt"
    raw = b"<!doctype html>\n<html>archived source</html>\n"
    monkeypatch.setattr(
        checker,
        "_fetch",
        lambda url, *args: (
            200,
            url,
            {"content-length": str(len(raw)), "content-type": content_type},
            raw,
        ),
    )
    with pytest.raises(ValueError, match="content type"):
        checker._observe(name, name, record(raw), {"receipt": {"path": "receipt.json"}})


@pytest.mark.smoke
@pytest.mark.parametrize("damage", ["short", "oversized", "same-sized"])
def test_archived_html_source_public_body_is_byte_exact(monkeypatch, damage):
    name = "evidence/frozen/index.html.txt"
    raw = b"<!doctype html>\n<html>archived source</html>\n"
    body = raw[:-1] if damage == "short" else raw + b"x" if damage == "oversized" else raw[:-1] + b"x"
    monkeypatch.setattr(
        checker,
        "_fetch",
        lambda url, *args: (
            200,
            url,
            {"content-length": str(len(raw)), "content-type": "text/plain"},
            body,
        ),
    )
    with pytest.raises(ValueError, match="bytes differ"):
        checker._observe(name, name, record(raw), {"receipt": {"path": "receipt.json"}})


@pytest.mark.smoke
@pytest.mark.parametrize("name", ["fallback.txt", "data.json", "models/model.onnx"])
def test_ordinary_assets_still_refuse_html_fallback_after_repacking(candidate, tmp_path, name):
    root, site, _, _ = candidate
    write(site, name, b"<!doctype html>\n<html>Wrong fallback</html>")
    pack = release_packs.pack(site, tmp_path / "fallback", "site", commit=COMMIT, version=VERSION)
    with pytest.raises(ValueError, match="Public asset replaced with HTML"):
        checker.check_site(site, pack, COMMIT, VERSION, root=root)
