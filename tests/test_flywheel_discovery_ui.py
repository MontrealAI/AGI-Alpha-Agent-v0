# SPDX-License-Identifier: Apache-2.0
"""Check bounded discovery drafts through the established Alpha project codec."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DiscoveryPlanningTests(unittest.TestCase):
    def run_node(self, body: str) -> None:
        source = (ROOT / "scripts/templates/alpha-flywheel/app.js").read_text()
        helpers = source.split("// BEGIN DISCOVERY PLANNING HELPERS\n", 1)[1].split(
            "// END DISCOVERY PLANNING HELPERS", 1
        )[0]
        code = (
            "import assert from 'node:assert/strict';\n"
            "import * as project from './examples/successor-alpha/project.mjs';\n"
            + helpers
            + "\nconst sample={needs:'Two independently motivated beneficiaries.',purpose:'Keep every original requirement.',"
            "existing:'Strong available method.',gap:'Unresolved useful requirement.',why:'New observed condition.',restriction:'Costly restriction.',structure:'Possible shared structure.',"
            "alternatives:'Method A\\nMethod B',construction:'Reusable checker.',arrangement:'Conditional demand.',"
            "experiment:'Compare both components and combination.',falsifier:'Any original requirement fails.',"
            "checkpoint:'Stop at the bound.',cap:5000,decision:'continue'};\n" + body
        )
        completed = subprocess.run(
            ["node", "--input-type=module", "-"],
            input=code,
            text=True,
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_draft_preserves_original_goal_and_grants_no_authority(self) -> None:
        self.run_node(
            "const fields=discoveryPlanFields(sample,'supplied fixture','a'.repeat(64));"
            "const p=project.addOpportunity(project.createProject(),fields);"
            "const restored=project.inspectProject(project.serializeProject(p));"
            "assert.equal(restored.authority,'none');"
            "assert.equal(restored.opportunities[0].state,'hypothesis');"
            "assert.equal(restored.opportunities[0].authority,'none');"
            "assert.ok(restored.opportunities[0].goal.includes(sample.purpose));"
            "assert.ok(restored.opportunities[0].target.includes(sample.falsifier));"
            "assert.ok(restored.opportunities[0].currentApproach.includes(sample.existing));"
            "assert.ok(restored.opportunities[0].currentApproach.includes(sample.gap));"
            "assert.ok(restored.opportunities[0].evidence.includes(sample.why));"
            "assert.ok(restored.opportunities[0].evidence.includes('No autonomous discovery'));"
            "assert.deepEqual(discoveryMissing(sample),[]);"
        )

    def test_partial_exploration_is_allowed_without_complete_business_case(self) -> None:
        self.run_node(
            "const partial={...sample,existing:'',gap:'',why:'',structure:'',alternatives:'',construction:'',arrangement:'',experiment:'',falsifier:''};"
            "const fields=discoveryPlanFields(partial,'user-supplied hypothesis','a'.repeat(64));"
            "assert.ok(discoveryMissing(partial).length>=6);"
            "assert.equal(project.planOpportunity(fields).state,'hypothesis');"
            "assert.ok(fields.alternative.includes('Unspecified; remains a hypothesis.'));"
            "assert.ok(discoveryMissing({...sample,alternatives:'Same\\nSame'}).includes('different formulations'));"
        )

    def test_field_limits_fit_existing_project_without_silent_truncation(self) -> None:
        self.run_node(
            "const sizes={needs:600,purpose:600,existing:500,gap:500,why:400,restriction:600,structure:500,alternatives:600,construction:500,"
            "arrangement:500,experiment:500,falsifier:500,checkpoint:500};"
            "const maximum={...sample,...Object.fromEntries(Object.entries(sizes).map(([k,n])=>[k,'x'.repeat(n)]))};"
            "const fields=discoveryPlanFields(maximum,'supplied fixture','a'.repeat(64));"
            "assert.ok(Object.values(fields).every(v=>v.length<=2000));project.planOpportunity(fields);"
            "assert.throws(()=>discoveryPlanFields({...maximum,needs:'x'.repeat(601)},'user','a'.repeat(64)));"
        )

    def test_source_motivated_candidate_is_optional_bounded_hypothesis(self) -> None:
        source = (ROOT / "scripts/templates/alpha-flywheel/app.js").read_text()
        candidate = source.split("const candidate={\n", 1)[1].split("};\nfor(const id of discoveryIds)", 1)[0]
        self.run_node(
            "for(const language of ['en','fr']){const say=(en,fr)=>language==='fr'?fr:en;"
            "const candidate={" + candidate + "};"
            "const fields=discoveryPlanFields({...candidate,cap:0,decision:'continue'},'researcher-selected hypothesis','a'.repeat(64));"
            "assert.ok(Object.values(fields).every(value=>value.length<=2000));"
            "assert.equal(project.planOpportunity(fields).authority,'none');"
            "assert.ok(fields.currentApproach.includes('https://modelcontextprotocol.io/'));"
            "assert.ok(fields.evidence.includes('https://modelcontextprotocol.io/'));}"
        )

    def test_invalid_budgets_purpose_and_decisions_are_refused(self) -> None:
        values = json.dumps([None, True, -1, 1.5, 1000001, "5000"])
        self.run_node(
            f"for(const cap of {values})assert.throws(()=>discoveryPlanFields({{...sample,cap}},'user','a'.repeat(64)));"
            "for(const key of ['needs','purpose'])assert.throws(()=>discoveryPlanFields({...sample,[key]:''},'user','a'.repeat(64)));"
            "assert.throws(()=>discoveryPlanFields({...sample,decision:'authorize'},'user','a'.repeat(64)));"
            "assert.throws(()=>discoveryPlanFields(sample,'user','not-a-source'));"
            "assert.equal(project.planOpportunity(discoveryPlanFields({...sample,decision:'stop'},'user','a'.repeat(64))).authority,'none');"
        )


if __name__ == "__main__":
    unittest.main()
