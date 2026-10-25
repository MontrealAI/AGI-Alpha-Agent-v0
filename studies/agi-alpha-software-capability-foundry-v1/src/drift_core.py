# SPDX-License-Identifier: Apache-2.0
"""Diagnose complete archive drift; never extract or repair source files."""
from __future__ import annotations
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile

def compare(files: dict[str, bytes], archive: Path, max_file: int = 8_000_000,
            total: int = 32_000_000) -> dict:
    """Return all changed/missing/extra paths after bounded archive qualification."""
    info = archive.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > total + 1_048_576:
        raise ValueError("Archive must be a bounded regular file")
    fd = os.open(archive, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError("Archive changed during capture")
        raw = stream.read(total + 1_048_577)
        after = os.fstat(stream.fileno())
        if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("Archive changed while being read")
    if len(raw) > total + 1_048_576:
        raise ValueError("Archive grew beyond its bound")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        rows = z.infolist()
        if len(rows) > 256 or len({i.filename for i in rows}) != len(rows):
            raise ValueError("Archive inventory invalid")
        if sum(i.file_size for i in rows) > total:
            raise ValueError("Archive expansion exceeds its bound")
        captured = {}
        for i in rows:
            p = PurePosixPath(i.filename)
            if (not i.filename or p.as_posix() != i.filename or p.is_absolute()
                or any(q in {"", ".", ".."} for q in i.filename.split("/"))
                or any(q in i.filename for q in "\\\x00\n\r") or i.is_dir()
                or i.orig_filename != i.filename or i.external_attr & 0x10
                or stat.S_IFMT(i.external_attr >> 16) not in {0, stat.S_IFREG}
                or i.flag_bits & 1 or i.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                or i.file_size > max_file):
                raise ValueError("Unsupported archive member")
            body = z.read(i)
            if len(body) != i.file_size:
                raise ValueError("Archive size mismatch")
            captured[i.filename] = body
    return {"missing": sorted(files.keys() - captured.keys()), "extra": sorted(captured.keys() - files.keys()),
            "changed": sorted(p for p in files.keys() & captured.keys() if files[p] != captured[p]),
            "archive_sha256": hashlib.sha256(raw).hexdigest(), "checked_members": len(captured)}
