// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
const workflow=fs.readFileSync(new URL('../../.github/workflows/successor-mission.yml',import.meta.url),'utf8');
test('mission PR gate retains pinned dependencies and all substantive suites',()=>{
  assert.match(workflow,/\n  pull_request:\n/);
  assert.match(workflow,/\n  push:\n    branches: \[main\]/);
  assert.match(workflow,/persist-credentials: false/);
  const actions=[...workflow.matchAll(/uses: (actions\/[a-z-]+)@([^\s]+)/g)];
  assert.equal(actions.length,3);
  for(const [,name,pin] of actions)assert.match(pin,/^[a-f0-9]{40}$/,name);
  for(const command of [
    'python -m pip install playwright==1.54.0',
    'python -m playwright install --with-deps chromium',
    'npm ci --prefix tests/browser --ignore-scripts',
    'node --test examples/successor-workbench/mission-record.test.mjs examples/successor-workbench/mission-app.test.mjs examples/successor-workbench/mission-workflow.test.mjs',
    'node examples/successor-workbench/test.mjs',
    'python scripts/generate_successor_mission.py',
    'python scripts/generate_successor_workbench.py',
    'python scripts/build_service_worker.py',
    'python tests/browser/test_successor_mission_store.py',
    'python tests/browser/test_successor_mission_browser.py',
  ])assert.ok(workflow.includes(command),command);
  assert.match(workflow,/AXE_SCRIPT:.*tests\/browser\/node_modules\/axe-core\/axe\.min\.js/);
  assert.doesNotMatch(workflow,/continue-on-error|if:\s*always\(\)|if:\s*failure\(\)/);
  assert.match(workflow,/cancel-in-progress: \$\{\{ github.event_name == 'pull_request' \}\}/);
});
