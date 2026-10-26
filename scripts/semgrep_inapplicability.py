# SPDX-License-Identifier: Apache-2.0
"""Exact inapplicability matcher used by the primary static scanner.

An absent approved pin leaves findings unadmitted. A separately reviewed fixed
map can classify only cases whose source, rule and full repository context match.
It never changes engine output, suppresses a rule, or grants release or runtime
authority. Inputs are captured by the operator's scanner, not by a candidate,
imported memory, environment variable, or command-line selector.

Normalization is a cycle breaker, not an approval anchor: changing both the
map and its literal pin is a protected criteria/source edit requiring separate
exact-source independent and configured review. Runtime candidates have no
permission to modify either file.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import partial
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import tempfile
from types import MappingProxyType
from typing import Any, Mapping, cast

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = "scripts/data/semgrep_python_inapplicability.json"
APPROVED_MAP_SHA256: str | None = None
REVIEWABLE_PACK_SHA256S = (
    "de5bc79d074c3b4146338a0bf95830406f169bd91ac590a2f1ef111f162e23f5",
    "e3c25cf9b28ddfd3cb1b7f240d2fc0998734199efa539fa0b10281487a602e79",
)
SEMGREP_VERSION = "1.99.0"
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_MAP_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 1_000_000
MAX_PACK_BYTES = 2_000_000
MAX_INVENTORY_FILES = 10_000
MAX_INVENTORY_FILE_BYTES = 64 * 1024 * 1024
MAX_INVENTORY_TOTAL_BYTES = 512 * 1024 * 1024
MODULE_PATH = "scripts/semgrep_inapplicability.py"


class Refusal(ValueError):
    """Incomplete, changed or unreviewed evidence cannot be matched."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise Refusal(reason)


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _json(raw: bytes, maximum: int) -> dict[str, Any]:
    _require(0 < len(raw) <= maximum, "JSON evidence is empty or oversized")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            _require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(_value: str) -> Any:
        raise Refusal("Nonfinite JSON value")

    def finite(value: str) -> float:
        result = float(value)
        _require(math.isfinite(result), "Nonfinite JSON value")
        return result

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite, parse_float=finite)
    _require(type(value) is dict, "JSON evidence must be an object")
    return cast(dict[str, Any], value)


def _path(name: str) -> Path:
    _require(type(name) is str and bool(name), "Missing source path")
    path = Path(name)
    _require(
        not name.startswith("-")
        and not path.is_absolute()
        and path.as_posix() == name
        and not {"", ".", ".."}.intersection(name.split("/")),
        "Noncanonical source path",
    )
    return ROOT / path


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


@dataclass(frozen=True)
class SourceIdentity:
    sha256: str
    fingerprint: tuple[int, ...]
    size: int


@dataclass(frozen=True)
class RepositoryInventory:
    records: tuple[tuple[str, str, int, str], ...]
    fingerprints: Mapping[str, tuple[int, ...]]
    raw_sha256: Mapping[str, str]
    head_sha256: Mapping[str, str]
    sha256: str


@dataclass(frozen=True)
class TrackedBlob:
    mode: str
    oid: str
    size: int


def _git(*args: str, maximum: int = 8 * 1024 * 1024) -> bytes:
    # Git's selectors/config/replacement environment cannot redirect the fixed
    # source root or hide its real index. No inherited credentials are needed.
    environment = {
        key: os.environ[key]
        for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP")
        if key in os.environ
    }
    environment.update(
        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0"
    )
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            [
                "git",
                "--no-replace-objects",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=" + os.devnull,
                "-C",
                str(ROOT),
                *args,
            ],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            preexec_fn=partial(resource.setrlimit, resource.RLIMIT_FSIZE, (maximum + 1, maximum + 1)),
        )
        try:
            code = process.wait(timeout=10)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                process.wait(timeout=3)
        _require(
            code == 0 and os.fstat(output.fileno()).st_size <= maximum, "Git evidence failed or exceeded its bound"
        )
        output.seek(0)
        return output.read(maximum + 1)


