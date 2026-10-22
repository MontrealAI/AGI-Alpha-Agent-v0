# SPDX-License-Identifier: Apache-2.0
import hashlib
import pathlib
import subprocess
import unittest


class SelectedSourceTests(unittest.TestCase):
    def test_actual_newline_conversion_checkout_preserves_selected_tex_bytes(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        expected = "2d3481ebb3274f5f870cb3f445e6f6deca24ac6cd718ebd467186e40eb2fbc0d"
        for autocrlf, eol in [("false", "lf"), ("true", "crlf")]:
            result = subprocess.check_output(
                [
                    "git",
                    "-c",
                    "core.autocrlf=" + autocrlf,
                    "-c",
                    "core.eol=" + eol,
                    "checkout-index",
                    "--temp",
                    "--ignore-skip-worktree-bits",
                    "--",
                    "docs/Autonomous_Enterprises.tex",
                ],
                cwd=root,
                text=True,
            )
            temp = root / result.split("\t", 1)[0]
            try:
                self.assertEqual(hashlib.sha256(temp.read_bytes()).hexdigest(), expected)
            finally:
                temp.unlink()


if __name__ == "__main__":
    unittest.main()
