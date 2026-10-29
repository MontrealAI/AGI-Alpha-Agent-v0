# SPDX-License-Identifier: Apache-2.0
"""Regressions for the actual counterexamples found during integration."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
import unittest

from contrib.enterprise_campaign.delta_acceptance import verify_delta
from contrib.enterprise_campaign.delta_delivery import _digest, build_delta, make_request

BEFORE = "sku,price,note\nA,10.00,keep\nB,20.00,local\n"
DELTA = "sku,price\nA,12.50\n"


class PacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = make_request(["sku"], ["price"], ["price"])
        self.packet = build_delta(BEFORE, DELTA, self.request)

    def reject_rehashed(self, packet: dict[str, Any]) -> None:
        native = packet["native_package"]
        if isinstance(native, dict):
            native["proof_digest"] = _digest({k: v for k, v in native.items() if k != "proof_digest"})
        packet["digest"] = _digest({k: v for k, v in packet.items() if k != "digest"})
        result = verify_delta(BEFORE, DELTA, packet, self.request)
        self.assertEqual(result["verdict"], "REJECTED", packet)

    def test_rehashed_unsafe_preview_rejected(self) -> None:
        self.packet["native_package"]["safe_preview_csv"] = "=2+2\n"
        self.reject_rehashed(self.packet)

    def test_rehashed_suppressed_change_list_rejected(self) -> None:
        self.packet["native_package"]["changes"] = []
        self.reject_rehashed(self.packet)

    def test_rehashed_false_row_count_rejected(self) -> None:
        self.packet["native_package"]["trace"]["before_rows"] = 999
        self.reject_rehashed(self.packet)

    def test_rehashed_substituted_producer_identity_rejected(self) -> None:
        self.packet["source_git_blob"] = "0" * 40
        self.reject_rehashed(self.packet)

    def test_every_native_field_is_checked(self) -> None:
        for field in self.packet["native_package"]:
            with self.subTest(field=field):
                packet = copy.deepcopy(self.packet)
                packet["native_package"][field] = "ALTERED"
                if field == "proof_digest":
                    packet["digest"] = _digest({k: v for k, v in packet.items() if k != "digest"})
                    self.assertEqual(verify_delta(BEFORE, DELTA, packet, self.request)["verdict"], "REJECTED")
                else:
                    self.reject_rehashed(packet)

    def test_unknown_packet_fields_refused(self) -> None:
        for location in ("native", "envelope"):
            with self.subTest(location=location):
                packet = copy.deepcopy(self.packet)
                target = packet["native_package"] if location == "native" else packet
                target["extra_permission"] = True
                self.reject_rehashed(packet)

    def test_malformed_container_returns_rejected(self) -> None:
        for value in (None, [], "packet", 123):
            with self.subTest(value=value):
                self.assertEqual(verify_delta(BEFORE, DELTA, value, self.request)["verdict"], "REJECTED")
                packet = copy.deepcopy(self.packet)
                packet["native_package"] = value
                self.reject_rehashed(packet)

    def test_invalid_untouched_decimal_refused(self) -> None:
        invalid = BEFORE.replace("B,20.00", "B,NaN")
        self.assertEqual(verify_delta(invalid, DELTA, self.packet, self.request)["verdict"], "REJECTED")

    def test_checker_does_not_mutate_candidate(self) -> None:
        original = copy.deepcopy(self.packet)
        self.assertEqual(verify_delta(BEFORE, DELTA, self.packet, self.request)["verdict"], "PASS_IN_SCOPE")
        self.assertEqual(self.packet, original)

    def test_boolean_does_not_substitute_for_count(self) -> None:
        self.packet["native_package"]["trace"]["changed_keys"] = True
        self.reject_rehashed(self.packet)

    def test_second_process_verifier_accepts_and_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name, text in {"before": BEFORE, "delta": DELTA,
                               "request": json.dumps(self.request), "package": json.dumps(self.packet)}.items():
                (folder / name).write_text(text, encoding="utf-8")
            command = [sys.executable, "-m", "contrib.enterprise_campaign.delta_acceptance"]
            for name in ("before", "delta", "request", "package"):
                command.extend(["--" + name, str(folder / name)])
            first = subprocess.run(command, cwd=Path(__file__).resolve().parents[2],
                                   capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 0, first.stderr)
            original_bytes = (folder / "package").read_bytes()
            self.assertEqual(json.loads(first.stdout)["verdict"], "PASS_IN_SCOPE")
            self.assertEqual((folder / "package").read_bytes(), original_bytes)
            self.packet["native_package"]["changes"] = []
            (folder / "package").write_text(json.dumps(self.packet), encoding="utf-8")
            second = subprocess.run(command, cwd=Path(__file__).resolve().parents[2],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(json.loads(second.stdout)["verdict"], "REJECTED")

    def test_verifier_missing_files_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            missing = str(Path(temp) / "missing")
            command = [sys.executable, "-m", "contrib.enterprise_campaign.delta_acceptance"]
            for name in ("before", "delta", "request", "package"):
                command.extend(["--" + name, missing])
            result = subprocess.run(command, cwd=Path(__file__).resolve().parents[2],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["verdict"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