def _tracked() -> dict[str, TrackedBlob]:
    rows = _git("ls-tree", "-r", "-l", "-z", "--full-tree", "HEAD").split(b"\0")
    _require(
        rows[-1] == b"" and 0 < len(rows) - 1 <= MAX_INVENTORY_FILES, "Tracked repository exceeds file-count bound"
    )
    files: dict[str, TrackedBlob] = {}
    total = 0
    for row in rows[:-1]:
        header, name_bytes = row.split(b"\t", 1)
        mode, kind, oid, size_text = header.decode("ascii").split()
        size = int(size_text)
        name = name_bytes.decode("utf-8")
        _path(name)
        _require(
            kind == "blob" and mode in ("100644", "100755") and name not in files, "Unknown mode or duplicate HEAD path"
        )
        _require(
            len(oid) in (40, 64) and all(char in "0123456789abcdef" for char in oid), "Unknown Git object identity"
        )
        _require(0 <= size <= MAX_INVENTORY_FILE_BYTES, "HEAD body exceeds per-file bound")
        total += size
        _require(total <= MAX_INVENTORY_TOTAL_BYTES, "HEAD exceeds total-byte bound")
        files[name] = TrackedBlob(mode, oid, size)
    _require(MODULE_PATH in files, "Matcher policy source is not tracked")
    index = {}
    for row in _git("ls-files", "--stage", "-z").split(b"\0")[:-1]:
        header, name_bytes = row.split(b"\t", 1)
        mode, oid, stage = header.decode("ascii").split()
        name = name_bytes.decode("utf-8")
        _require(stage == "0" and name not in index, "Unmerged or duplicate index path")
        index[name] = (mode, oid)
    _require(index == {name: (blob.mode, blob.oid) for name, blob in files.items()}, "Index overlays committed HEAD")
    flags = _git("ls-files", "-v", "-z").split(b"\0")[:-1]
    _require(len(flags) == len(files) and all(row.startswith(b"H ") for row in flags), "Hidden or altered index flags")
    _require({row[2:].decode("utf-8") for row in flags} == set(files), "Index flag paths differ from HEAD")
    return files


def _normalize_pin(body: bytes) -> bytes:
    """Normalize exactly one reviewed literal; every other byte stays intact."""
    try:
        tree = ast.parse(body)
    except (SyntaxError, UnicodeError) as error:
        raise Refusal("Matcher source syntax is invalid") from error
    stores = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "APPROVED_MAP_SHA256" and isinstance(node.ctx, ast.Store)
    ]
    declarations = [
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "APPROVED_MAP_SHA256"
    ]
    _require(len(stores) == len(declarations) == 1, "Duplicate or altered approved-pin declaration")
    node = declarations[0]
    expected_annotation = ast.parse("str | None", mode="eval").body
    _require(
        node.simple == 1
        and node.col_offset == 0
        and node.end_lineno == node.lineno
        and ast.dump(node.annotation) == ast.dump(expected_annotation)
        and isinstance(node.value, ast.Constant),
        "Approved pin must have its exact reviewed declaration",
    )
    assert isinstance(node.value, ast.Constant)
    value = node.value.value
    _require(
        value is None
        or (type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value)),
        "Approved pin is not a literal None or SHA256",
    )
    lines = body.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    ending = b"\r\n" if line.endswith(b"\r\n") else (b"\n" if line.endswith(b"\n") else b"")
    prefix = b"APPROVED_MAP_SHA256: str | None = "
    literal = b"None" if value is None else b'"' + cast(str, value).encode("ascii") + b'"'
    _require(line == prefix + literal + ending, "Approved pin declaration spelling changed")
    lines[node.lineno - 1] = prefix + b"None" + ending
    return b"".join(lines)


