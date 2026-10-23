# SPDX-License-Identifier: Apache-2.0
"""Create and verify a separate companion copy with the reviewed runtime corrections."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request

ARCHIVE_SHA256 = "a622657df828aefb4a081d1e0f5d1fb665fcf69991383245b6ece7cb66bee7ee"
MANIFEST_SHA256 = "c7f6b7fa6c0ef674106d6428e675fd4a91bdb0c61391f2251852e9fab1f8cdb4"
ORIGINAL_QUEUE_SHA256 = "6569a7fd1d749283f5959343465bc41c812f36446ec16266016042120e46878a"
ORIGINAL_REPLACEMENTS = {
    "study/evaluation/queue.mjs": ORIGINAL_QUEUE_SHA256,
    "study/integration/mission-delivery.mjs": "8346eed178d93a96a445b4bf5ea5c0b1921fe2807d0cb9371325dc2c5f11439f",
    "study/interface/app.js": "55c99dc57a7e23f9a238cfda1830ca94090646115fef3f67fb23c716a4367e66",
}
OVERRIDES = {
    "study/evaluation/queue.mjs": "f9d637b607a31c16160254659f6a29cd262373c4201d65a5aba570b48475ea80",
    "study/evaluation/queue-input.test.mjs": "1a47f6004e395f99e375a920b663c5c41563aff8ad0ce5c402eca6a765c58d7e",
    "study/integration/mission-delivery.mjs": "14f46a110f182b462963fb39619c9dcd3a87a2f24a9e0b92b842b7a4ad20ea68",
    "study/integration/execution-identity.test.mjs": "1eb36919630bac62eb7d4e96456abbb440480cddb95dde32a88599fdcadfc4cb",
    "study/integration/bridge-lifecycle.test.mjs": "e7109d59dcafe8a29b3f7498fa805f4876f3b586ab80ee8dc00dc8e80149fe3d",
    "study/interface/app.js": "003d2eac0966ce7425f8a690bccbbe6e776957e4a4c347628d1a49e5cb57101c",
    "study/interface/status.test.mjs": "efc671d0c998d7843a88be38e264880f655ddf7ed6baa71f9f0ae067e6f539d3",
}
OVERLAY_COMMIT = "aaf2074de0c3df4dda27547468d5a57efb3ac39a"
BASE = (
    "https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/"
    + OVERLAY_COMMIT
    + "/studies/transformational-autonomous-enterprises-v1/"
)
RECEIPT = "QUEUE_INPUT_OVERLAY.json"


def digest(raw: bytes) -> str:
    """Return the exact byte digest."""
    return hashlib.sha256(raw).hexdigest()


def read_regular(root: Path, relative: str) -> bytes:
    """Read a bounded regular leaf without following a link inside the copy."""
    parts = PurePosixPath(relative).parts
    if not parts or relative.startswith("/") or any(part in (".", "..") for part in parts):
        raise ValueError("Unsafe companion member path")
    leaf = root.joinpath(*parts)
    if leaf.is_symlink() or not leaf.is_file() or leaf.resolve() != leaf or leaf.stat().st_size > 32_000_000:
        raise ValueError("Missing, linked or oversized companion member: " + relative)
    raw = leaf.read_bytes()
    if len(raw) > 32_000_000:
        raise ValueError("Companion member exceeded its bound: " + relative)
    return raw


def original_inventory(root: Path) -> tuple[bytes, dict[str, str]]:
    """Authenticate the frozen archive manifest before using its member names."""
    raw = read_regular(root, "MANIFEST.sha256")
    if digest(raw) != MANIFEST_SHA256:
        raise ValueError("Original companion manifest differs; no output created")
    entries = {}
    for line in raw.decode("utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        if relative in entries:
            raise ValueError("Duplicate manifest member")
        entries[relative] = expected
    if len(entries) != 457 or any(entries.get(name) != expected for name, expected in ORIGINAL_REPLACEMENTS.items()):
        raise ValueError("Original companion inventory differs")
    return raw, entries


def override_bytes(download: bool) -> dict[str, bytes]:
    """Use pinned local corrections or explicitly selected anonymous public reads."""
    root = Path(__file__).resolve().parent
    result = {}
    for relative, expected in OVERRIDES.items():
        if root.joinpath(relative).exists() or root.joinpath(relative).is_symlink():
            raw = read_regular(root, relative)
        elif download:
            request = urllib.request.Request(BASE + relative, headers={"User-Agent": "Companion-queue-overlay/1"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200 or response.url != BASE + relative:
                    raise ValueError("Pinned public correction returned an unexpected response")
                raw = response.read(100_001)
        else:
            raise ValueError("Missing correction file: " + relative + "; use --download or retain the study files")
        if len(raw) > 100_000 or digest(raw) != expected:
            raise ValueError("Correction bytes differ: " + relative)
        result[relative] = raw
    return result


def verify_overlay(root: Path) -> dict[str, object]:
    """Verify the derived source against the frozen inventory and pinned overlay."""
    root = root.resolve(strict=True)
    _, entries = original_inventory(root)
    receipt = json.loads(read_regular(root, RECEIPT))
    if receipt != overlay_receipt():
        raise ValueError("Derived overlay receipt differs")
    expected = entries | OVERRIDES
    for relative, sha256 in expected.items():
        if digest(read_regular(root, relative)) != sha256:
            raise ValueError("Derived source differs: " + relative)
    return {"verified": True, "originalManifestMembers": 457, "derivedMembersChecked": len(expected), "receipt": receipt}


def overlay_receipt() -> dict[str, object]:
    """Describe the separate source epoch without relabeling frozen evidence."""
    return {
        "schema": "tae.research-runtime-overlay.v4",
        "originalArchiveSha256": ARCHIVE_SHA256,
        "originalManifestSha256": MANIFEST_SHA256,
        "originalQueueSha256": ORIGINAL_QUEUE_SHA256,
        "originalReplacedFiles": ORIGINAL_REPLACEMENTS,
        "correctionSourceCommit": OVERLAY_COMMIT,
        "overrides": OVERRIDES,
        "originalManifestIsHistorical": True,
        "scope": "Derived queue, admission, input, bridge lifecycle and UI status corrections; frozen scores unchanged",
        "installedFourRepositoryAcceptance": False,
        "authority": [],
    }


def apply_overlay(source: Path, output: Path, *, download: bool = False) -> dict[str, object]:
    """Capture verified source and create a new copy; never edit the input tree."""
    source = source.resolve(strict=True)
    output = output.absolute()
    output = output.parent.resolve(strict=True) / output.name
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; previous copies are preserved")
    if source == output or source in output.parents:
        raise ValueError("The derived copy must be outside the original companion")
    manifest, inventory = original_inventory(source)
    captured = {}
    for relative, expected in inventory.items():
        raw = read_regular(source, relative)
        if digest(raw) != expected:
            raise ValueError("Original source differs: " + relative + "; no output created")
        captured[relative] = raw
    captured["MANIFEST.sha256"] = manifest
    captured.update(override_bytes(download))
    output.mkdir(mode=0o700)
    for relative, raw in captured.items():
        leaf = output / relative
        leaf.parent.mkdir(parents=True, exist_ok=True)
        with leaf.open("xb") as stream:
            stream.write(raw)
    with (output / RECEIPT).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(overlay_receipt(), indent=2) + "\n")
    return verify_overlay(output)


def main() -> None:
    """Apply to a separate copy, or verify a previously derived copy."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify and (args.output is not None or args.download):
        parser.error("--verify accepts only the derived source directory")
    if not args.verify and args.output is None:
        parser.error("Supply original and separate derived directories")
    result = verify_overlay(args.source) if args.verify else apply_overlay(args.source, args.output, download=args.download)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
