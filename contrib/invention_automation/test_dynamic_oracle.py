# SPDX-License-Identifier: Apache-2.0
"""Judge controls only; these tests do not qualify dynamic execution."""

from __future__ import annotations

import unittest
from copy import deepcopy
from typing import Any

from contrib.invention_automation.dynamic_oracle import expected_outputs, judge
from contrib.invention_automation.qualify_dynamic import (
    require_native_artifact,
    require_probe_receipt,
)


class DynamicOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case: dict[str, Any] = {
            "requirements": {"voltage": "voltage"},
            "records": [
                {"id": "valid", "fields": {"voltage": {"unit": "kV", "value": "12"}}},
                {"id": "invalid", "fields": {"voltage": {"unit": "kVA", "value": "12"}}},
                {"id": "missing", "fields": {}},
            ],
        }
        self.result: dict[str, Any] = {
            "executed": True,
            "status": "EXECUTED_UNVERIFIED",
            "image": "fixture-image",
            "artifact": {
                "outputs": expected_outputs(self.case),
                "trace": [{"record": record["id"], "op": "emit"} for record in self.case["records"]],
                "operations": 3,
            },
        }

    def test_actual_outcomes_are_checked(self) -> None:
        self.assertEqual(judge(self.case, self.result, "fixture-image")["verdict"], "PASS")
        self.result["artifact"]["outputs"][1]["status"] = "CONSISTENT"
        self.assertEqual(judge(self.case, self.result, "fixture-image")["verdict"], "REJECTED")

    def test_blocked_and_exit_success_do_not_qualify(self) -> None:
        for update in ({"executed": False}, {"status": "BLOCKED"}, {"status": "PASS"}):
            candidate = {**self.result, **update}
            self.assertEqual(judge(self.case, candidate, "fixture-image")["verdict"], "REJECTED")

    def test_wrong_image_is_rejected(self) -> None:
        self.assertEqual(judge(self.case, self.result, "other-image")["verdict"], "REJECTED")

    def test_missing_or_extra_containment_checks_cannot_pass(self) -> None:
        require_probe_receipt("resource-exhaustion", {"checks": {"scratch_exhaustion": True, "pids_exhaustion": True}})
        for checks in (
            {},
            {"unrelated": True},
            {"scratch_exhaustion": True},
            {"scratch_exhaustion": True, "pids_exhaustion": 1},
        ):
            with self.assertRaises(ValueError):
                require_probe_receipt("resource-exhaustion", {"checks": checks})

    def test_invalid_control_cannot_pass_by_crashing(self) -> None:
        require_native_artifact(self.result)
        for update in ({"status": "FAILED"}, {"executed": False}, {"artifact": None}):
            with self.assertRaises(ValueError):
                require_native_artifact({**self.result, **update})

    def test_empty_or_missing_record_trace_is_rejected(self) -> None:
        self.result["artifact"]["trace"] = []
        self.result["artifact"]["operations"] = 0
        self.assertEqual(judge(self.case, self.result, "fixture-image")["verdict"], "REJECTED")

    def test_duplicate_and_unsupported_cohort_rejected(self) -> None:
        with self.assertRaises(ValueError):
            expected_outputs({**self.case, "records": [self.case["records"][0]] * 2})
        with self.assertRaises(ValueError):
            expected_outputs({**self.case, "requirements": {"x": "invented"}})

    def test_schema_success_cannot_hide_missing_or_reordered_outputs(self) -> None:
        candidate = deepcopy(self.result)
        candidate["artifact"]["outputs"].reverse()
        self.assertEqual(judge(self.case, candidate, "fixture-image")["verdict"], "REJECTED")
        candidate["artifact"]["outputs"].pop()
        self.assertEqual(judge(self.case, candidate, "fixture-image")["verdict"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
