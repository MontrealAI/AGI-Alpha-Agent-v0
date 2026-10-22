# SPDX-License-Identifier: Apache-2.0
"""Immutable manuscript bytes survive Git's Windows-style text conversion."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PaperCheckoutBytesTests(unittest.TestCase):
    def assert_checkout_preserves(self, files: dict[str, bytes]) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-checkout-") as directory:
            root = Path(directory)

            def git(*args: str) -> bytes:
                env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
                env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
                return subprocess.check_output(
                    [
                        "git",
                        "-C",
                        str(root),
                        "-c",
                        "core.autocrlf=true",
                        "-c",
                        "core.safecrlf=false",
                        "-c",
                        f"core.hooksPath={os.devnull}",
                        *args,
                    ],
                    stderr=subprocess.PIPE,
                    timeout=30,
                    env=env,
                )

            git("init", "--quiet")
            (root / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
            for name, raw in files.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            git("add", "--all")
            for name, raw in files.items():
                with self.subTest(path=name, stage="index"):
                    self.assertEqual(git("show", ":" + name), raw)
                (root / name).unlink()
            git("checkout-index", "--force", "--all")
            for name, raw in files.items():
                with self.subTest(path=name, stage="checkout"):
                    self.assertEqual((root / name).read_bytes(), raw)

    def test_catalog_originals_keep_their_exact_hashes(self) -> None:
        catalog = json.loads((ROOT / "docs/research-papers.json").read_bytes())
        files = {}
        for paper in catalog["papers"]:
            source = paper["tex"]
            if source is not None:
                raw = (ROOT / source["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), source["sha256"])
                files[source["path"]] = raw
        self.assertTrue(files)
        self.assert_checkout_preserves(files)

    def test_opaque_uploads_preserve_both_lf_and_crlf(self) -> None:
        for newline in (b"\n", b"\r\n"):
            raw = newline.join((b"% Immutable original", b"\\section{Original}", b""))
            with self.subTest(newline=newline):
                self.assert_checkout_preserves(
                    {
                        "docs/Out_Learn.tex": raw,
                        "docs/Autonomous_Enterprises.tex": raw,
                        "docs/papers/versioned-original.tex": raw,
                    }
                )


if __name__ == "__main__":
    unittest.main()
