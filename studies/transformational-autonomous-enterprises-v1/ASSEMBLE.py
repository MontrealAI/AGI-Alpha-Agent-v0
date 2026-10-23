#!/usr/bin/env python3
"""Assemble the exact public companion archive; never execute its contents."""
from pathlib import Path
import hashlib
import sys
import urllib.request

PARTS = [('Successor_Omega_Harness_Companion.zip.part001', 8800000, '37c907d87a91711bd983be3f37ced616480bee6779f06df09e852de928706df4'), ('Successor_Omega_Harness_Companion.zip.part002', 8800000, '899c900a469896ac23815747b37c3156278bcac1f0bcf06a8a9b24f8138adb52'), ('Successor_Omega_Harness_Companion.zip.part003', 7171301, 'afba4d28c00f0be699bd6251bbea41578b4001f0a3c7d24608f46f353860f6a6')]
ARCHIVE = 'Successor_Omega_Harness_Companion.zip'
EXPECTED = 'a622657df828aefb4a081d1e0f5d1fb665fcf69991383245b6ece7cb66bee7ee'
BASE = "https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/research/writer4-transformational-enterprises-v1-20261023/studies/transformational-autonomous-enterprises-v1/"
root = Path(__file__).resolve().parent
if any(arg != "--download" for arg in sys.argv[1:]):
    raise SystemExit("Usage: python3 ASSEMBLE.py [--download]")
for name, size, digest in PARTS:
    path = root / name
    if not path.exists():
        if "--download" not in sys.argv:
            raise SystemExit(f"Missing {name}; use --download to fetch the declared public parts")
        print(f"Downloading {name} ({size:,} bytes)")
        request = urllib.request.Request(BASE + name, headers={"User-Agent": "Writer4-companion-assembler/1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(size + 1)
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit(f"Refused unexpected bytes for {name}; nothing executed")
        with path.open("xb") as stream:
            stream.write(data)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"Existing part differs: {name}; preserve it and use a new directory")
assembled = b"".join((root / name).read_bytes() for name, _, _ in PARTS)
if hashlib.sha256(assembled).hexdigest() != EXPECTED:
    raise SystemExit("Full archive digest mismatch")
target = root / ARCHIVE
if target.exists():
    if target.is_symlink() or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit("Existing archive differs; preserve it and use a new directory")
    print(f"Already assembled and verified: {target}")
else:
    with target.open("xb") as stream:
        stream.write(assembled)
    print(f"Assembled and verified: {target}")
print("Extract the ZIP, open its README, then verify and start the local demonstration. No archive content was executed.")
