# SPDX-License-Identifier: Apache-2.0
"""Independent development checks for archive-versus-commit diagnosis."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import warnings
import zipfile

from adversarial_check import git


def _archive(path: Path, files: dict[str, bytes], compression=zipfile.ZIP_STORED) -> None:
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, body in files.items():
            archive.writestr(name, body)


def check(diagnose) -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="foundry-child-development-") as temporary:
        root = Path(temporary)
        repo = root / "repository"
        repo.mkdir()
        git(repo, "init", "--quiet", "--object-format=sha1", "-b", "development")
        files = {"alpha.txt": b"alpha source\n", "nested/beta.bin": bytes(range(64)), "empty": b""}
        for name, body in files.items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        git(repo, "add", "--all")
        git(repo, "commit", "--quiet", "-m", "Independent child qualification fixture")
        commit = git(repo, "rev-parse", "HEAD").decode().strip()
        names = list(files)

        def expect(name, path, output=None, refusal=False, **kwargs):
            try:
                result = diagnose(repo, commit, names, path, **kwargs)
                comparable = {key: result[key] for key in ("changed", "missing", "extra")}
                rows.append({"name": name, "passed": not refusal and comparable == output, "observed": "returned"})
            except Exception as error:
                rows.append({"name": name, "passed": refusal, "observed": type(error).__name__})

        clean = {"changed": [], "missing": [], "extra": []}
        good = root / "good.zip"
        _archive(good, files)
        expect("clean-package", good, clean)
        changed = root / "changed.zip"
        _archive(changed, {"alpha.txt": b"changed\n", "nested/beta.bin": files["nested/beta.bin"], "unexpected": b"extra\n"})
        expect("complete-changed-missing-extra-diagnosis", changed, {"changed": ["alpha.txt"], "missing": ["empty"], "extra": ["unexpected"]})
        deflated = root / "deflated.zip"
        _archive(deflated, files, zipfile.ZIP_DEFLATED)
        expect("deflated-package-retains-correctness", deflated, clean)
        traversal = root / "traversal.zip"
        _archive(traversal, {"../escape": b"no extraction is permitted"})
        expect("reject-path-traversal", traversal, refusal=True)
        duplicate = root / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(duplicate, "w") as archive:
                archive.writestr("alpha.txt", b"one")
                archive.writestr("alpha.txt", b"two")
        expect("reject-duplicate-members", duplicate, refusal=True)
        symlink = root / "symlink-member.zip"
        with zipfile.ZipFile(symlink, "w") as archive:
            member = zipfile.ZipInfo("linked")
            member.create_system = 3
            member.external_attr = 0o120777 << 16
            archive.writestr(member, "alpha.txt")
        expect("reject-symlink-member", symlink, refusal=True)
        directory = root / "directory.zip"
        _archive(directory, {"directory/": b""})
        expect("reject-directory-member", directory, refusal=True)
        expect("reject-member-over-budget", good, refusal=True, max_file=63)
        expect("reject-total-over-budget", good, refusal=True, total=76)
        encrypted = root / "encrypted.zip"
        raw = bytearray(good.read_bytes())
        for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
            start = raw.find(signature)
            flags = struct.unpack_from("<H", raw, start + flag_offset)[0]
            struct.pack_into("<H", raw, start + flag_offset, flags | 1)
        encrypted.write_bytes(raw)
        expect("reject-encrypted-member", encrypted, refusal=True)
        bad_crc = root / "bad-crc.zip"
        raw = bytearray(good.read_bytes())
        position = raw.index(files["alpha.txt"])
        raw[position] ^= 1
        bad_crc.write_bytes(raw)
        expect("reject-wrong-CRC", bad_crc, refusal=True)
        truncated = root / "truncated.zip"
        truncated.write_bytes(good.read_bytes()[:-17])
        expect("reject-truncated-archive", truncated, refusal=True)
        linked_archive = root / "linked-archive.zip"
        linked_archive.symlink_to(good.name)
        expect("reject-symlink-archive", linked_archive, refusal=True)
        too_many = root / "too-many.zip"
        _archive(too_many, {f"file-{number}": b"" for number in range(257)})
        expect("reject-too-many-members", too_many, refusal=True)
        backslash = root / "backslash.zip"
        _archive(backslash, {"directory\\escape": b"noncanonical"})
        expect("reject-backslash-member", backslash, refusal=True)
        empty = root / "empty.zip"
        _archive(empty, {})
        expect("empty-package-reports-every-required-file-missing", empty, {"changed": [], "missing": sorted(files), "extra": []})
        dos_directory = root / "dos-directory.zip"
        with zipfile.ZipFile(dos_directory, "w") as archive:
            member = zipfile.ZipInfo("directory-without-slash")
            member.external_attr = (0o100644 << 16) | 0x10
            archive.writestr(member, b"")
        expect("reject-DOS-directory-member", dos_directory, refusal=True)
        nul_name = root / "NUL-member.zip"
        _archive(nul_name, {"alphaXtxt": b"noncanonical"})
        nul_name.write_bytes(nul_name.read_bytes().replace(b"alphaXtxt", b"alpha\0txt"))
        expect("reject-NUL-before-ZipInfo-truncation", nul_name, refusal=True)
        original_fdopen = os.fdopen
        archive_inode = good.stat().st_ino

        class ChangedCapture:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def fileno(self):
                return self.stream.fileno()

            def read(self, *args):
                body = self.stream.read(*args)
                observed = good.stat()
                os.utime(good, ns=(observed.st_atime_ns, observed.st_mtime_ns + 10_000_000))
                return body

        def injected_fdopen(descriptor, *args, **kwargs):
            stream = original_fdopen(descriptor, *args, **kwargs)
            return ChangedCapture(stream) if os.fstat(stream.fileno()).st_ino == archive_inode else stream

        try:
            os.fdopen = injected_fdopen
            expect("reject-detected-mutation-during-capture", good, refusal=True)
        finally:
            os.fdopen = original_fdopen
    return {"schema": "foundry-independent-child-development/v1", "passed": all(row["passed"] for row in rows), "checks": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--function", default="direct_diagnose")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    spec = importlib.util.spec_from_file_location("independently_checked_diagnoser", arguments.module)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    result = check(getattr(module, arguments.function))
    rendered = json.dumps(result, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(rendered)
    print(rendered)
    raise SystemExit(0 if result["passed"] else 1)
