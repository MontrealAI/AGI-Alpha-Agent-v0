# SPDX-License-Identifier: Apache-2.0
"""Keep read-only deployment snapshots complete without caching wallet runtime profiles."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.build_service_worker import gather_assets


class DeploymentCacheTests(unittest.TestCase):
    def test_complete_snapshot_and_fresh_wallet_boundary(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            names = [
                "deployments/2026-10-18/index.html",
                "deployments/2026-10-18/directory.css",
                "deployments/2026-10-18/manifest.json",
                "ascension/mainnet/index.html",
                "assets/nova-studio/profile.json",
                "assets/ascension-wallet/profile.json",
                "deployments/2026-10-18/operator.js",
            ]
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("snapshot", encoding="utf-8")
            self.assertEqual(gather_assets(root), sorted(names[:3]))


if __name__ == "__main__":
    unittest.main()