def repository_inventory() -> RepositoryInventory:
    """Hash every tracked body/mode; the fixed map has a separate exact pin."""
    files = _tracked()
    records = []
    fingerprints = {}
    raw_sha256 = {}
    head_sha256 = {}
    total = 0
    for name, blob in sorted(files.items()):
        mode = blob.mode
        path = _path(name)
        _require(path.resolve(strict=True) == path, "Tracked file or ancestor is aliased")
        before = path.lstat()
        _require(
            stat.S_ISREG(before.st_mode)
            and before.st_size <= MAX_INVENTORY_FILE_BYTES
            and bool(before.st_mode & 0o111) == (mode == "100755"),
            "Tracked file is nonregular, oversized or has an inconsistent Git mode",
        )
        total += before.st_size
        _require(total <= MAX_INVENTORY_TOTAL_BYTES, "Tracked repository exceeds total-byte bound")
        # This fixed data file never contributes to its own approval digest.
        # Matching separately requires its exact regular/tracked/pinned body.
        if name == MAP_PATH:
            continue
        head_body = _git("cat-file", "blob", blob.oid, maximum=blob.size)
        _require(len(head_body) == blob.size, "HEAD body was incomplete")
        normalized_head = _normalize_pin(head_body) if name == MODULE_PATH else head_body
        head_digest = _digest(normalized_head)
        head_sha256[name] = _digest(head_body)
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        digest = hashlib.sha256()
        raw_digest = hashlib.sha256()
        count = 0
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if name == MODULE_PATH:
                body = stream.read(MAX_INVENTORY_FILE_BYTES + 1)
                _require(len(body) <= MAX_INVENTORY_FILE_BYTES, "Matcher source grew beyond its bound")
                normalized = _normalize_pin(body)
                digest.update(normalized)
                raw_digest.update(body)
                count = len(normalized)
            else:
                while block := stream.read(1024 * 1024):
                    count += len(block)
                    _require(count <= MAX_INVENTORY_FILE_BYTES, "Tracked body grew beyond its bound")
                    digest.update(block)
                    raw_digest.update(block)
            after = os.fstat(stream.fileno())
        current = path.lstat()
        _require(
            _fingerprint(before) == _fingerprint(opened) == _fingerprint(after) == _fingerprint(current)
            and path.resolve(strict=True) == path,
            "Tracked body changed during inventory capture",
        )
        fingerprints[name] = _fingerprint(current)
        _require(
            before.st_size == blob.size and raw_digest.hexdigest() == head_sha256[name],
            "Working raw bytes overlay committed HEAD",
        )
        _require(
            count == len(normalized_head) and digest.hexdigest() == head_digest, "Working bytes overlay committed HEAD"
        )
        raw_sha256[name] = raw_digest.hexdigest()
        records.append((name, mode, count, digest.hexdigest()))
    _require(_tracked() == files, "Tracked path/mode inventory changed during capture")
    for name, fingerprint in fingerprints.items():
        path = _path(name)
        _require(
            path.resolve(strict=True) == path and _fingerprint(path.lstat()) == fingerprint,
            "Previously captured tracked body changed before inventory completed",
        )
    rows = tuple(records)
    return RepositoryInventory(
        rows,
        MappingProxyType(fingerprints),
        MappingProxyType(raw_sha256),
        MappingProxyType(head_sha256),
        _digest(_canonical(rows)),
    )


def _source(name: str, maximum: int = MAX_SOURCE_BYTES) -> tuple[bytes, SourceIdentity]:
    _require(ROOT.is_absolute() and ROOT.resolve(strict=True) == ROOT, "Source root is aliased")
    path = _path(name)
    _require(path.resolve(strict=True) == path, "Source or ancestor is a symlink")
    before = path.lstat()
    _require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "Source is nonregular or oversized")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        body = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    _require(
        len(body) <= maximum
        and _fingerprint(before) == _fingerprint(opened) == _fingerprint(after) == _fingerprint(current)
        and path.resolve(strict=True) == path,
        "Source changed during capture",
    )
    return body, SourceIdentity(_digest(body), _fingerprint(current), len(body))


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    start_byte: int
    end_byte: int
    sha256: str


@dataclass(frozen=True)
class CapturedInputs:
    targets: tuple[str, ...]
    sources: Mapping[str, SourceIdentity]
    official_pack: bytes
    rule_definitions: tuple[RuleDefinition, ...]
    repository: RepositoryInventory


