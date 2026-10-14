# SPDX-License-Identifier: Apache-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_mark_wallet", ROOT / "scripts/build_mark_wallet.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProfileBuild(unittest.TestCase):
    def fixture(self, root):
        folder = root / "deployments/ethereum-mainnet/2026-10-11"
        folder.mkdir(parents=True)
        manifest = {
            "chainId": 1,
            "profile": "ascension-2026-10-11-solc-0.8.24",
            "contracts": {
                name: {"address": module.ADDRESSES[alias], "runtimeCodeHash": "0x" + "a" * 64}
                for alias, name in module.NAMES.items()
            },
        }
        (folder / "manifest.json").write_text(json.dumps(manifest))
        (folder / "runtime-code.json").write_text(json.dumps({name: "0x6000" for name in module.NAMES.values()}))
        return folder

    def test_build_is_deterministic_and_preserves_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = self.fixture(root)
            before = {p.name: p.read_bytes() for p in archive.iterdir()}
            output = module.build(root)
            first = output.read_bytes()
            self.assertEqual(first, module.build(root).read_bytes())
            self.assertEqual(before, {p.name: p.read_bytes() for p in archive.iterdir()})
            profile = json.loads(first)
            self.assertIs(profile["newExposureEnabled"], False)
            self.assertEqual(profile["contracts"]["Mark"]["sha256"], hashlib.sha256(bytes.fromhex("6000")).hexdigest())

    def test_rejects_changed_chain_address_and_empty_code(self):
        for corruption in ["chain", "address", "code"]:
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                archive = self.fixture(root)
                manifest = json.loads((archive / "manifest.json").read_text())
                if corruption == "chain":
                    manifest["chainId"] = 31337
                elif corruption == "address":
                    manifest["contracts"]["AscensionMark"]["address"] = "0x" + "0" * 40
                else:
                    runtime = json.loads((archive / "runtime-code.json").read_text())
                    runtime["AscensionMark"] = "0x"
                    (archive / "runtime-code.json").write_text(json.dumps(runtime))
                (archive / "manifest.json").write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    module.build(root)


if __name__ == "__main__":
    unittest.main()
