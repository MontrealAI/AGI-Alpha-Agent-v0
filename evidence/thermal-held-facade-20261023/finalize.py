# SPDX-License-Identifier: Apache-2.0
"""Retain source identities and package data-only evidence, excluding held code and keys."""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
CHECKOUT = ROOT / "checkout"
START = dt.datetime.now(dt.timezone.utc).isoformat()
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
commands = []


def git(*args: str) -> str:
    argv = ["git", *args]
    result = subprocess.run(argv, cwd=CHECKOUT, env=ENV, capture_output=True, text=True, check=False)
    commands.append({"argv": argv, "cwd": str(CHECKOUT), "exit": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def write(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


result = json.loads((ROOT / "result.json").read_text())
assert result["status"] == "PASS_WITH_EXPECTED_STUDIO_REJECTION"
assert result["runnerSha256"] == hashlib.sha256((ROOT / "probe.py").read_bytes()).hexdigest()
assert result["criteriaSha256"] == hashlib.sha256((ROOT / "criteria.json").read_bytes()).hexdigest()
commits = {}
for commit in (result["candidate"], result["heldHead"], "c455ad4ce109c86df2fef09d19674810290b5185",
               "0a668817284fed9010ad71ce405dbd5906ef2b28"):
    lines = git("show", "--no-patch", "--format=%H%n%T%n%P", commit).splitlines()
    commits[commit] = {"commit": lines[0], "tree": lines[1], "parents": lines[2].split()}
source = json.loads((ROOT / "logs/composed-source-identity.stdout").read_text())
tree = git("write-tree")
assert tree == result["prospectiveTree"]
assert git("diff", "--name-only") == "" and git("ls-files", "--unmerged") == ""
assert git("rev-parse", "HEAD") == result["candidate"]
assert git("rev-parse", "MERGE_HEAD") == result["heldHead"]
for path, expected in source["files"].items():
    assert hashlib.sha256((CHECKOUT / path).read_bytes()).hexdigest() == expected["sha256"]
composition = {
    "schema": "thermal-held-facade-source-composition/v1",
    "recordedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    "commits": commits, "compositionTree": tree,
    "prospectiveParents": [result["candidate"], result["heldHead"]],
    "commonBase": "0a668817284fed9010ad71ce405dbd5906ef2b28",
    "gitState": "Uncommitted conflict-free prospective merge; detached HEAD and MERGE_HEAD retained",
    "fetchDepth": 128, "commonAncestryPresent": True, "sourceFiles": source["files"],
    "trackedWorktreeEdits": [], "unmergedPaths": [], "heldModulesMatchExactPublicHead": True,
    "remoteRefMutations": [], "publication": False, "reviewRestrictionCleared": False,
    "sourceIdentityCommands": commands,
}
write(ROOT / "composition.json", composition)
with (ROOT / "commands.jsonl").open("a") as stream:
    stream.write(json.dumps({"label": "finalize-evidence", "startedAt": START,
                            "recordedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "argv": [sys.executable, "-I", "-B", str(Path(__file__).resolve())],
                            "cwd": str(ROOT), "scope": "Metadata and archive creation; no decisive rerun",
                            "sourceIdentityCommands": "composition.json"}, sort_keys=True) + "\n")
paths = sorted(path for path in ROOT.rglob("*")
               if path.is_file() and path.relative_to(ROOT).parts[0] not in {"checkout", "private-homes"}
               and path.name != "evidence-index.json")
index = {
    "schema": "thermal-held-facade-evidence-index/v1",
    "excluded": {"checkout": "Held source, local only", "private-homes": "Disposable private test journal keys"},
    "files": {str(path.relative_to(ROOT)): {"bytes": path.stat().st_size,
                                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
              for path in paths},
}
write(ROOT / "evidence-index.json", index)
paths.append(ROOT / "evidence-index.json")
archive = ROOT.parent / (ROOT.name + "-evidence.tar.gz")
with archive.open("xb") as target, gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
    with tarfile.open(fileobj=compressed, mode="w") as bundle:
        for path in sorted(paths):
            body = path.read_bytes()
            entry = tarfile.TarInfo(ROOT.name + "/" + str(path.relative_to(ROOT)))
            entry.size, entry.mode, entry.mtime = len(body), 0o644, 0
            bundle.addfile(entry, io.BytesIO(body))
print(json.dumps({"archive": str(archive), "archiveBytes": archive.stat().st_size,
                  "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                  "evidenceFiles": len(paths), "indexedFiles": len(index["files"]),
                  "resultSha256": hashlib.sha256((ROOT / "result.json").read_bytes()).hexdigest(),
                  "compositionSha256": hashlib.sha256((ROOT / "composition.json").read_bytes()).hexdigest(),
                  "indexSha256": hashlib.sha256((ROOT / "evidence-index.json").read_bytes()).hexdigest()}, sort_keys=True))
