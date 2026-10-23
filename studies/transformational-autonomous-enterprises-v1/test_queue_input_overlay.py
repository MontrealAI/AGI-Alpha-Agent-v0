# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual overlay against an extracted frozen companion fixture."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("queue_overlay", Path(__file__).with_name("APPLY_QUEUE_INPUT_FIX.py"))
assert spec is not None and spec.loader is not None
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)
SOURCE: Path | None = None


class OverlayTests(unittest.TestCase):
    """Use real manifest and source bytes, keeping the frozen source untouched."""

    def setUp(self) -> None:
        """Allocate an isolated derived output parent."""
        if SOURCE is None:
            self.skipTest("Supply the extracted frozen companion fixture to run these explicit overlay checks")
        self.source = SOURCE
        self.temp = tempfile.TemporaryDirectory(prefix="tae-overlay-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        """Remove only this test's disposable outputs."""
        self.temp.cleanup()

    def test_apply_verify_and_repeat_refusal(self) -> None:
        """The real overlay preserves input and refuses a repeated destination."""
        before = overlay.digest((self.source / "study/evaluation/queue.mjs").read_bytes())
        target = self.root / "derived"
        result = overlay.apply_overlay(self.source, target)
        self.assertTrue(result["verified"])
        self.assertEqual(result["derivedMembersChecked"], 460)
        self.assertEqual(overlay.digest((self.source / "study/evaluation/queue.mjs").read_bytes()), before)
        self.assertEqual(before, overlay.ORIGINAL_QUEUE_SHA256)
        self.assertEqual(overlay.verify_overlay(target), result)
        with self.assertRaisesRegex(ValueError, "Output already exists"):
            overlay.apply_overlay(self.source, target)
        self.assertEqual(overlay.verify_overlay(target), result)

    def test_tampered_source_refused_before_output(self) -> None:
        """A changed original queue cannot be silently adopted."""
        source = self.root / "source"
        shutil.copytree(self.source, source)
        queue = source / "study/evaluation/queue.mjs"
        queue.write_bytes(queue.read_bytes() + b"\n// altered original\n")
        target = self.root / "derived"
        with self.assertRaisesRegex(ValueError, "Original source differs"):
            overlay.apply_overlay(source, target)
        self.assertFalse(target.exists())

    def test_derived_tamper_and_receipt_tamper_refused(self) -> None:
        """Verification binds both installed queue bytes and the source receipt."""
        target = self.root / "derived"
        overlay.apply_overlay(self.source, target)
        queue = target / "study/evaluation/queue.mjs"
        raw = queue.read_bytes()
        queue.write_bytes(raw + b"\n// altered derived\n")
        with self.assertRaisesRegex(ValueError, "Derived source differs"):
            overlay.verify_overlay(target)
        queue.write_bytes(raw)
        (target / overlay.RECEIPT).write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "receipt differs"):
            overlay.verify_overlay(target)

    def test_wrong_local_override_is_not_downloaded_or_installed(self) -> None:
        """A tampered present override is refused rather than replaced by a read."""
        helper = self.root / "tooling"
        helper.mkdir()
        shutil.copy2(Path(overlay.__file__), helper / "APPLY_QUEUE_INPUT_FIX.py")
        queue = helper / "study/evaluation/queue.mjs"
        queue.parent.mkdir(parents=True)
        queue.write_bytes(b"wrong bytes\n")
        original_file = overlay.__file__
        overlay.__file__ = str(helper / "APPLY_QUEUE_INPUT_FIX.py")
        try:
            with self.assertRaisesRegex(ValueError, "Correction bytes differ"):
                overlay.override_bytes(download=True)
        finally:
            overlay.__file__ = original_file

    def test_parent_alias_into_original_is_refused_without_source_changes(self) -> None:
        """A linked output parent cannot place the derived copy inside its input."""
        alias = self.root / "original-alias"
        alias.symlink_to(self.source, target_is_directory=True)
        name = "forbidden-derived-" + self.root.name
        output = alias / name
        before = {str(path.relative_to(self.source)) for path in self.source.rglob("*")}
        manifest_before = (self.source / "MANIFEST.sha256").read_bytes()
        with self.assertRaisesRegex(ValueError, "outside the original companion"):
            overlay.apply_overlay(self.source, output)
        self.assertFalse(output.exists())
        self.assertFalse((self.source / name).exists())
        self.assertEqual({str(path.relative_to(self.source)) for path in self.source.rglob("*")}, before)
        self.assertEqual((self.source / "MANIFEST.sha256").read_bytes(), manifest_before)

    def test_every_runtime_correction_is_installed_and_originals_remain_exact(self) -> None:
        """Every declared runtime fix and regression reaches the complete derived copy."""
        target = self.root / "all-corrections"
        overlay.apply_overlay(self.source, target)
        for relative, expected in overlay.OVERRIDES.items():
            with self.subTest(derived=relative):
                self.assertEqual(overlay.digest((target / relative).read_bytes()), expected)
        for relative, expected in overlay.ORIGINAL_REPLACEMENTS.items():
            with self.subTest(original=relative):
                self.assertEqual(overlay.digest((self.source / relative).read_bytes()), expected)
        receipt = overlay.verify_overlay(target)["receipt"]
        self.assertEqual(receipt["schema"], "tae.research-runtime-overlay.v3")
        self.assertEqual(len(receipt["overrides"]), 5)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 test_queue_input_overlay.py <original-extracted-companion>")
    SOURCE = Path(sys.argv.pop(1)).resolve()
    unittest.main()