def capture_inputs(
    targets: tuple[str, ...], official_pack: bytes, rule_definitions: tuple[RuleDefinition, ...]
) -> CapturedInputs:
    """Capture direct source identities; there is no root or policy-path override."""
    _require(bool(targets) and len(targets) == len(set(targets)), "Missing or duplicate selected sources")
    sources = {name: _source(name)[1] for name in targets}
    _require(sum(source.size for source in sources.values()) <= 32_000_000, "Source selection is oversized")
    return CapturedInputs(targets, MappingProxyType(sources), official_pack, rule_definitions, repository_inventory())


def _inputs(before: CapturedInputs, after: CapturedInputs) -> tuple[dict[str, bytes], dict[str, RuleDefinition]]:
    _require(before == after, "Source or official rules changed during scanning")
    _require(repository_inventory() == after.repository, "Tracked repository content changed after scanning")
    targets = before.targets
    _require(bool(targets) and len(targets) == len(set(targets)), "Missing or duplicate selected sources")
    _require(set(before.sources) == set(targets), "Source identities do not cover selected targets")
    bodies = {}
    for name in targets:
        body, identity = _source(name)
        _require(identity == before.sources[name], "Source no longer matches the completed scan")
        body.decode("utf-8")
        bodies[name] = body
    pack = before.official_pack
    _require(type(pack) is bytes and 0 < len(pack) <= MAX_PACK_BYTES, "Official rules are missing or oversized")
    rules = {}
    previous_end = 0
    for rule in before.rule_definitions:
        _require(
            type(rule.rule_id) is str
            and bool(rule.rule_id)
            and rule.rule_id not in rules
            and type(rule.start_byte) is int
            and type(rule.end_byte) is int
            and previous_end <= rule.start_byte < rule.end_byte <= len(pack),
            "Duplicate, missing or malformed rule definition",
        )
        _require(_digest(pack[rule.start_byte : rule.end_byte]) == rule.sha256, "Rule definition identity changed")
        rules[rule.rule_id] = rule
        previous_end = rule.end_byte
    _require(bool(rules), "Official rule definitions are missing")
    return bodies, rules


def _location(value: Any, body: bytes) -> dict[str, int]:
    _require(type(value) is dict and set(value) == {"line", "col", "offset"}, "Incomplete finding location")
    _require(all(type(number) is int for number in value.values()), "Finding positions must be integers")
    offset = value["offset"]
    _require(0 <= offset <= len(body), "Finding offset is outside its source")
    line = body.count(b"\n", 0, offset) + 1
    column = offset - (body.rfind(b"\n", 0, offset) + 1) + 1
    _require(value["line"] == line and value["col"] == column, "Finding line/byte-column disagrees with its offset")
    return cast(dict[str, int], value)


def _source_lines(body: bytes, start: dict[str, int], end: dict[str, int]) -> str:
    # Preserve the pinned1.99 formatter contract; raw span hashes stay exact.
    lines = itertools.islice(io.StringIO(body.decode("utf-8"), newline=None), start["line"] - 1, end["line"])
    return "".join(lines).rstrip()


def _findings(
    report: dict[str, Any], bodies: dict[str, bytes], rules: dict[str, RuleDefinition]
) -> list[dict[str, Any]]:
    identities = []
    seen = set()
    for finding in report["results"]:
        _require(type(finding) is dict, "Malformed finding")
        name, rule = finding.get("path"), finding.get("check_id")
        _require(
            type(name) is str and name in bodies and type(rule) is str and rule in rules, "Unknown finding source/rule"
        )
        body = bodies[name]
        start, end = _location(finding.get("start"), body), _location(finding.get("end"), body)
        _require(start["offset"] < end["offset"], "Empty or reversed finding span")
        snippet = body[start["offset"] : end["offset"]]
        snippet.decode("utf-8")
        extra = finding.get("extra")
        _require(
            type(extra) is dict
            and extra.get("is_ignored") is False
            and type(extra.get("lines")) is str
            and bool(extra["lines"]),
            "Ignored finding or missing reported source lines",
        )
        _require(
            extra["lines"] == _source_lines(body, start, end),
            "Reported finding lines disagree with the captured source",
        )
        identity = {
            "rule_id": rule,
            "rule_definition_sha256": rules[rule].sha256,
            "rule_start_byte": rules[rule].start_byte,
            "rule_end_byte": rules[rule].end_byte,
            "source_path": name,
            "source_sha256": _digest(body),
            "source_bytes": len(body),
            "start": start,
            "end": end,
            "snippet_sha256": _digest(snippet),
            "reported_lines_sha256": _digest(extra["lines"].encode("utf-8")),
        }
        key = _canonical(identity)
        _require(key not in seen, "Duplicate finding identity")
        seen.add(key)
        identities.append(identity)
    return identities


