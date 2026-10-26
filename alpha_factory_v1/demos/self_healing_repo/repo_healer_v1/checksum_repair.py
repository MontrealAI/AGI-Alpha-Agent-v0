# SPDX-License-Identifier: Apache-2.0
"""Conservative checksum-before-write repair for the historical downloader shape.

This is a candidate generator, not a proof of correctness. The existing engine's
safety, targeted, broader and promotion gates remain mandatory. Unknown shapes
are intentionally unsupported; no complete-file fingerprint is used.
"""

from __future__ import annotations

import ast
from pathlib import Path

from .models import FailureBundle

_PATTERN = ast.parse(
    '''path.write_bytes(data)
key = label or path.name
expected = CHECKSUMS.get(key) or CHECKSUMS.get(path.name)
if expected:
    algo, ref = expected.split("-", 1)
    digest_bytes = getattr(hashlib, algo)(data).digest()
    calc_b64 = base64.b64encode(digest_bytes).decode()
    calc_hex = digest_bytes.hex()
    if ref == calc_b64 or ref.lower() == calc_hex:
        return
    raise RuntimeError(f"Checksum mismatch for {key}: expected {ref} got {calc_b64}")
'''
).body
_PATTERN_DUMPS = [ast.dump(node, include_attributes=False) for node in _PATTERN]


def transform_checksum_write_order(source: str) -> str | None:
    """Move only a structurally matched write onto checksum-success paths.

    Matching the entire straight-line window excludes mutations, side effects,
    different checksum semantics and unrelated returns inside the guard. Reject
    uncommon physical separators because downstream patch normalization does not
    preserve them. Preserve ordinary surrounding source and comments.
    """
    separators = ("\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")
    if any(separator in source for separator in separators):
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    lines = source.split("\n")
    offsets = [0]
    for line in lines[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)
    offsets.append(len(source))
    edits: list[tuple[int, int, str]] = []
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef):
            continue
        for index in range(len(function.body) - len(_PATTERN) + 1):
            window = function.body[index : index + len(_PATTERN)]
            if [ast.dump(node, include_attributes=False) for node in window] != _PATTERN_DUMPS:
                continue
            write, _, _, guard = window
            assert isinstance(guard, ast.If)
            valid = guard.body[-2]
            assert isinstance(valid, ast.If)
            returned = valid.body[0]
            assert isinstance(returned, ast.Return)
            if write.lineno != write.end_lineno or returned.lineno != returned.end_lineno:
                continue
            write_line = lines[write.lineno - 1]
            if write_line.strip() != ast.get_source_segment(source, write):
                continue
            if lines[returned.lineno - 1].strip() != "return":
                continue
            assert guard.end_lineno is not None
            write_indent = write_line[: len(write_line) - len(write_line.lstrip())]
            return_line = lines[returned.lineno - 1]
            return_indent = return_line[: len(return_line) - len(return_line.lstrip())]
            edits.extend(
                [
                    (write.lineno - 1, write.lineno, ""),
                    (returned.lineno - 1, returned.lineno - 1, return_indent + write_line.strip() + "\n"),
                    (guard.end_lineno, guard.end_lineno, write_indent + write_line.strip() + "\n"),
                ]
            )
    if not edits:
        return None
    updated = source
    for start, end, replacement in sorted(edits, reverse=True):
        updated = updated[: offsets[start]] + replacement + updated[offsets[end] :]
    try:
        ast.parse(updated)
    except SyntaxError:
        return None
    return updated


def repair_checksum_write_order(repo: Path, bundle: FailureBundle) -> bool:
    """Mutate the engine-owned candidate copy, only on explicit checksum evidence."""
    if "checksum" not in bundle.logs.lower():
        return False
    changed = False
    for name in bundle.candidate_files:
        path = repo / name
        if path.suffix != ".py" or not path.is_file():
            continue
        # Read bytes to avoid silently normalizing unsupported CRLF sources.
        try:
            original = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue
        updated = transform_checksum_write_order(original)
        if updated is not None and updated != original:
            path.write_text(updated, encoding="utf-8")
            changed = True
    return changed
