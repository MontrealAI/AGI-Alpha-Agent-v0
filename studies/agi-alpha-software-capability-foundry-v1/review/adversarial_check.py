# SPDX-License-Identifier: Apache-2.0
"""Independent development checks for the bounded exact-commit reader contract."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zlib


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        timeout=20,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Independent development checker",
            "GIT_AUTHOR_EMAIL": "checker@example.invalid",
            "GIT_COMMITTER_NAME": "Independent development checker",
            "GIT_COMMITTER_EMAIL": "checker@example.invalid",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        },
    )
    return result.stdout


def check(reader) -> dict:
    rows = []

    def expect(name, function, output=None, refusal=False):
        try:
            result = function()
            passed = not refusal and result == output
            rows.append({"name": name, "passed": passed, "observed": "returned"})
        except Exception as error:
            rows.append({"name": name, "passed": refusal, "observed": type(error).__name__})

    with tempfile.TemporaryDirectory(prefix="foundry-independent-development-") as temporary:
        repo = Path(temporary)
        git(repo, "init", "--quiet", "--object-format=sha1", "-b", "development")
        files = {
            "empty": b"",
            "nested/binary": bytes(range(256)) * 3,
            "étude/file with spaces": b"public unicode path\n",
            "executable": b"#!/bin/sh\nprintf 'public fixture\\n'\n",
            "-leading": b"same bytes\n",
            "duplicate": b"same bytes\n",
            "attribute.txt": b"$Format:%H$\n",
            ".gitattributes": b"attribute.txt export-subst\n",
        }
        for name, body in files.items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        (repo / "executable").chmod(0o755)
        (repo / "symbolic").symlink_to("empty")
        git(repo, "add", "--all")
        git(repo, "commit", "--quiet", "-m", "Reader development edge cases")
        original = git(repo, "rev-parse", "HEAD").decode().strip()
        git(repo, "update-index", "--add", "--cacheinfo", f"160000,{original},vendor/submodule")
        git(repo, "commit", "--quiet", "-m", "Add a deliberately unsupported gitlink")
        commit = git(repo, "rev-parse", "HEAD").decode().strip()
        tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
        git(repo, "tag", "-a", "annotated", "-m", "Development annotated tag", commit)
        tag = git(repo, "rev-parse", "annotated").decode().strip()
        (repo / "duplicate").write_bytes(b"uncommitted working tree mutation\n")
        names = list(files)
        expect("all-supported-bytes-and-executable", lambda: reader(repo, commit, names), files)
        expect("empty-file-zero-limit", lambda: reader(repo, commit, ["empty"], max_file=0, total=0), {"empty": b""})
        expect("fresh-read-ignores-mutated-working-tree", lambda: reader(repo, commit, ["duplicate"]), {"duplicate": files["duplicate"]})
        expect("retains-export-subst-literal-bytes", lambda: reader(repo, commit, ["attribute.txt"]), {"attribute.txt": files["attribute.txt"]})
        for label, identity, paths, kwargs in [
            ("reject-mutable-reference", "HEAD", ["empty"], {}),
            ("reject-tree-as-commit", tree, ["empty"], {}),
            ("reject-tag-as-commit", tag, ["empty"], {}),
            ("reject-missing-commit", "0" * 40, ["empty"], {}),
            ("reject-missing-path", commit, ["does-not-exist"], {}),
            ("reject-symlink", commit, ["symbolic"], {}),
            ("reject-gitlink", commit, ["vendor/submodule"], {}),
            ("reject-directory", commit, ["nested"], {}),
            ("reject-duplicate-request", commit, ["empty", "empty"], {}),
            ("reject-empty-request", commit, [], {}),
            ("reject-too-many-paths", commit, [f"x-{i}" for i in range(257)], {}),
            ("reject-parent-traversal", commit, ["../empty"], {}),
            ("reject-absolute-path", commit, ["/empty"], {}),
            ("reject-normalized-dot", commit, ["./empty"], {}),
            ("reject-repeated-separator", commit, ["nested//binary"], {}),
            ("reject-backslash", commit, ["nested\\binary"], {}),
            ("reject-newline", commit, ["empty\n"], {}),
            ("reject-carriage-return", commit, ["empty\r"], {}),
            ("reject-NUL", commit, ["empty\0"], {}),
            ("reject-file-over-budget", commit, ["nested/binary"], {"max_file": 767}),
            ("reject-total-over-budget", commit, ["-leading", "duplicate"], {"total": 21}),
            ("reject-negative-limit", commit, ["empty"], {"total": -1}),
            ("reject-bool-limit", commit, ["empty"], {"max_file": True}),
        ]:
            expect(label, lambda identity=identity, paths=paths, kwargs=kwargs: reader(repo, identity, paths, **kwargs), refusal=True)
        (repo / "duplicate").write_bytes(b"committed replacement bytes\n")
        git(repo, "add", "duplicate")
        git(repo, "commit", "--quiet", "-m", "Different commit for a local replace ref")
        replacement = git(repo, "rev-parse", "HEAD").decode().strip()
        git(repo, "replace", commit, replacement)
        expect("ignores-git-replace-ref", lambda: reader(repo, commit, ["duplicate"]), {"duplicate": files["duplicate"]})
        git(repo, "replace", "--delete", commit)
        blob = git(repo, "rev-parse", commit + ":duplicate").decode().strip()
        loose = repo / ".git" / "objects" / blob[:2] / blob[2:]
        corrupt = b"X" * len(files["duplicate"])
        loose.chmod(0o644)
        loose.write_bytes(zlib.compress(f"blob {len(corrupt)}\0".encode() + corrupt))
        expect("reject-corrupted-object-identity", lambda: reader(repo, commit, ["duplicate"]), refusal=True)
    return {"schema": "foundry-independent-development/v1", "passed": all(row["passed"] for row in rows), "checks": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    spec = importlib.util.spec_from_file_location("independently_checked_reader", arguments.module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = check(module.read)
    rendered = json.dumps(result, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(rendered)
    print(rendered)
    raise SystemExit(0 if result["passed"] else 1)
