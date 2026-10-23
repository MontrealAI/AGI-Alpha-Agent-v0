// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {FROZEN_EVALUATION} from './compounding-probe.mjs';

test('existing enterprise constructs, reuses and recovers with complete counted comparisons', () => {
    const root = fileURLToPath(new URL('../../', import.meta.url));
    const protocol = JSON.parse(readFileSync(new URL('../../docs/agent/compounding-probe-2026-10-22.json', import.meta.url)));
    const runner = new URL('./compounding-probe.mjs', import.meta.url);
    const digest = createHash('sha256').update(readFileSync(runner)).digest('hex');
    assert.deepEqual(FROZEN_EVALUATION, protocol.criteria);
    assert.equal(digest, protocol.amendment.correctedRunnerSHA256);
    const invocation = spawnSync(process.execPath, [fileURLToPath(runner)], {
        cwd: root, encoding: 'utf8', timeout: 60_000, maxBuffer: 2_000_000
    });
    assert.ifError(invocation.error);
    assert.equal(invocation.signal, null);
    assert.equal(invocation.status, 0, invocation.stderr || invocation.stdout);
    const report = JSON.parse(invocation.stdout), result = report.components, journey = report.enterpriseJourney;
    assert.equal(report.environment.runnerSHA256, digest);
    assert.equal(result.state, 'PASSED_COMPONENT_CRITERIA');
    assert.deepEqual(result.failures, []);
    assert.equal(result.scenarios.length, 9);
    assert.equal(result.actualCampaignKnownWork, 1_348_918);
    assert.equal(new Set(result.ledger.map(item => item.id)).size, result.ledger.length);
    for (const scenario of result.scenarios) {
        const entries = scenario.chargeIds.map(id => result.ledger.find(item => item.id === id));
        assert.ok(entries.every(Boolean));
        assert.equal(entries.reduce((total, item) => total + item.countedWork, 0), scenario.knownCountedWork);
        assert.equal(scenario.totalEconomicCostComplete, false);
        assert.ok(Object.values(scenario.unknownCosts).every(value => value === null));
    }
    for (const round of FROZEN_EVALUATION.rounds) {
        const at = arm => result.scenarios.find(item => item.rounds === round && item.arm === arm);
        assert.ok(at('competent-static-specialist').knownCountedWork < at('retained-assets').knownCountedWork);
        assert.equal(at('rebuild-per-round').knownCountedWork - at('retained-assets').knownCountedWork,
            (round - 1) * at('retained-assets').knownPreparationWork);
    }
    const specialist = result.ledger.filter(item => item.scope.startsWith('competent-static-specialist/'));
    assert.equal(specialist.length, 63);
    for (const entry of specialist) {
        const receipt = result.rawReceipts[entry.receiptDigest];
        assert.equal(receipt.artifactDigest, null);
        assert.equal(receipt.executionSource, 'examples/autonomous-enterprises/specialist.mjs');
        assert.equal(receipt.accepted, true);
    }
    assert.equal(result.changed.stalePassesChangedRequirement, false);
    assert.equal(result.changed.successorPassesChangedRequirement, true);
    assert.equal(result.changed.rejectedReason, 'SINGULAR_KERNEL');
    assert.equal(result.changed.rejectedSpentWork, 32);
    assert.equal(result.changed.knownIncrementalWork, 18_250);
    assert.equal(journey.state, 'SUCCESSOR_ACCEPTED_LOCAL');
    assert.equal(journey.recoveredState, journey.state);
    assert.equal(journey.fileRoundtripIdentical, true);
    assert.equal(journey.knownObservedControllerWork, journey.originalExecutionWork
        + Object.values(journey.actualReplayWork).reduce((a, b) => a + b, 0));
    assert.equal(journey.knownObservedControllerWork, 1_802_222);
    assert.equal(journey.institutionalAcceptance, false);
    assert.equal(journey.externalAuthority, false);
    assert.equal(journey.totalEconomicCostComplete, false);
    assert.equal(journey.settlement, 'SIMULATED_ONLY');
});