def _approved_map() -> tuple[dict[str, Any], str]:
    pin = APPROVED_MAP_SHA256
    _require(
        type(pin) is str and len(pin) == 64 and all(char in "0123456789abcdef" for char in pin),
        "Map has no reviewed pin",
    )
    assert isinstance(pin, str)
    blob = _tracked().get(MAP_PATH)
    _require(
        blob is not None and blob.mode == "100644" and blob.size <= MAX_MAP_BYTES,
        "Approved map must be committed regular bounded data",
    )
    assert blob is not None
    raw, identity = _source(MAP_PATH, MAX_MAP_BYTES)
    _require(identity.sha256 == pin, "Inapplicability map differs from its reviewed pin")
    _require(raw == _git("cat-file", "blob", blob.oid, maximum=blob.size), "Approved map overlays committed HEAD")
    return _json(raw, MAX_MAP_BYTES), pin


def _case_keys(cases: Any, bodies: dict[str, bytes], rules: dict[str, RuleDefinition]) -> set[bytes]:
    _require(type(cases) is list and bool(cases), "Variant has no reviewed cases")
    expected = set()
    for case in cases:
        _require(
            type(case) is dict
            and set(case) == {"identity", "rationale", "review_reference"}
            and type(case["identity"]) is dict
            and all(
                type(case[field]) is str and 0 < len(case[field]) <= 2000 for field in ("rationale", "review_reference")
            ),
            "Map case has no explicit review rationale/reference",
        )
        identity = case["identity"]
        _require(
            set(identity)
            == {
                "rule_id",
                "rule_definition_sha256",
                "rule_start_byte",
                "rule_end_byte",
                "source_path",
                "source_sha256",
                "source_bytes",
                "start",
                "end",
                "snippet_sha256",
                "reported_lines_sha256",
            },
            "Unknown or incomplete case identity",
        )
        _require(
            type(identity["rule_id"]) is str
            and identity["rule_id"] in rules
            and type(identity["source_path"]) is str
            and identity["source_path"] in bodies,
            "Case references an unknown source or rule",
        )
        for field in ("rule_definition_sha256", "source_sha256", "snippet_sha256", "reported_lines_sha256"):
            value = identity[field]
            _require(
                type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value),
                "Malformed case digest",
            )
        first, last = identity["rule_start_byte"], identity["rule_end_byte"]
        _require(
            type(first) is int and type(last) is int and 0 <= first < last <= MAX_PACK_BYTES, "Malformed case rule span"
        )
        body = bodies[identity["source_path"]]
        _require(
            type(identity["source_bytes"]) is int
            and identity["source_bytes"] == len(body)
            and identity["source_sha256"] == _digest(body),
            "Case source identity changed",
        )
        start, end = _location(identity["start"], body), _location(identity["end"], body)
        _require(
            start["offset"] < end["offset"]
            and identity["snippet_sha256"] == _digest(body[start["offset"] : end["offset"]])
            and identity["reported_lines_sha256"] == _digest(_source_lines(body, start, end).encode("utf-8")),
            "Case source span or reported lines changed",
        )
        key = _canonical(identity)
        _require(key not in expected, "Duplicate map case")
        expected.add(key)
    return expected


