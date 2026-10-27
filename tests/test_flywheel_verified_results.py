# SPDX-License-Identifier: Apache-2.0
"""Recorded achievements must distinguish checked plans, impossibility and missing evidence."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VerifiedResultsTests(unittest.TestCase):
    def test_actual_record_and_incomplete_evidence_cannot_manufacture_success(self) -> None:
        source = (ROOT / "scripts/templates/alpha-flywheel/app.js").read_text()
        helper = source.split("// BEGIN VERIFIED RESULT HELPERS\n", 1)[1].split("// END VERIFIED RESULT HELPERS", 1)[0]
        report = json.loads((ROOT / "scripts/templates/alpha-flywheel/discovery-evidence.json").read_bytes())
        code = (
            "import assert from 'node:assert/strict';\n"
            + helper
            + "\nconst report="
            + json.dumps({"connected": report["connected"]})
            + ";\n"
            + "const actual=verifiedSnapshot(report);assert.equal(actual.accepted,12);"
            "assert.equal(actual.feasible,3);assert.equal(actual.infeasible,9);"
            "assert.equal(actual.artifact.outcome.placement.length,4);"
            "assert.deepEqual(actual.workflow,report.connected.constructed_workflow);"
            "for(const bad of [false,'true',1,null]){const changed=structuredClone(report);"
            "changed.connected.fresh_evaluation.cases[0].v2.verification.accepted_finite_result=bad;"
            "const partial=verifiedSnapshot(changed);assert.equal(partial.accepted,11);"
            "assert.equal(partial.infeasible,8);assert.equal(partial.results[0].accepted,false);}"
            "const noOracle=structuredClone(report);"
            "delete noOracle.connected.fresh_evaluation.cases[0].v2.verification.oracle_enumerated;"
            "assert.equal(verifiedSnapshot(noOracle).accepted,11);"
            "for(const bad of [{},{connected:{}},null])assert.equal(verifiedSnapshot(bad),null);"
            "for(const field of ['constructed_workflow','original_execution','fresh_evaluation']){"
            "const changed=structuredClone(report);delete changed.connected[field];"
            "assert.equal(verifiedSnapshot(changed),null);}"
            "const rejected=structuredClone(report);"
            "rejected.connected.original_execution.result.verification.accepted_finite_result=false;"
            "assert.equal(verifiedSnapshot(rejected),null);"
            "const missing=structuredClone(report);missing.connected.original_execution.result.artifacts={};"
            "assert.equal(verifiedSnapshot(missing),null);"
        )
        result = subprocess.run(["node", "--input-type=module", "-"], input=code, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
