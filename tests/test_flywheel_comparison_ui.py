# SPDX-License-Identifier: Apache-2.0
"""Verify the result view preserves missing evidence and exact fixture provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_comparison_evidence_binds_actual_sources() -> None:
    evidence = json.loads((ROOT / "scripts/templates/alpha-flywheel/comparison-evidence.json").read_bytes())
    for path, expected in evidence["sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    final = evidence["stages"]["reconciled-fixture"]
    assert final["planned_cases"] == 2
    assert final["contrasts"]["retained"]["cost_saving_micro_usd"] == "-77"
    assert evidence["actual_complete_cost_micro_usd"] is None
    assert evidence["actual_customer_collections_micro_usd"] == evidence["controlled_frontier_trials"] == 0


def test_result_view_recomputes_counts_and_refuses_duplicate_or_missing_acceptance() -> None:
    source = (ROOT / "scripts/templates/alpha-flywheel/app.js").read_text()
    helpers = source.split("// BEGIN COMPARISON RESULT HELPERS\n", 1)[1].split("// END COMPARISON RESULT HELPERS", 1)[0]
    code = (
        "import assert from 'node:assert/strict';import fs from 'node:fs';\n"
        + helpers
        + "\n"
        + """
const data=JSON.parse(fs.readFileSync('scripts/templates/alpha-flywheel/comparison-evidence.json','utf8'));
const final=data.stages['reconciled-fixture'];
assert.equal(comparisonView(final).accepted,6);
assert.equal(comparisonView(final).retained,0);
assert.equal(comparisonView(data.stages.planned).accepted,0);
assert.equal(comparisonView(data.stages.planned).complete,false);
assert.equal(comparisonView(data.stages['partially-executed']).accepted,3);
const removed=structuredClone(final);removed.cells[0].acceptance_digest=null;
assert.equal(comparisonView(removed).accepted,5);assert.equal(comparisonView(removed).complete,false);
const spoof=structuredClone(final);spoof.arms.U.accepted=99;
assert.equal(comparisonView(spoof).arms.U.accepted,2);
for(const mutate of [x=>x.cells.pop(),x=>x.cells[0]=x.cells[1],x=>x.planned_cases=1.5,x=>x.planned_cases=17]){
 const bad=structuredClone(final);mutate(bad);assert.equal(comparisonView(bad),null);
}
const stale=structuredClone(final);stale.current_evidence_valid=false;
assert.equal(comparisonView(stale).complete,false);
assert.equal(comparisonView(null),null);
"""
    )
    result = subprocess.run(["node", "--input-type=module", "-"], input=code, text=True, cwd=ROOT, capture_output=True)
    assert result.returncode == 0, result.stderr
