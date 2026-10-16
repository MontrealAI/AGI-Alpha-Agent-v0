// SPDX-License-Identifier: Apache-2.0
// V2 exact-source export. Predicted export is offline; receipt-proven export re-verifies read-only evidence.
const fs = require('fs');
const path = require('path');
const policy = require('./mainnet-authority');
const legacy = require('./mainnet');
const packages = require('./verification-package');
const json = value => JSON.stringify(value, null, 2) + '\n';
async function plannedPackage(plan, revision, compiled = policy.compiledContracts()) {
    await policy.checkPlan(plan, compiled, revision);
    const bundle = packages.packageFiles({ kind: 'v2-new-graph-prediction', planSha256: plan.payloadSha256, revision,
        addressesAre: 'CREATE predictions only; no deployment or explorer acceptance proof' }, policy.NAMES.map((name, i) => {
        const contract = plan.contracts[name], build = plan.builds[contract.buildId], tx = plan.transactions[i];
        return { name, address: tx.expectedAddress, compiler: build.compiler, inputText: json(build.input), sourceName: contract.sourceName,
            abi: contract.abi, bytecode: contract.bytecode, args: tx.constructorArguments, data: tx.envelope.data };
    }));
    bundle.files['README.txt'] = [
        'ALPHA V2 NEW-GRAPH SOURCE VERIFICATION PACKAGE, ETHEREUM MAINNET CHAIN 1',
        'Addresses are predictions from the checked plan, not proof of deployment.',
        'Before submitting, match all five successful canonical creation receipts against this plan.',
        'For each address use standard-input.json, exact manifest compiler/qualified contract name,',
        'and constructor-arguments.txt. Preserve every compiler setting, metadata and source path.',
        'etherscan-request.json is an unsigned API V2 form payload; supply credentials separately.',
        'Nothing in this package signs, submits, changes historical deployments or contacts Etherscan.',
        'Retain final successful explorer acceptance; a submission GUID is only pending.',
        'Run the v2 finalized authority verifier. Funding, admission and activation need separate approval.',
        'Ownership is constructor-set transferable governor storage; dependency/binding semantics differ.',
        'No independent review, wallet custody, delegate safety or full consensus qualification is implied.', ''
    ].join('\n');
    bundle.manifest.schema = 'agialpha.explorer-verification-package.v2';
    bundle.manifest.activationAllowed = false;
    bundle.manifest.planSha256 = plan.payloadSha256;
    bundle.manifest.observedRevision = revision;
    bundle.manifest.senderPolicySha256 = policy.digest(plan.config.sender);
    bundle.manifest.sourceClosureSha256 = policy.digest(plan.builds);
    bundle.manifest.addressStatus = 'predicted';
    if (plan.config.sender.mode === policy.MARKER) {
        bundle.manifest.senderMode = policy.MARKER;
        bundle.manifest.originationScope = 'Bound review proposition: exact direct CREATE without creator/target invocation; report provenance requires independent acceptance, no delegate safety or custody conclusion';
        bundle.files['origination-evidence.json'] = json(plan.directOriginationEvidence);
    }
    for (const contract of Object.values(bundle.manifest.contracts)) contract.addressStatus = 'predicted';
    bundle.manifest.files = Object.fromEntries(Object.entries(bundle.files).filter(([name]) => name !== 'manifest.json').map(([name, value]) => [name, policy.digest(value)]));
    bundle.files['manifest.json'] = json(bundle.manifest);
    return bundle;
}
async function receiptProvenPackage(plan, rpc, evidence, revision, compiled = policy.compiledContracts()) {
    // Never accept a self-declared report or its checksum as deployment proof.
    const bundle = await plannedPackage(plan, revision, compiled);
    const report = await policy.verifyAuthority(plan, rpc, evidence, revision);
    bundle.manifest.profile.kind = 'v2-new-graph-receipt-proven';
    bundle.manifest.profile.addressesAre = 'Successful exact canonical creation receipts, rechecked using trusted read-only RPC';
    bundle.manifest.addressStatus = 'receipt-proven';
    bundle.manifest.readOnlyProviderObservations = true;
    bundle.manifest.authorityEvidenceSha256 = report.payloadSha256;
    bundle.manifest.acceptanceBlock = report.block;
    for (const [index, name] of policy.NAMES.entries()) {
        const creation = report.creations[index];
        bundle.manifest.contracts[name].addressStatus = 'receipt-proven';
        bundle.manifest.contracts[name].creationEvidence = creation;
    }
    bundle.files['authority-evidence.json'] = json(report);
    bundle.files['README.txt'] = bundle.files['README.txt'].replace(
        'Addresses are predictions from the checked plan, not proof of deployment.\nBefore submitting, match all five successful canonical creation receipts against this plan.',
        'All five addresses were matched to exact successful canonical creation receipts.\nThe finalized authority report is included. RPC observations trust the provider and are not consensus proofs.');
    bundle.manifest.files = Object.fromEntries(Object.entries(bundle.files).filter(([name]) => name !== 'manifest.json').map(([name, value]) => [name, policy.digest(value)]));
    bundle.files['manifest.json'] = json(bundle.manifest);
    return bundle;
}
function writePackage(bundle, destination) {
    const target = require('./authority-paths').assertOutsideCheckout(destination), parent = path.dirname(target);
    // Require an existing, real parent; do not follow symlink ancestors or silently create paths.
    let cursor = path.parse(parent).root;
    for (const part of parent.slice(cursor.length).split(path.sep).filter(Boolean)) {
        cursor = path.join(cursor, part);
        const stat = fs.lstatSync(cursor);
        if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error('Package parent must be an existing real directory');
    }
    if (!bundle || typeof bundle.files !== 'object' || !bundle.files['manifest.json']) throw Error('Invalid package');
    for (const [name, content] of Object.entries(bundle.files)) {
        if (!/^(?:[A-Za-z][A-Za-z0-9-]*\/)?[A-Za-z][A-Za-z0-9.-]*$/.test(name) || typeof content !== 'string') throw Error('Invalid package member');
    }
    // Atomic creation refuses both existing directories and symlinks. Partial failures remain visible.
    fs.mkdirSync(target, { mode: 0o700 });
    const directories = new Set([target]);
    for (const [name, content] of Object.entries(bundle.files)) {
        const file = path.join(target, name), directory = path.dirname(file);
        if (!directories.has(directory)) { fs.mkdirSync(directory, { mode: 0o700 }); directories.add(directory); }
        const fd = fs.openSync(file, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_NOFOLLOW, 0o600);
        try { fs.writeFileSync(fd, content); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    }
    for (const directory of [...directories].reverse().concat(parent)) {
        const fd = fs.openSync(directory, fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW);
        try { fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    }
    return target;
}
async function main() {
    const [mode, input, evidenceOrOutput, receiptOutput, extra] = process.argv.slice(2);
    if (!input || !evidenceOrOutput || extra || !['plan', 'receipts'].includes(mode) ||
        (mode === 'plan' ? receiptOutput !== undefined : !receiptOutput))
        throw Error('Usage: authority-verification-package.js plan PLAN.json NEW_DIRECTORY OR receipts PLAN.json EVIDENCE.json NEW_DIRECTORY');
    const revision = require('./authority-revision').reviewedRevision();
    require('./authority-paths').assertOutsideCheckout(mode === 'plan' ? evidenceOrOutput : receiptOutput);
    const boundary = require('./authority-input-boundary').createInputBoundary(revision);
    boundary.pinDirectory(path.dirname(path.resolve(mode === 'plan' ? evidenceOrOutput : receiptOutput)));
    const plan = boundary.readJson(input);
    // Validate source independently before even constructing a provider transport.
    await policy.checkPlan(plan, undefined, revision);
    let bundle;
    if (mode === 'plan') bundle = await plannedPackage(plan, revision);
    else {
        const evidence = boundary.readJson(evidenceOrOutput);
        if (!process.env.ALPHA_READ_ONLY_RPC_URL) throw Error('Explicit ALPHA_READ_ONLY_RPC_URL required');
        const { createReadOnlyRpc, scopeForPlan } = require('./authority-rpc');
        const rpc = createReadOnlyRpc(process.env.ALPHA_READ_ONLY_RPC_URL, scopeForPlan(plan));
        bundle = await receiptProvenPackage(plan, rpc, evidence, revision);
    }
    boundary.assertCurrent();
    const destination = writePackage(bundle, mode === 'plan' ? evidenceOrOutput : receiptOutput);
    console.log(JSON.stringify({ output: destination, schema: bundle.manifest.schema, addressStatus: bundle.manifest.addressStatus,
        readOnlyProviderObservations: mode === 'receipts', externalTransactions: false, explorerSubmission: 'not-performed' }));
}
module.exports = { plannedPackage, receiptProvenPackage, writePackage };
if (require.main === module) main().catch(() => { console.error('V2 export failed; use exact clean reviewed sources and a new output directory.'); process.exitCode = 1; });
