// SPDX-License-Identifier: Apache-2.0
// Saved-evidence join regressions only. No native runtime, EVM, or held probe runs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { verifyJourney } from '../verify-journey.mjs';
import { canonicalBytes } from './mission-delivery.mjs';

const savedJourney = JSON.parse(readFileSync(new URL('../results/journey.json', import.meta.url), 'utf8'));
const savedEvm = JSON.parse(readFileSync(new URL('../../evidence/contracts/writer4-parent-lifecycle.json', import.meta.url), 'utf8'));
const sha = value => createHash('sha256').update(value).digest('hex');

function rejectMutation(mutate) {
  const journey = structuredClone(savedJourney), evm = structuredClone(savedEvm);
  mutate(journey, evm);
  assert.throws(() => verifyJourney(journey, evm), { code: 'ERR_ASSERTION' });
}

// Keep derivative transport hashes consistent, so the refusal must come from
// the untouched scientific artifact/proof rather than an obsolete graph digest.
function refreshGraphBinding(delivery) {
  delivery.bindingSha256 = sha(canonicalBytes(delivery.binding).trimEnd());
  for (const transfer of Object.values(delivery.transferBindings)) transfer.graphBindingSha256 = delivery.bindingSha256;
}

test('the exact recorded parent and distinct successor retain their accepted join', () => {
  const acceptance = verifyJourney(savedJourney, savedEvm);
  assert.equal(acceptance.accepted, true);
  assert.deepEqual(acceptance.joins.map(item => item.missionId), ['bom-demand-00', 'remediation-impact-03']);
  assert.deepEqual(acceptance.joins.map(item => item.localTransactions), [16, 16]);
  assert.deepEqual(acceptance.joins.map(item => item.repositories), [['alpha', 'manager', 'jobs', 'fleet'], ['alpha', 'manager', 'jobs', 'fleet']]);
});

test('joint input rebinding in delivery and chain evidence cannot replace the checked input', () => {
  rejectMutation((journey, evm) => {
    journey.parent.binding.inputSha256 = '0'.repeat(64);
    evm.inputSha256 = '0'.repeat(64);
    refreshGraphBinding(journey.parent);
  });
});

test('empty transaction histories cannot stand in for either 16-stage lifecycle', () => {
  rejectMutation((_journey, evm) => { evm.steps = []; evm.successorLifecycle.steps = []; });
});

test('changed native groups are refused even when the aggregate total is preserved', () => {
  rejectMutation(journey => {
    const groups = journey.parent.native.result.groups;
    groups[0].total += 1;
    groups[1].total -= 1;
  });
});

test('the same transaction cannot be counted in both mission lifecycles', () => {
  rejectMutation((_journey, evm) => {
    evm.successorLifecycle.steps[0].transactionHash = evm.steps[0].transactionHash;
  });
});

test('an accepted proof for a different mission cannot authorize this join', () => {
  rejectMutation(journey => { journey.parent.admission.proof.missionId = 'another-mission'; });
});

test('joint capability rebinding cannot change the original checked artifact', () => {
  rejectMutation((journey, evm) => {
    journey.parent.binding.capabilityId = '0'.repeat(64);
    journey.parent.admission.proof.capabilityHash = '0'.repeat(64);
    evm.capabilityHash = '0'.repeat(64);
    refreshGraphBinding(journey.parent);
  });
});

test('each repository transfer must retain the exact graph binding digest', () => {
  rejectMutation(journey => { journey.parent.transferBindings.fleet.graphBindingSha256 = '0'.repeat(64); });
});
