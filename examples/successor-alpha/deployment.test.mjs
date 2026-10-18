// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const snapshot = JSON.parse(readFileSync(new URL('./deployment.json', import.meta.url), 'utf8'));
const recordBytes = readFileSync(new URL('../../deployments/ethereum-mainnet/2026-10-18/manifest.json', import.meta.url));
const record = JSON.parse(recordBytes);

test('flagship contract snapshot is bound to the retained exact deployment evidence', () => {
    assert.equal(snapshot.retainedEvidence.recordSha256, createHash('sha256').update(recordBytes).digest('hex'));
    assert.equal(snapshot.sourceCommit, record.source.commit);
    assert.deepEqual(snapshot.source, record.source);
    assert.deepEqual(snapshot.retainedEvidence.provenance, record.provenance);
    assert.equal(snapshot.retainedEvidence.planSha256, record.planSha256);
    assert.equal(snapshot.chainId, record.chainId);
    assert.equal(Object.keys(snapshot.contracts).length, record.contracts.length);
    for (const contract of record.contracts) {
        const item = snapshot.contracts[contract.name];
        assert.equal(item.name, contract.name);
        assert.equal(item.address, contract.address.toLowerCase());
        assert.equal(item.explorer, `https://etherscan.io/address/${item.address}#code`);
        assert.equal(item.runtimeCodeHash, contract.codeHash);
        assert.equal(item.creationTransactionHash, contract.creation.transactionHash);
        assert.deepEqual(item.recordedExplorerResult, contract.explorer);
        assert.deepEqual(item.observedValues, contract.values);
    }
    assert.deepEqual(snapshot.authoritySnapshot.block, record.authorityBlock);
    assert.deepEqual(snapshot.authoritySnapshot.bindings, record.bindings);
    assert.equal(snapshot.authoritySnapshot.governor, record.governor);
});

test('retained verification never becomes a fresh observation or operational authorization', () => {
    assert.equal(snapshot.publicVerification.status, 'retained-evidence-verified');
    assert.equal(snapshot.publicVerification.observedAt, record.observedAt);
    assert.deepEqual(snapshot.publicVerification.authorityBlock, record.authorityBlock);
    assert.equal(snapshot.publicVerification.freshRpcObservation, false);
    assert.equal(snapshot.publicVerification.freshExplorerObservation, false);
    assert.equal(snapshot.runtimeAuthorized, false);
    for (const key of ['activationAllowed', 'readyForPublicFunding', 'fullyProductionReady']) {
        assert.equal(snapshot[key], false);
        assert.equal(snapshot[key], record.status[key]);
    }
});
