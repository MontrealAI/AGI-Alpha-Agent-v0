# SPDX-License-Identifier: Apache-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
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

    def local_profile(self):
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                "const p=await import(process.argv[1]);process.stdout.write(p.protocolIdentity());",
                (ROOT / "docs/assets/ascension-wallet/protocol.mjs").as_uri(),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return {
            "schema": "agialpha.nova-local-profile.v1",
            "profile": "local-source-fixture",
            "chainId": 31337,
            "environment": "local-exact-source",
            "mainnetQualification": False,
            "newExposureEnabled": True,
            "sourceSHA256": "a" * 64,
            "abiSHA256": hashlib.sha256(result.stdout.encode()).hexdigest(),
            "genesisHash": "0x" + "1" * 64,
            "deploymentBlock": "0x1",
            "deploymentBlockHash": "0x" + "2" * 64,
            "contracts": {
                alias: {"address": "0x" + f"{index + 1:02x}" * 20, "sha256": "b" * 64}
                for index, alias in enumerate((*module.NAMES, "Token"))
            },
        }

    def test_local_profile_is_bound_in_isolated_build_without_mutating_production(self):
        original = (ROOT / "docs/assets/ascension-wallet/build-profile.mjs").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            profile = local / "source.json"
            profile.write_text(json.dumps(self.local_profile()))
            output = module.build_local_profile(ROOT, profile, local / "wallet")
            compiled = json.loads(output.read_text())
            self.assertTrue(compiled["allowedActions"])
            subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "-e",
                    "const m=await import(process.argv[1]);const fs=await import('node:fs');"
                    "const c=new m.MarkClient(JSON.parse(fs.readFileSync(process.argv[2],'utf8')));"
                    "if(c.chainId!==31337||!c.profile.newExposureEnabled)throw Error('Wrong build binding');",
                    (output.parent / "client.mjs").as_uri(),
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(original, (ROOT / "docs/assets/ascension-wallet/build-profile.mjs").read_bytes())

    def test_local_builder_refuses_mainnet_mixed_abi_and_production_destinations(self):
        for corruption in ("mainnet", "abi", "archived-address", "destination"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                local = Path(directory)
                value = self.local_profile()
                output = local / "wallet"
                if corruption == "mainnet":
                    value["chainId"] = 1
                elif corruption == "abi":
                    value["abiSHA256"] = "0" * 64
                elif corruption == "archived-address":
                    value["contracts"]["Seed"]["address"] = module.ADDRESSES["Seed"]
                else:
                    output = ROOT / "docs/generated-forbidden-local-profile"
                source = local / "source.json"
                source.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    module.build_local_profile(ROOT, source, output)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
