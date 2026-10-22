// Adversarial data variants of an actual receipt; never another execution.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import * as contract from '../alpha/examples/successor-capability/discovery-lab-contract.mjs';
import * as workspace from '../alpha/examples/successor-capability/workspace.mjs';
import * as receipts from '../alpha/examples/successor-capability/discovery-lab-receipts.mjs';
assert.equal(process.argv.length, 5, 'Usage: node receipt-v3-variants.mjs workspace.json actual-wrapper.json output-directory');
const [workspacePath, wrapperPath, directory] = process.argv.slice(2);
const wrapper = JSON.parse(fs.readFileSync(wrapperPath, 'utf8'));
const saved = await workspace.parseWorkspace(fs.readFileSync(workspacePath, 'utf8'));
const inspection = await workspace.inspectWorkspace(saved), originalReceipt = JSON.parse(wrapper.raw);
const campaign = inspection.discovery.campaigns.find(record => contract.canonical(record.bindings) === contract.canonical(originalReceipt.bindings));
const context = receipts.makeReceiverContext(campaign), original = await receipts.inspectReceiverReceipt(wrapper, context);
const variants = [
    ['units-equal-bytes', receipt => {receipt.resources.units = 'x' + receipt.resources.units.slice(1);}],
    ['diagnostics', receipt => {receipt.checker.report.reasons = ['UNATTESTED_DIAGNOSTIC_TEXT'];}],
    ['native-accepted-false', receipt => {receipt.checker.report.accepted = false; receipt.checker.report.reasons = ['ELAPSED_REPLAY_CHECK_INCOMPLETE']; receipt.state = 'inconclusive';}],
    ['native-memory', receipt => {receipt.checker.report.resourceUsed.memoryBytes++; receipt.resources.checkerUsed.memoryBytes++;}],
    ['elapsed', receipt => {receipt.resources.receiverUsed.elapsedMs += 10; receipt.resources.checkerUsed.elapsedMs += 10; receipt.checker.report.resourceUsed.elapsedMs += 10; receipt.resources.totalUsed.elapsedMs = receipt.resources.receiverUsed.elapsedMs + receipt.resources.checkerUsed.elapsedMs;}],
    ['search-reservation', receipt => {receipt.resources.receiverReservation.search++; receipt.resources.nativeLimits.search--;}],
    ['derived-outcome', receipt => {receipt.resources.receiverUsed.memoryBytes = JSON.parse(receipt.original).resourceLimits.memoryBytes + 1; receipt.checker.withinResourceEnvelope = false; receipt.state = 'inconclusive';}],
    ['nested-request', async receipt => {
        const before = Buffer.byteLength(receipt.original), request = JSON.parse(receipt.original);
        receipt.original = JSON.stringify(Object.fromEntries(Object.entries(request).reverse()));
        receipt.requestSha256 = await receipts.rawReceiptDigest(receipt.original);
        const delta = Buffer.byteLength(receipt.original) - before;
        receipt.resources.receiverUsed.memoryBytes += delta;
        receipt.resources.receiverReservation.memoryBytes += 3 * delta;
        receipt.resources.receiverReservation.storageBytes += 2 * delta;
        for (const key of contract.RESOURCE_KEYS) receipt.resources.nativeLimits[key] = request.resourceLimits[key] - receipt.resources.receiverReservation[key];
    }]
];
fs.mkdirSync(directory, {recursive: true});
const output = [];
for (const [name, change] of variants) {
    const receipt = JSON.parse(wrapper.raw); await change(receipt);
    const working = receipt.resources.receiverUsed.memoryBytes - receipt.resources.receiverUsed.storageBytes;
    for (let index = 0; index < 16; index++) {
        receipt.resources.receiverUsed.storageBytes = Buffer.byteLength(JSON.stringify(receipt));
        receipt.resources.receiverUsed.memoryBytes = working + receipt.resources.receiverUsed.storageBytes;
        for (const key of contract.RESOURCE_KEYS.filter(key => key !== 'elapsedMs')) receipt.resources.totalUsed[key]
            = receipt.resources.receiverUsed[key] + receipt.resources.checkerUsed[key];
    }
    const variant = {raw: JSON.stringify(receipt), source: wrapper.source};
    const checked = await receipts.inspectReceiverReceipt(variant, context);
    assert.equal(checked.receiptId, original.receiptId, name); assert.notEqual(checked.receiptDigest, original.receiptDigest, name);
    const path = directory + '/' + name + '-wrapper.json', raw = JSON.stringify(variant);
    fs.writeFileSync(path, raw, {flag: 'wx'});
    output.push({name, path, rawReceiptSha256: checked.receiptDigest,
        wrapperSha256: createHash('sha256').update(raw).digest('hex'), semanticReceiptId: checked.receiptId,
        individuallyValidated: true, reportedState: checked.state});
}
const proof = {schema: 'discovery-lab/v3-adversarial-receipt-variants/v1',
    scope: 'Adversarial variants of an actual captured receipt. No additional execution or authenticated invocation count.',
    input: wrapperPath, originalRawReceiptSha256: original.receiptDigest, semanticReceiptId: original.receiptId,
    missionId: saved.missionId, variants: output, authority: 'none'};
fs.writeFileSync(directory + '/variant-proof.json', JSON.stringify(proof, null, 2) + '\n', {flag: 'wx'});
console.log(JSON.stringify(proof, null, 2));