def assess(raw_report: bytes, raw_exit_code: int, before: CapturedInputs, after: CapturedInputs) -> dict[str, Any]:
    """Preserve raw scan status; every prerequisite fails before any map lookup."""
    decision: dict[str, Any] = {
        "schema": "agialpha.semgrep-inapplicability/v1",
        "raw_report_sha256": _digest(raw_report),
        "raw_exit_code": raw_exit_code,
        "raw_scan_passed": False,
        "raw_findings": None,
        "raw_finding_count": None,
        "policy_disposition": "REFUSED",
        "policy_accepted": False,
        "inapplicable_finding_count": 0,
        "production_authority": False,
        "release_authorized": False,
    }
    try:
        report = _json(raw_report, MAX_REPORT_BYTES)
        _require(type(report.get("results")) is list, "Missing findings")
        decision.update(raw_findings=report["results"], raw_finding_count=len(report["results"]))
        _require(report.get("version") == SEMGREP_VERSION, "Unqualified scanner version")
        _require(type(report.get("errors")) is list and report["errors"] == [], "Scanner errors or missing errors")
        _require(
            type(report.get("skipped_rules")) is list and report["skipped_rules"] == [], "Skipped or missing rules"
        )
        paths = report.get("paths")
        _require(type(paths) is dict, "Missing target coverage")
        assert isinstance(paths, dict)
        scanned = paths.get("scanned")
        _require(
            type(scanned) is list
            and all(type(name) is str for name in scanned)
            and len(scanned) == len(set(scanned)) == len(before.targets)
            and set(scanned) == set(before.targets)
            and paths.get("skipped", []) == [],
            "Incomplete, duplicate, unknown or skipped target coverage",
        )
        bodies, rules = _inputs(before, after)
        _require(type(raw_exit_code) is int and raw_exit_code in (0, 1), "Scanner did not finish normally")
        _require((raw_exit_code == 0) == (report["results"] == []), "Raw exit/findings inconsistency")
        _require(
            _digest(before.official_pack) in REVIEWABLE_PACK_SHA256S,
            "Actual pack is outside the finite reviewed representations",
        )
        if raw_exit_code == 0:
            decision.update(raw_scan_passed=True, policy_disposition="NOT_NEEDED_RAW_PASS", policy_accepted=True)
            return decision
        identities = _findings(report, bodies, rules)
        decision["finding_identities"] = identities
        decision["official_pack_sha256"] = _digest(before.official_pack)
        decision["repository_inventory_sha256"] = before.repository.sha256
        if APPROVED_MAP_SHA256 is None:
            decision.update(policy_disposition="INACTIVE", reason="No independently reviewed map or pin is installed")
            return decision
        approved, pin = _approved_map()
        _require(
            set(approved)
            == {
                "schema",
                "semgrep_version",
                "target_paths_sha256",
                "repository_inventory_sha256",
                "variants",
            }
            and approved["schema"] == "agialpha.semgrep-reviewed-inapplicability/v2"
            and approved["semgrep_version"] == SEMGREP_VERSION
            and approved["target_paths_sha256"] == _digest(_canonical(sorted(before.targets)))
            and approved["repository_inventory_sha256"] == before.repository.sha256,
            "Map schema, version, pack or target scope differs from the scan",
        )
        variants = approved["variants"]
        _require(type(variants) is list and len(variants) == 2, "Map must contain exactly two reviewed pack variants")
        by_pack = {}
        for variant in variants:
            _require(
                type(variant) is dict and set(variant) == {"official_pack_sha256", "cases"},
                "Malformed pack variant",
            )
            pack = variant["official_pack_sha256"]
            _require(
                type(pack) is str and pack in REVIEWABLE_PACK_SHA256S and pack not in by_pack,
                "Unknown or duplicate pack variant",
            )
            by_pack[pack] = _case_keys(variant["cases"], bodies, rules)
        _require(set(by_pack) == set(REVIEWABLE_PACK_SHA256S), "Reviewed pack variants are missing")
        actual_pack = _digest(before.official_pack)
        _require(actual_pack in by_pack, "Actual pack has no exact reviewed variant")
        _require(
            by_pack[actual_pack] == {_canonical(identity) for identity in identities},
            "Unknown, changed, missing or copied finding",
        )
        decision.update(
            policy_disposition="EXACT_REVIEWED_INAPPLICABILITY",
            policy_accepted=True,
            inapplicable_finding_count=len(identities),
            approved_map_sha256=pin,
        )
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as error:
        decision["reason"] = str(error) if isinstance(error, Refusal) else type(error).__name__
    return decision
