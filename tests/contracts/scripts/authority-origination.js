// SPDX-License-Identifier: Apache-2.0
// Additive direct-origination evidence. No signing, provider, delegate call or marker change.
const E = require('ethers');
const crypto = require('crypto');
const { canonical } = require('./mainnet');
const MARKER = 'marker-eoa-direct-create.v1';
const digest = x => crypto.createHash('sha256').update(typeof x === 'string' ? x : canonical(x)).digest('hex');
function need(ok, message) { if (!ok) { const e = Error(message); e.publicMessage = true; throw e; } }
function exact(x, fields) { need(x && typeof x === 'object' && !Array.isArray(x) && Object.keys(x).sort().join(',') === [...fields].sort().join(','), 'Exact direct-origination fields required'); }
function address(x) { const a = E.getAddress(x); need(a !== E.ZeroAddress, 'Zero address'); return a; }
function word(x) { need(typeof x === 'string' && /^0x[0-9a-f]{64}$/.test(x), 'Exact lowercase storage word required'); }
function sha(x) { need(typeof x === 'string' && /^[0-9a-f]{64}$/.test(x) && x !== '0'.repeat(64), 'Nonzero evidence SHA256 required'); }
function validateSender(sender, creator) {
    exact(sender, ['mode', 'delegationCode', 'target', 'targetCodeHash', 'storageChecks', 'qualification']);
    need(sender.mode === MARKER && /^0xef0100[0-9a-f]{40}$/.test(sender.delegationCode), 'Exact marker direct-origination mode/code required');
    need(address(sender.target) === address('0x' + sender.delegationCode.slice(8)) && address(sender.target) !== address(creator), 'Marker target mismatch or self target');
    word(sender.targetCodeHash); need(sender.targetCodeHash !== E.ZeroHash, 'Target code hash required');
    need(Array.isArray(sender.storageChecks) && sender.storageChecks.length <= 32, 'At most 32 explicitly selected storage probes');
    const seen = new Set();
    for (const s of sender.storageChecks) {
        exact(s, ['address', 'slot', 'value']); const a = address(s.address); word(s.slot); word(s.value);
        need([address(creator), address(sender.target)].includes(a), 'Storage probe must name creator or marker target');
        const key = a.toLowerCase() + ':' + s.slot; need(!seen.has(key), 'Duplicate storage probe'); seen.add(key);
    }
    exact(sender.qualification, ['consensusEvidenceSha256', 'directExecutionEvidenceSha256']); Object.values(sender.qualification).forEach(sha);
}
function qualificationScope(config, compiled, revision, transactions) {
    validateSender(config.sender, config.deployer);
    need(Array.isArray(transactions) && transactions.length === 5, 'Exactly five source-derived CREATEs required');
    const operations = transactions.map((t, index) => {
        const e = t.envelope;
        need(e.type === 2 && e.chainId === 1 && e.from === config.deployer && e.nonce === config.nonce + index && e.to === null && e.value === '0' &&
            Array.isArray(e.accessList) && e.accessList.length === 0 && t.expectedAddress === E.getCreateAddress({ from: config.deployer, nonce: e.nonce }), 'Exact direct CREATE scope required');
        return { index, name: t.name, from: e.from, nonce: e.nonce, to: null, value: '0', address: t.expectedAddress, initcodeKeccak256: E.keccak256(e.data), envelopeSha256: digest(e) };
    });
    return { schema: 'agialpha.marker-direct-qualification-scope.v1', chainId: 1, creator: config.deployer, governor: config.governor.address,
        source: structuredClone(revision), compiledSha256: digest(compiled), block: structuredClone(config.block), executionHardfork: 'osaka',
        delegationCode: config.sender.delegationCode, target: config.sender.target, targetCodeHash: config.sender.targetCodeHash,
        storageChecks: structuredClone(config.sender.storageChecks), dependencies: structuredClone(config.dependencies), rootOwners: structuredClone(config.rootOwners), operations };
}
function validateEvidence(config, compiled, revision, transactions, evidence) {
    const scope = qualificationScope(config, compiled, revision, transactions);
    exact(evidence, ['schema', 'scope', 'reports']); need(evidence.schema === 'agialpha.marker-direct-qualification-evidence.v1' && canonical(evidence.scope) === canonical(scope), 'Direct-origination evidence scope differs');
    exact(evidence.reports, ['consensusEvidenceSha256', 'directExecutionEvidenceSha256']);
    for (const [key, expected] of Object.entries(config.sender.qualification)) {
        const report = evidence.reports[key], consensus = key === 'consensusEvidenceSha256';
        need(digest(report) === expected, 'Direct-origination report bytes differ');
        exact(report, consensus ? ['schema', 'disposition', 'scope', 'reviewReference', 'artifacts'] : ['schema', 'disposition', 'scope', 'reviewReference', 'artifacts', 'invocations']);
        need(report.schema === (consensus ? 'agialpha.direct-consensus-report.v1' : 'agialpha.direct-execution-report.v1') &&
            report.disposition === (consensus ? 'direct-type2-create-does-not-invoke-origin-code' : 'five-direct-creates-no-creator-or-target-invocation'), 'Direct-origination proposition differs');
        need(canonical(report.scope) === canonical(scope) && typeof report.reviewReference === 'string' && report.reviewReference.length >= 8 && report.reviewReference.length <= 2048, 'Direct-origination source/actor/operation review differs');
        exact(report.artifacts, consensus ? ['consensusSourceSha256', 'analysisSha256'] : ['sourceCallGraphSha256', 'initcodeCallGraphSha256', 'traceSha256']); Object.values(report.artifacts).forEach(sha);
        if (!consensus) { exact(report.invocations, ['creator', 'target']); need(report.invocations.creator === 0 && report.invocations.target === 0, 'Creator/target invocation is outside this profile'); }
    }
    // Content binding is not reviewer independence, factual attestation, target safety or key custody.
    // The trusted Mac independently accepts the actual source/build and report/artifact provenance.
    return scope;
}
function analyzeTrace(trace, creator, target, callCode) {
    need(trace && trace.failed === false && Array.isArray(trace.structLogs) && trace.structLogs.length > 0 && trace.structLogs.length <= 100000,
        'Complete successful bounded local execution trace required');
    need(Buffer.byteLength(JSON.stringify(trace)) <= 32 * 1024 * 1024, 'Trace exceeds byte bound');
    need(Number.isSafeInteger(trace.gas) && trace.gas > 0 && typeof trace.returnValue === 'string', 'Trace gas/return metadata required');
    need(callCode && typeof callCode === 'object' && !Array.isArray(callCode), 'Pinned call-destination code observations required');
    const codes = new Map();
    for (const [destination, code] of Object.entries(callCode)) {
        const a = address(destination).toLowerCase(); need(!codes.has(a) && typeof code === 'string' && /^0x(?:[0-9a-fA-F]{2})*$/.test(code), 'Invalid or duplicate call code observation'); codes.set(a, code.toLowerCase());
    }
    const blocked = [address(creator).toLowerCase(), address(target).toLowerCase()], calls = [], used = new Set(); let previousDepth = 1, previousOp;
    const fixed = new Set('STOP ADD MUL SUB DIV SDIV MOD SMOD ADDMOD MULMOD EXP SIGNEXTEND LT GT SLT SGT EQ ISZERO AND OR XOR NOT BYTE SHL SHR SAR KECCAK256 SHA3 ADDRESS BALANCE ORIGIN CALLER CALLVALUE CALLDATALOAD CALLDATASIZE CALLDATACOPY CODESIZE CODECOPY GASPRICE EXTCODESIZE EXTCODECOPY RETURNDATASIZE RETURNDATACOPY EXTCODEHASH BLOCKHASH COINBASE TIMESTAMP NUMBER PREVRANDAO DIFFICULTY GASLIMIT CHAINID SELFBALANCE BASEFEE BLOBHASH BLOBBASEFEE POP MLOAD MSTORE MSTORE8 SLOAD SSTORE JUMP JUMPI PC MSIZE GAS JUMPDEST TLOAD TSTORE MCOPY CALL CALLCODE RETURN DELEGATECALL STATICCALL REVERT INVALID'.split(' '));
    for (const [i, step] of trace.structLogs.entries()) {
        need(step && Number.isInteger(step.depth) && step.depth >= 1 && step.depth <= 1024 && (i !== 0 || step.depth === 1) && step.depth <= previousDepth + 1 &&
            Number.isSafeInteger(step.pc) && step.pc >= 0 && typeof step.op === 'string' && !step.error, 'Unsupported or incomplete trace frame');
        need(fixed.has(step.op) || /^(?:PUSH(?:[0-9]|[12][0-9]|3[0-2])|DUP(?:[1-9]|1[0-6])|SWAP(?:[1-9]|1[0-6])|LOG[0-4])$/.test(step.op), 'Unsupported trace opcode or nested creation/destruction');
        if (step.depth > previousDepth) need(['CALL', 'CALLCODE', 'DELEGATECALL', 'STATICCALL'].includes(previousOp), 'Unmodeled nested trace entry');
        previousDepth = step.depth; previousOp = step.op;
        if (['CALL', 'CALLCODE', 'DELEGATECALL', 'STATICCALL'].includes(step.op)) {
            need(Array.isArray(step.stack) && step.stack.length >= 2 && typeof step.stack.at(-2) === 'string' && /^(?:0x)?[0-9a-fA-F]{1,64}$/.test(step.stack.at(-2)), 'Call stack required for no-invocation proof');
            const to = E.getAddress(E.toBeHex(BigInt('0x' + step.stack.at(-2).replace(/^0x/, '')) & ((1n << 160n) - 1n), 20));
            need(!blocked.includes(to.toLowerCase()), 'Trace invokes creator or marker target');
            const code = codes.get(to.toLowerCase()); need(code !== undefined, 'Missing pinned call-destination code');
            need(!code.startsWith('0xef0100'), 'Marker-bearing callee requires a separately modeled execution graph'); used.add(to.toLowerCase());
            calls.push({ index: i, depth: step.depth, opcode: step.op, to });
        }
    }
    need(used.size === codes.size, 'Extraneous call-destination code observation');
    need(['STOP', 'RETURN'].includes(trace.structLogs.at(-1).op) && trace.structLogs.at(-1).depth === 1, 'Top-level trace termination required');
    return { schema: 'agialpha.local-no-origin-invocation-trace.v1', traceSha256: digest(trace), steps: trace.structLogs.length, gas: trace.gas, callCodeSha256: digest(callCode), invocations: { creator: 0, target: 0 }, calls,
        scope: 'Complete supplied local-engine trace only; trusted trace provenance required, no custody or Mainnet proof' };
}
module.exports = { MARKER, validateSender, qualificationScope, validateEvidence, analyzeTrace };
