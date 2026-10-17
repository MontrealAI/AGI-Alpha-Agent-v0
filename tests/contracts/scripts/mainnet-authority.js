// SPDX-License-Identifier: Apache-2.0
// Candidate v2: unsigned plans and read-only evidence. No signer or send method.
// v1 and the October 11 archive intentionally retain their original semantics.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const ethers = require("ethers");
const legacy = require("./mainnet");
const { assertOutsideCheckout } = require("./authority-paths");
const { AGIALPHA_ADDRESS: TOKEN } = require("../../../token.config");
const { ENS, WRAPPER, roots, canonical } = legacy;
const NAMES = ["AscensionAccess", "NovaSeed", "AscensionRiskOracle", "AscensionJobMarket", "AscensionMark"];
const OWNED = ["AscensionAccess", "AscensionRiskOracle", "AscensionJobMarket"];
// Read and integrity-check the archive; never generate actions against its deployed graph.
// Arbitrary existing addresses are additionally excluded by code/nonce preflight checks.
const HISTORICAL_GRAPH = Object.freeze(Object.values(require("./mainnet-record").loadRecord().record.contracts)
    .map(record => ethers.getAddress(record.address)));
const CONVENTIONAL = "conventional-eoa-direct-create.v1";
const EMPTY = "empty-eoa-direct-create.v1";
const DELEGATED = "delegated-eoa-direct-create.v1";
const origination = require("./authority-origination");
const MARKER = origination.MARKER;
const POLICY = "agialpha.zero-retained-creator-authority.v2";
const MAX_TRANSACTION_GAS = 16777216n; // EIP-7825, active on mainnet Osaka.
const digest = x => crypto.createHash("sha256").update(typeof x === "string" ? x : canonical(x)).digest("hex");
function demand(ok, message) { if (!ok) { const error = Error(message); error.publicMessage = true; throw error; } }
function exact(x, fields) { demand(x && typeof x === "object" && !Array.isArray(x) && Object.keys(x).length === fields.length && Object.keys(x).every(k => fields.includes(k)), "Missing or unsupported fields"); }
function addr(x) { let a; try { a = ethers.getAddress(x); } catch { demand(false, "Invalid address"); } demand(a !== ethers.ZeroAddress, "Zero address"); return a; }
function same(a, b, label) { demand(String(a).toLowerCase() === String(b).toLowerCase(), `Mismatch: ${label}`); }
function uint(x, min = 0) { demand(Number.isSafeInteger(x) && x >= min, "Invalid safe integer"); }
function quantity(x) { demand(typeof x === "string" && /^(0|[1-9][0-9]*)$/.test(x) && BigInt(x) < 2n ** 256n, "Invalid decimal quantity"); return BigInt(x); }
function hash(x) { demand(typeof x === "string" && /^0x[0-9a-fA-F]{64}$/.test(x) && x !== ethers.ZeroHash, "Missing reviewed nonzero hash"); }
function sha(x) { demand(typeof x === "string" && /^[0-9a-f]{64}$/.test(x) && x !== "0".repeat(64), "Missing evidence SHA-256"); }
function bytes(x) { demand(typeof x === "string" && /^0x(?:[0-9a-fA-F]{2})*$/.test(x), "Invalid bytes"); }
function block(x) { exact(x, ["number", "hash"]); uint(x.number, 1); hash(x.hash); }
function seal(payload) { return { ...payload, payloadSha256: digest(payload) }; }
function checkSeal(x) { const { payloadSha256, ...payload } = x; same(digest(payload), payloadSha256, "payload checksum"); }
function validateConfig(c) {
    exact(c, ["schema", "chainId", "deployer", "nonce", "block", "governor", "dependencies", "rootOwners", "parameters", "sender", "envelope"]);
    demand(c.schema === "agialpha.mainnet.config.v2" && c.chainId === 1, "Explicit v2 Ethereum mainnet configuration required");
    addr(c.deployer); uint(c.nonce); demand(c.nonce <= Number.MAX_SAFE_INTEGER - 5, "Nonce overflow"); block(c.block);
    exact(c.governor, ["kind", "address", "addressAcknowledgement"]);
    demand(c.governor.kind === "ledger-eoa", "Only explicitly acknowledged EOA governance is modeled in v2");
    const governor = addr(c.governor.address);
    demand(c.governor.address === governor && c.governor.addressAcknowledgement === governor, "Acknowledge the exact selected checksummed governor");
    demand(addr(c.deployer) !== governor, "Creator and governor must be separate");
    exact(c.dependencies, ["token", "ens", "wrapper"]);
    for (const [key, value] of Object.entries({ token: TOKEN, ens: ENS, wrapper: WRAPPER })) {
        exact(c.dependencies[key], ["address", "codeHash"]); same(addr(c.dependencies[key].address), addr(value), `canonical ${key}`); hash(c.dependencies[key].codeHash);
    }
    exact(c.rootOwners, roots); for (const a of Object.values(c.rootOwners)) addr(a);
    exact(c.parameters, ["minimumValidatorStake", "minimumAgentStake", "quorum", "maximumRiskBps"]);
    for (const key of ["minimumValidatorStake", "minimumAgentStake"]) demand(quantity(c.parameters[key]) > 0n && quantity(c.parameters[key]) < 2n ** 96n, "Invalid stake parameter");
    uint(c.parameters.quorum, 2); demand(c.parameters.quorum <= 15, "Invalid quorum");
    uint(c.parameters.maximumRiskBps); demand(c.parameters.maximumRiskBps <= 10000, "Invalid maximum risk");
    exact(c.envelope, ["gasLimit", "maxFeePerGas", "maxPriorityFeePerGas", "accessList"]);
    demand(quantity(c.envelope.gasLimit) >= 21000n && quantity(c.envelope.maxFeePerGas) > 0n && quantity(c.envelope.maxPriorityFeePerGas) <= quantity(c.envelope.maxFeePerGas), "Invalid reviewed gas or fee bounds");
    demand(quantity(c.envelope.gasLimit) <= MAX_TRANSACTION_GAS, "Osaka EIP-7825 transaction gas cap exceeded");
    demand(Array.isArray(c.envelope.accessList) && c.envelope.accessList.length === 0, "Only an explicit empty access list is supported");
    if ([EMPTY, CONVENTIONAL].includes(c.sender.mode)) exact(c.sender, ["mode"]);
    else if (c.sender.mode === MARKER) {
        origination.validateSender(c.sender, c.deployer);
        demand(!Object.values(c.dependencies).some(d => [addr(c.deployer), addr(c.sender.target)].includes(addr(d.address))), "Origin/target cannot alias a dependency invoked during preflight");
    }
    else {
        exact(c.sender, ["mode", "delegationCode", "target", "targetCodeHash", "stateChecks", "qualification"]);
        demand(c.sender.mode === DELEGATED, "Unsupported sender mode: no factory, smart wallet, batch, relayer, type4 or CREATE2");
        demand(/^0xef0100[0-9a-fA-F]{40}$/.test(c.sender.delegationCode), "Exact 23-byte EIP-7702 indicator required");
        same(addr(c.sender.target), addr(`0x${c.sender.delegationCode.slice(8)}`), "delegation target");
        demand(addr(c.sender.target) !== addr(c.deployer), "Self-delegation unsupported"); hash(c.sender.targetCodeHash);
        demand(Array.isArray(c.sender.stateChecks) && c.sender.stateChecks.length > 0 && c.sender.stateChecks.length <= 32, "Reviewed delegate authority/state checks required");
        const checks = new Set();
        for (const s of c.sender.stateChecks) {
            exact(s, ["to", "data", "resultHash"]); addr(s.to); bytes(s.data); demand(s.data.length >= 10, "State getter calldata required"); hash(s.resultHash);
            const key = `${s.to}:${s.data}`.toLowerCase(); demand(!checks.has(key), "Duplicate state check"); checks.add(key);
        }
        exact(c.sender.qualification, ["consensusEvidenceSha256", "forkEvidenceSha256", "delegateReviewSha256"]);
        for (const value of Object.values(c.sender.qualification)) sha(value);
    }
    return c;
}
function validateJournal(c, j) {
    exact(j, ["schema", "journalId", "revision", "chainId", "sender", "scope", "block", "latestNonce", "pendingNonce", "allocations"]);
    demand(j.schema === "ethereum.cross-project-nonce-journal.v1" && typeof j.journalId === "string" && /^[A-Za-z0-9_-]{1,80}$/.test(j.journalId), "Coordinated nonce journal required");
    uint(j.revision, 1); same(j.chainId, 1, "journal chain"); same(addr(j.sender), addr(c.deployer), "journal sender"); block(j.block);
    demand(canonical(j.block) === canonical(c.block), "Journal and configuration evidence pin differ");
    demand(canonical(j.scope) === canonical(["alpha", "jobs", "manager"]), "Shared Alpha, Jobs and Manager reconciliation required");
    demand(j.latestNonce === c.nonce && j.pendingNonce === c.nonce, "Journal starting nonce or pending transactions mismatch");
    demand(Array.isArray(j.allocations) && j.allocations.length > 0, "Nonce allocation required");
    const ranges = j.allocations.map(a => {
        exact(a, ["project", "startNonce", "count"]); demand(j.scope.includes(a.project), "Unknown journal project"); uint(a.startNonce); uint(a.count, 1);
        demand(a.startNonce <= Number.MAX_SAFE_INTEGER - a.count, "Journal nonce overflow"); return a;
    }).sort((a, b) => a.startNonce - b.startNonce);
    for (let i = 1; i < ranges.length; ++i) demand(ranges[i].startNonce >= ranges[i - 1].startNonce + ranges[i - 1].count, "Overlapping cross-project nonce allocation");
    const selected = ranges.filter(a => a.project === "alpha");
    demand(selected.length === 1 && selected[0].startNonce === c.nonce && selected[0].count === 5, "Exactly five contiguous Alpha CREATE nonces required");
    return j;
}
function compiledContracts() {
    const compiled = legacy.compiledContracts();
    for (const name of NAMES) {
        const directory = path.resolve(__dirname, `../artifacts/contracts/ascension/${name}.sol`);
        const debug = JSON.parse(fs.readFileSync(path.join(directory, `${name}.dbg.json`)));
        const build = JSON.parse(fs.readFileSync(path.resolve(directory, debug.buildInfo)));
        const ids = {};
        function visit(node) {
            if (!node || typeof node !== "object") return;
            if (node.nodeType === "VariableDeclaration" && node.mutability === "immutable") ids[node.id] = node;
            for (const value of Object.values(node)) if (value && typeof value === "object") {
                if (Array.isArray(value)) value.forEach(visit); else visit(value);
            }
        }
        Object.values(build.output.sources).forEach(source => visit(source.ast));
        compiled.records[name].immutableGetters = Object.fromEntries(Object.keys(compiled.records[name].immutableReferences).map(id => {
            demand(ids[id]?.visibility === "public", "Unmodeled immutable declaration"); return [id, ids[id].name];
        }));
    }
    return compiled;
}
function constructorArguments(c, a) {
    const p = c.parameters, g = c.governor.address;
    return [[ENS, WRAPPER, g], [a.AscensionAccess], [a.AscensionAccess, a.NovaSeed, p.minimumValidatorStake, p.quorum, p.maximumRiskBps, g],
        [a.AscensionAccess, a.AscensionRiskOracle, p.minimumAgentStake, g], [a.NovaSeed, a.AscensionAccess, a.AscensionRiskOracle, a.AscensionJobMarket]];
}
function planComponents(config, compiled, revision, journal) {
    validateConfig(config); validateJournal(config, journal);
    exact(revision, ["commit", "tree", "lockSha256"]); demand(/^[a-f0-9]{40}$/.test(revision.commit) && /^[a-f0-9]{40}$/.test(revision.tree), "Exact source commit and tree required"); sha(revision.lockSha256);
    const addresses = Object.fromEntries(NAMES.map((name, i) => [name, ethers.getCreateAddress({ from: config.deployer, nonce: config.nonce + i })]));
    demand(Object.values(addresses).every(a => !HISTORICAL_GRAPH.includes(a)), "Previously deployed graph is protected; choose a fresh creation nonce/address plan");
    if (config.sender.mode === MARKER) demand(Object.values(addresses).every(a => ![addr(config.deployer), addr(config.sender.target)].includes(a)), "Origin/target cannot alias the new graph");
    const args = constructorArguments(config, addresses);
    const transactions = NAMES.map((name, i) => ({ name, expectedAddress: addresses[name], constructorArguments: args[i],
        envelope: { type: 2, chainId: 1, from: config.deployer, nonce: config.nonce + i, to: null, value: "0",
            data: ethers.concat([compiled.records[name].bytecode, new ethers.Interface(compiled.records[name].abi).encodeDeploy(args[i])]), ...config.envelope } }));
    return { addresses, transactions };
}
function qualificationRequest(config, compiled, revision, journal) {
    demand(config?.sender?.mode === MARKER && config.sender.qualification === null, "Scope-only input requires marker mode and explicit null qualification");
    const c = structuredClone(config);
    // This sentinel permits only generation of an unsigned review request, never a qualified plan.
    c.sender.qualification = { consensusEvidenceSha256: digest("UNQUALIFIED SCOPE REQUEST"), directExecutionEvidenceSha256: digest("UNQUALIFIED SCOPE REQUEST") };
    const { transactions } = planComponents(c, compiled, revision, journal);
    return { schema: "agialpha.marker-direct-qualification-request.v1", scope: origination.qualificationScope(c, compiled, revision, transactions),
        readyToSign: false, readyToBroadcast: false, warning: "A source-bound review request only. Independently accepted reports and artifacts are still required." };
}
async function makePlan(config, compiled, revision, journal, directOriginationEvidence) {
    const { addresses, transactions } = planComponents(config, compiled, revision, journal);
    if (config.sender.mode === MARKER) origination.validateEvidence(config, compiled, revision, transactions, directOriginationEvidence);
    else demand(directOriginationEvidence === undefined, "Only marker direct-origination accepts its evidence bundle");
    const governanceCalls = [["AscensionRiskOracle", "bindMarketplace", addresses.AscensionJobMarket], ["AscensionJobMarket", "bindMark", addresses.AscensionMark]]
        .map(([name, method, argument]) => ({ name, method, argument, from: config.governor.address, to: addresses[name], chainId: 1, value: "0", operation: 0,
            data: new ethers.Interface(compiled.records[name].abi).encodeFunctionData(method, [argument]) }));
    return seal({ schema: "agialpha.mainnet.unsigned-plan.v2", policy: POLICY, config, revision, journal, journalSha256: digest(journal),
        addresses, transactions, governanceCalls, ...(config.sender.mode === CONVENTIONAL ? { originationAssurance: 'Conventional transaction correctness only; no wallet qualification, delegate target safety, no-invocation or custody assurance' } : {}), ...(config.sender.mode === MARKER ? { directOriginationEvidence } : {}),
        executionPolicy: { hardfork: "osaka", maximumTransactionGas: MAX_TRANSACTION_GAS.toString(), envelope: "type2-direct-create", scope: "Non-blob transaction execution only; not full consensus or finality qualification" }, contracts: compiled.records, builds: compiled.builds, readyToBroadcast: false,
        limitations: ["Functional candidate; hashes identify evidence but do not certify review quality or wallet custody.", "No consensus/fork qualification, independent security review or activation approval is implied.",
            "The journal is coordinated evidence, not an on-chain nonce reservation or a lock against other signers.", "Ownership is constructor-set transferable storage. Dependency immutables and one-time graph bindings have different semantics."] });
}
// revision is a caller-owned trust anchor, obtained independently of this plan (for the CLI,
// require('./authority-revision').reviewedRevision() observes a clean checkout). A plan checksum cannot attest its label.
async function checkPlan(plan, compiled = compiledContracts(), revision) {
    demand(revision !== undefined, "An independently observed source revision is required");
    checkSeal(plan);
    demand(canonical(plan.revision) === canonical(revision), "Plan/source/constructor mismatch: independently observed revision differs"); demand(plan.schema === "agialpha.mainnet.unsigned-plan.v2" && plan.policy === POLICY && plan.readyToBroadcast === false, "Wrong candidate policy");
    const rebuilt = await makePlan(plan.config, compiled, revision, plan.journal, plan.directOriginationEvidence);
    demand(canonical(plan) === canonical(rebuilt), "Plan/source/constructor mismatch"); return plan;
}
function validateEnvelope(expected, actual) {
    exact(actual, ["type", "chainId", "from", "nonce", "to", "value", "data", "gasLimit", "maxFeePerGas", "maxPriorityFeePerGas", "accessList"]);
    demand(actual.type === 2 && actual.to === null, "Only direct type-2 CREATE is supported");
    for (const key of Object.keys(expected)) demand(canonical(actual[key]) === canonical(expected[key]), `Envelope mismatch: ${key}`);
    return true;
}
// This schema is shared with Jobs/Manager. It is an intent, never permission to sign.
function creationIntents(plan) {
    return plan.transactions.map(tx => ({ schema: "creation-intent-v1", chainId: 1, creator: ethers.getAddress(plan.config.deployer),
        transactionMode: "eoa-create", nonce: tx.envelope.nonce, to: null, value: "0", dataHash: ethers.keccak256(tx.envelope.data),
        startBlock: plan.config.block.number, address: tx.expectedAddress, gasLimit: tx.envelope.gasLimit }));
}
function signingBoundary(plan) {
    return { schema: "agialpha.external-signing-boundary.v1", planSha256: plan.payloadSha256,
        senderPolicySha256: digest(plan.config.sender), envelopeSha256: plan.transactions.map(tx => digest(tx.envelope)), intents: creationIntents(plan),
        lock: { environment: "DEPLOYMENT_LOCK_DIRECTORY", key: `1-${plan.config.deployer.toLowerCase()}`, schema: "creator-nonce-lock-v1",
            keys: [...new Set([plan.config.deployer, plan.config.governor.address].map(a => `1-${a.toLowerCase()}`))].sort(),
            acquisitionOrder: "Deduplicate and lexically sort all actual sender keys, including the governor, before acquiring any lock",
            requiredScope: "Exclusive across Alpha, Jobs and Manager through creation and governor binding; never auto-break a stale lock" },
        requiredExecutorChecks: ["Acquire the common atomic-directory lock before nonce inspection or signing and fsync the journal intent before submission",
            plan.config.sender.mode === CONVENTIONAL ? "Revalidate exact plan/envelope and latest=pending nonce while holding the lock" : "Revalidate exact plan/envelope/delegation and latest=pending nonce while holding the lock",
            "Governor calls also require their actor lock, separately reviewed current nonce/fees and a durable exact CALL intent before signing; never reuse the creator nonce journal for them",
            "Intent without a proven canonical matching receipt after possible submission is unresolved: read-only reconcile; never blindly retry",
            "Retain exact transaction hashes and canonical receipts; permit only the contiguous receipt prefix; never silently skip a consumed nonce",
            "Operator must exclude signing from other machines/wallets; the filesystem lock does not enforce this"],
        executorIntegrated: false, readyToBroadcast: false };
}
function expectedState(plan, bound = true) {
    const bindings = typeof bound === "boolean" ? (bound ? 2 : 0) : bound;
    demand(Number.isInteger(bindings) && bindings >= 0 && bindings <= 2, "Invalid governor binding prefix");
    const a = plan.addresses, g = plan.config.governor.address, p = plan.config.parameters;
    return {
        AscensionAccess: { owner: g, pendingOwner: ethers.ZeroAddress, ens: ENS, wrapper: WRAPPER },
        NovaSeed: { access: a.AscensionAccess, nextId: "0" },
        AscensionRiskOracle: { owner: g, pendingOwner: ethers.ZeroAddress, access: a.AscensionAccess, seed: a.NovaSeed, token: TOKEN,
            marketplace: bindings >= 1 ? a.AscensionJobMarket : ethers.ZeroAddress, minimumStake: p.minimumValidatorStake, quorum: String(p.quorum), maximumRiskBps: String(p.maximumRiskBps) },
        AscensionJobMarket: { owner: g, pendingOwner: ethers.ZeroAddress, access: a.AscensionAccess, oracle: a.AscensionRiskOracle, token: TOKEN,
            mark: bindings >= 2 ? a.AscensionMark : ethers.ZeroAddress, minimumStake: p.minimumAgentStake, nextId: "0" },
        AscensionMark: { seed: a.NovaSeed, access: a.AscensionAccess, oracle: a.AscensionRiskOracle, jobs: a.AscensionJobMarket, token: TOKEN }
    };
}
function expectedRuntime(record, values) {
    const runtime = ethers.getBytes(record.runtime);
    for (const [id, references] of Object.entries(record.immutableReferences)) {
        const getter = record.immutableGetters[id]; demand(Object.hasOwn(values, getter), "Unmodeled immutable getter");
        const encoded = ethers.getBytes(ethers.zeroPadValue(ethers.toBeHex(BigInt(values[getter])), 32));
        for (const { start, length } of references) {
            demand(Number.isSafeInteger(start) && start >= 0 && length === 32 && start + length <= runtime.length, "Invalid immutable range"); runtime.set(encoded, start);
        }
    }
    return ethers.hexlify(runtime);
}
async function atBlock(rpc, pin) {
    const found = await rpc("eth_getBlockByNumber", [ethers.toQuantity(pin.number), false]);
    demand(found && found.hash, "Missing canonical block"); same(found.hash, pin.hash, "canonical block hash");
    same(BigInt(found.number), BigInt(pin.number), "canonical block number"); return found;
}
async function call(rpc, to, signature, args, tag) {
    const abi = new ethers.Interface([`function ${signature}`]), fn = abi.fragments[0];
    return abi.decodeFunctionResult(fn, await rpc("eth_call", [{ to, data: abi.encodeFunctionData(fn, args) }, tag]));
}
async function verifyContract(plan, name, rpc, pin, bound) {
    const values = expectedState(plan, bound)[name], record = plan.contracts[name], target = plan.addresses[name], tag = ethers.toQuantity(pin.number);
    const code = await rpc("eth_getCode", [target, tag]); same(code, expectedRuntime(record, values), `${name} exact runtime/immutables`);
    const abi = new ethers.Interface(record.abi);
    for (const [getter, expected] of Object.entries(values)) {
        const raw = await rpc("eth_call", [{ to: target, data: abi.encodeFunctionData(getter) }, tag]);
        same(abi.decodeFunctionResult(getter, raw)[0], expected, `${name}.${getter}`);
    }
    return { name, address: target, codeHash: ethers.keccak256(code), values };
}
async function inspectEnvironment(c, rpc, pin, checkCreator) {
    const tag = ethers.toQuantity(pin.number);
    const observedBlock = await atBlock(rpc, pin);
    demand(observedBlock.gasLimit && BigInt(c.envelope.gasLimit) <= BigInt(observedBlock.gasLimit), "Reviewed transaction exceeds observed block gas limit");
    for (const [label, dep] of Object.entries(c.dependencies)) {
        const code = await rpc("eth_getCode", [dep.address, tag]); demand(code !== "0x", `${label} missing code`); same(ethers.keccak256(code), dep.codeHash, `${label} code`);
    }
    same((await call(rpc, TOKEN, "decimals() view returns (uint8)", [], tag))[0], 18, "token decimals");
    demand(await rpc("eth_getCode", [c.governor.address, tag]) === "0x", "Selected governor has code/delegation");
    for (const name of roots) {
        const node = ethers.namehash(name);
        let owner = (await call(rpc, ENS, "owner(bytes32) view returns (address)", [node], tag))[0];
        if (addr(owner) === addr(WRAPPER)) {
            const data = await call(rpc, WRAPPER, "getData(uint256) view returns (address owner,uint32 fuses,uint64 expiry)", [BigInt(node)], tag);
            const b = await atBlock(rpc, pin); demand(data.expiry > BigInt(b.timestamp), "Expired ENS root"); owner = data.owner;
        }
        same(owner, c.rootOwners[name], `ENS ${name}`);
    }
    if (checkCreator) {
        // Conventional mode observes origin code without wallet-specific admission.
        // Ethereum validates eligibility; no target/state/custody assurance is claimed.
        const code = await rpc("eth_getCode", [c.deployer, tag]);
        if (c.sender.mode === EMPTY) demand(code === "0x", "Empty-code mode rejects delegated/contract sender");
        else if (c.sender.mode !== CONVENTIONAL) {
            same(code, c.sender.delegationCode, "delegation bytes");
            const targetCode = await rpc("eth_getCode", [c.sender.target, tag]); demand(targetCode !== "0x", "Missing delegation target code");
            same(ethers.keccak256(targetCode), c.sender.targetCodeHash, "delegation target code");
            if (c.sender.mode === DELEGATED) for (const s of c.sender.stateChecks) same(ethers.keccak256(await rpc("eth_call", [{ to: s.to, data: s.data }, tag])), s.resultHash, "delegate authority/state drift");
            else for (const s of c.sender.storageChecks) same(await rpc("eth_getStorageAt", [s.address, s.slot, tag]), s.value, "selected origin storage drift");
        }
    }
    await atBlock(rpc, pin);
}
async function receiptEvidence(plan, index, txHash, rpc, acceptancePin) {
    hash(txHash); const expected = plan.transactions[index], tx = await rpc("eth_getTransactionByHash", [txHash]), receipt = await rpc("eth_getTransactionReceipt", [txHash]);
    demand(tx && receipt && receipt.status === "0x1", "Missing or unsuccessful creation receipt");
    same(tx.hash, txHash, "transaction hash"); same(receipt.transactionHash, txHash, "receipt hash");
    demand(tx.to === null && receipt.to === null && BigInt(tx.type) === 2n && BigInt(receipt.type) === 2n, "Receipt is not direct type-2 CREATE");
    demand(!tx.authorizationList && !tx.blobVersionedHashes, "Unsupported transaction authorization/blob fields");
    const actual = { type: 2, chainId: Number(BigInt(tx.chainId)), from: tx.from, nonce: Number(BigInt(tx.nonce)), to: tx.to, value: BigInt(tx.value).toString(), data: tx.input,
        gasLimit: BigInt(tx.gas).toString(), maxFeePerGas: BigInt(tx.maxFeePerGas).toString(), maxPriorityFeePerGas: BigInt(tx.maxPriorityFeePerGas).toString(), accessList: tx.accessList };
    // Address case is representation only; exact recovered signer is checked below.
    actual.from = ethers.getAddress(actual.from); const canonicalExpected = { ...expected.envelope, from: ethers.getAddress(expected.envelope.from) };
    validateEnvelope(canonicalExpected, actual);
    const signed = ethers.Transaction.from({ type: 2, chainId: actual.chainId, nonce: actual.nonce, to: null, value: actual.value, data: actual.data, gasLimit: actual.gasLimit,
        maxFeePerGas: actual.maxFeePerGas, maxPriorityFeePerGas: actual.maxPriorityFeePerGas, accessList: [], signature: { r: tx.r, s: tx.s, yParity: Number(BigInt(tx.yParity ?? tx.v)) } });
    same(signed.hash, txHash, "reconstructed signed transaction"); same(signed.from, plan.config.deployer, "recovered creation signer");
    same(receipt.from, plan.config.deployer, "receipt creator"); same(receipt.contractAddress, expected.expectedAddress, "created address");
    same(tx.blockHash, receipt.blockHash, "transaction/receipt block"); same(tx.blockNumber, receipt.blockNumber, "transaction/receipt block number");
    same(tx.transactionIndex, receipt.transactionIndex, "transaction index");
    const pin = { number: Number(BigInt(receipt.blockNumber)), hash: receipt.blockHash };
    demand(pin.number > plan.config.block.number && pin.number <= acceptancePin.number, "Receipt outside finalized campaign interval");
    await atBlock(rpc, pin);
    demand(await rpc("eth_getCode", [plan.config.governor.address, ethers.toQuantity(pin.number)]) === "0x", "Governor code at creation block");
    await verifyContract(plan, expected.name, rpc, pin, false);
    if (OWNED.includes(expected.name)) {
        const abi = new ethers.Interface(plan.contracts[expected.name].abi);
        const events = receipt.logs.filter(log => log.address.toLowerCase() === expected.expectedAddress.toLowerCase()).map(log => abi.parseLog(log));
        demand(events.length === 1 && events[0]?.name === "OwnershipTransferred", "Unexpected constructor events");
        same(events[0].args.previousOwner, ethers.ZeroAddress, "initial previous owner"); same(events[0].args.newOwner, plan.config.governor.address, "direct constructor governor");
    } else demand(receipt.logs.length === 0, "Unexpected constructor logs");
    return { index, transactionHash: txHash, block: pin, transactionIndex: Number(BigInt(receipt.transactionIndex)), expectedAddress: expected.expectedAddress };
}
async function preflight(plan, rpc, revision, creationHashes = [], currentJournal = plan.journal, governanceHashes = []) {
    await checkPlan(plan, undefined, revision); validateJournal(plan.config, currentJournal);
    demand(canonical(currentJournal) === canonical(plan.journal), "Journal changed; stop and reconcile/rebuild");
    demand(Array.isArray(creationHashes) && creationHashes.length <= 5 && new Set(creationHashes).size === creationHashes.length, "Contiguous creation receipt prefix required");
    demand(Array.isArray(governanceHashes) && governanceHashes.length <= 2 && (governanceHashes.length === 0 || creationHashes.length === 5) &&
        new Set([...creationHashes, ...governanceHashes]).size === creationHashes.length + governanceHashes.length, "Contiguous seven-operation prefix required");
    same(BigInt(await rpc("eth_chainId", [])), 1n, "chain");
    const final = await rpc("eth_getBlockByNumber", ["finalized", false]); demand(final && BigInt(final.number) >= BigInt(plan.config.block.number), "Finalized plan pin required");
    const finalPin = { number: Number(BigInt(final.number)), hash: final.hash };
    await inspectEnvironment(plan.config, rpc, plan.config.block, true);
    const progress = [];
    for (const [i, h] of creationHashes.entries()) progress.push(await receiptEvidence(plan, i, h, rpc, finalPin));
    const bindings = [];
    for (const [i, h] of governanceHashes.entries()) bindings.push(await verifyGovernanceReceipt(plan, i, h, rpc, finalPin));
    const ordered = [...progress, ...bindings]; requireOrdered(ordered);
    const latest = await rpc("eth_getBlockByNumber", ["latest", false]); demand(latest?.hash && latest.timestamp, "Latest block metadata required");
    const latestPin = { number: Number(BigInt(latest.number)), hash: latest.hash };
    await inspectEnvironment(plan.config, rpc, latestPin, true);
    const next = plan.config.nonce + creationHashes.length;
    for (const tag of ["latest", "pending"]) same(BigInt(await rpc("eth_getTransactionCount", [plan.config.deployer, tag])), BigInt(next), `${tag} creator nonce drift`);
    for (let i = 0; i < 5; ++i) {
        if (i < creationHashes.length) await verifyContract(plan, NAMES[i], rpc, latestPin, bindings.length);
        else {
            demand(await rpc("eth_getCode", [plan.transactions[i].expectedAddress, "latest"]) === "0x", "Predicted address occupied");
            same(BigInt(await rpc("eth_getTransactionCount", [plan.transactions[i].expectedAddress, "latest"])), 0n, "Predicted address nonzero nonce");
        }
    }
    if (progress.length) await verifyCampaignEvents(plan, rpc, latestPin, progress, bindings);
    let nextOperation = null;
    if (progress.length < 5) nextOperation = { index: progress.length, sender: plan.config.deployer, nonce: next };
    else if (bindings.length < 2) {
        const pending = BigInt(await rpc("eth_getTransactionCount", [plan.config.governor.address, "pending"]));
        same(BigInt(await rpc("eth_getTransactionCount", [plan.config.governor.address, "latest"])), pending, "governor pending nonce drift");
        demand(pending <= BigInt(Number.MAX_SAFE_INTEGER), "Governor nonce overflow");
        if (bindings.length) same(pending, BigInt(bindings.at(-1).nonce + 1), "governor nonce changed between bindings");
        nextOperation = { index: 5 + bindings.length, sender: plan.config.governor.address, nonce: Number(pending) };
    }
    const end = await rpc("eth_getBlockByNumber", ["latest", false]); same(end.hash, latest.hash, "latest block changed during preflight; repeat");
    await atBlock(rpc, plan.config.block); await atBlock(rpc, finalPin);
    return seal({ schema: "agialpha.mainnet.preflight.v2", observedRevision: revision, planSha256: plan.payloadSha256, journalSha256: plan.journalSha256,
        progress, bindings, nextOperation, signingBoundary: signingBoundary(plan), nextIndex: creationHashes.length, nextNonce: next, observedAtBlock: { ...latestPin, timestamp: Number(BigInt(latest.timestamp)) },
        preflightPassed: true, readyToBroadcast: false, externalTransactions: false,
        limitation: "Read-only transient evidence. A post-check race can still replace a transaction, consume a nonce or change delegation. A partial run must never restart at nonce zero or skip missing receipts." });
}
async function verifyGovernanceReceipt(plan, index, txHash, rpc, pin) {
    hash(txHash); const expected = plan.governanceCalls[index], tx = await rpc("eth_getTransactionByHash", [txHash]), receipt = await rpc("eth_getTransactionReceipt", [txHash]);
    demand(tx && receipt && receipt.status === "0x1" && BigInt(tx.type) === 2n && BigInt(receipt.type) === 2n, "Successful direct governor type-2 CALL required");
    for (const [key, value] of Object.entries({ from: expected.from, to: expected.to, input: expected.data, hash: txHash })) same(tx[key], value, `governor ${key}`);
    same(BigInt(tx.chainId), 1n, "governor chain"); same(BigInt(tx.value), 0n, "governor value");
    demand(BigInt(tx.gas) <= MAX_TRANSACTION_GAS, "Governor transaction exceeds Osaka gas cap");
    demand(!tx.authorizationList && !tx.blobVersionedHashes && Array.isArray(tx.accessList) && tx.accessList.length === 0, "Unsupported governor envelope");
    const signed = ethers.Transaction.from({ type: 2, chainId: 1, nonce: BigInt(tx.nonce), to: tx.to, value: 0n, data: tx.input, gasLimit: BigInt(tx.gas), maxFeePerGas: BigInt(tx.maxFeePerGas),
        maxPriorityFeePerGas: BigInt(tx.maxPriorityFeePerGas), accessList: [], signature: { r: tx.r, s: tx.s, yParity: Number(BigInt(tx.yParity ?? tx.v)) } });
    same(signed.hash, txHash, "governor signed transaction"); same(signed.from, expected.from, "recovered governor");
    same(receipt.from, expected.from, "governor receipt sender"); same(receipt.to, expected.to, "governor receipt destination"); same(receipt.transactionHash, txHash, "governor receipt hash");
    same(tx.blockHash, receipt.blockHash, "governor block"); same(tx.blockNumber, receipt.blockNumber, "governor block number");
    same(tx.transactionIndex, receipt.transactionIndex, "governor transaction index"); demand(receipt.contractAddress === null, "Governor call cannot create a contract");
    const b = { number: Number(BigInt(receipt.blockNumber)), hash: receipt.blockHash };
    demand(b.number > plan.config.block.number && b.number <= pin.number, "Governor receipt outside acceptance interval"); await atBlock(rpc, b);
    demand(await rpc("eth_getCode", [expected.from, ethers.toQuantity(b.number)]) === "0x", "Governor code at binding block");
    const abi = new ethers.Interface(plan.contracts[expected.name].abi), logs = receipt.logs;
    demand(logs.length === 1, "Unexpected governance receipt logs"); same(logs[0].address, expected.to, "binding event address");
    const event = abi.parseLog(logs[0]); demand(event?.name === (index === 0 ? "MarketplaceBound" : "MarkBound"), "Binding event required"); same(event.args[0], expected.argument, "binding event argument");
    return { transactionHash: txHash, nonce: Number(BigInt(tx.nonce)), block: b, transactionIndex: Number(BigInt(receipt.transactionIndex)) };
}
function requireOrdered(ordered) {
    for (let i = 1; i < ordered.length; ++i) demand(ordered[i].block.number > ordered[i - 1].block.number ||
        (ordered[i].block.number === ordered[i - 1].block.number && ordered[i].transactionIndex > ordered[i - 1].transactionIndex), "Noncontiguous/reordered campaign evidence");
}
async function verifyCampaignEvents(plan, rpc, pin, creations, bindings) {
    const a = plan.addresses, tag = ethers.toQuantity(pin.number), ordered = [...creations, ...bindings];
    const evidence = { creationHashes: creations.map(x => x.transactionHash), governanceHashes: bindings.map(x => x.transactionHash) };
    // Fresh commissioning boundary: require exactly the three direct ownership events and two bindings.
    // Any admission, registration, NFT/operator approval, participant action or unknown event stops acceptance.
    const logs = await rpc("eth_getLogs", [{ address: Object.values(a), fromBlock: ethers.toQuantity(creations[0].block.number), toBlock: tag }]);
    demand(Array.isArray(logs) && logs.length === creations.filter(row => OWNED.includes(NAMES[row.index])).length + bindings.length, "Unexpected authority/participant/approval events; reconcile the complete interval");
    const eventKeys = new Set();
    for (const log of logs) {
        demand(log.removed === false, "Removed or unqualified event");
        const name = NAMES.find(n => a[n].toLowerCase() === log.address.toLowerCase()); demand(name, "Unknown graph event address");
        const event = new ethers.Interface(plan.contracts[name].abi).parseLog(log); demand(event, "Unknown graph event");
        let expectedHash;
        if (event.name === "OwnershipTransferred" && OWNED.includes(name)) {
            same(event.args.previousOwner, ethers.ZeroAddress, "ownership origin"); same(event.args.newOwner, plan.config.governor.address, "ownership destination"); expectedHash = evidence.creationHashes[NAMES.indexOf(name)];
        } else if (name === "AscensionRiskOracle" && event.name === "MarketplaceBound") { same(event.args[0], a.AscensionJobMarket, "marketplace event"); expectedHash = evidence.governanceHashes[0]; }
        else if (name === "AscensionJobMarket" && event.name === "MarkBound") { same(event.args[0], a.AscensionMark, "MARK event"); expectedHash = evidence.governanceHashes[1]; }
        else demand(false, "Unexpected authority, approval or participant event");
        same(log.transactionHash, expectedHash, "event transaction");
        const key = `${name}:${event.name}`; demand(!eventKeys.has(key), "Duplicate authority event"); eventKeys.add(key);
        const row = ordered.find(x => x.transactionHash.toLowerCase() === expectedHash.toLowerCase()); same(log.blockHash, row.block.hash, "event block hash");
        same(BigInt(log.blockNumber), BigInt(row.block.number), "event block number"); same(BigInt(log.transactionIndex), BigInt(row.transactionIndex), "event transaction index");
    }
    return true;
}
async function verifyAuthority(plan, rpc, evidence, revision) {
    await checkPlan(plan, undefined, revision); exact(evidence, ["creationHashes", "governanceHashes", "acceptanceBlock"]); block(evidence.acceptanceBlock);
    demand(evidence.creationHashes.length === 5 && evidence.governanceHashes.length === 2 && new Set([...evidence.creationHashes, ...evidence.governanceHashes]).size === 7, "Five unique creations and two unique governor bindings required");
    same(BigInt(await rpc("eth_chainId", [])), 1n, "chain");
    const final = await rpc("eth_getBlockByNumber", ["finalized", false]); demand(BigInt(final.number) >= BigInt(evidence.acceptanceBlock.number), "Acceptance block must be finalized");
    const pin = evidence.acceptanceBlock, tag = ethers.toQuantity(pin.number); await atBlock(rpc, pin);
    // Historical creation facts remain valid even after the retired creator changes code or nonce.
    await inspectEnvironment(plan.config, rpc, pin, false);
    const creations = []; for (const [i, h] of evidence.creationHashes.entries()) creations.push(await receiptEvidence(plan, i, h, rpc, pin));
    const bindings = []; for (const [i, h] of evidence.governanceHashes.entries()) bindings.push(await verifyGovernanceReceipt(plan, i, h, rpc, pin));
    const ordered = [...creations, ...bindings];
    for (let i = 1; i < ordered.length; ++i) demand(ordered[i].block.number > ordered[i - 1].block.number || (ordered[i].block.number === ordered[i - 1].block.number && ordered[i].transactionIndex > ordered[i - 1].transactionIndex), "Noncontiguous/reordered campaign evidence");
    const contracts = []; for (const name of NAMES) contracts.push(await verifyContract(plan, name, rpc, pin, true));
    const a = plan.addresses, creator = plan.config.deployer;
    const admission = await call(rpc, a.AscensionAccess, "admission(address) view returns (bytes32 evidence,uint64 until)", [creator], tag);
    same(admission.evidence, ethers.ZeroHash, "creator admission evidence"); same(admission.until, 0, "creator admission expiry");
    same((await call(rpc, a.AscensionAccess, "admitted(address) view returns (bool)", [creator], tag))[0], false, "creator admission");
    for (let role = 0; role < 3; ++role) {
        same((await call(rpc, a.AscensionAccess, "names(address,uint8) view returns (bytes32)", [creator, role], tag))[0], ethers.ZeroHash, "creator registration");
        same((await call(rpc, a.AscensionAccess, "eligible(address,uint8) view returns (bool)", [creator, role], tag))[0], false, "creator eligibility");
        same((await call(rpc, a.AscensionAccess, "roots(uint8) view returns (bytes32)", [role], tag))[0], ethers.namehash(roots[role]), "Access root");
    }
    for (const [name, getters] of [["AscensionRiskOracle", ["stake", "lockedUntil", "activeJobs", "jobCapacity"]], ["AscensionJobMarket", ["stake", "locked", "reputation"]]])
        for (const getter of getters) same((await call(rpc, a[name], `${getter}(address) view returns (uint256)`, [creator], tag))[0], 0, `creator ${name}.${getter}`);
    await verifyCampaignEvents(plan, rpc, pin, creations, bindings);
    await atBlock(rpc, pin);
    return seal({ schema: "agialpha.mainnet.authority-evidence.v2", observedRevision: revision, planSha256: plan.payloadSha256, block: pin, creations, bindings, contracts,
        graphAuthorityVerified: true, creatorDeploymentPrivilege: "none observed in the exact fresh five-contract graph at this block",
        ownership: "Constructor-set Ownable2Step storage, transferable later by the governor; not immutable ownership",
        graphBindings: "Constructor dependency immutables and governor-only one-time bindings",
        readyToBroadcast: false, readyForPublicFunding: false, activationAllowed: false, externalTransactions: false,
        unresolvedGates: ["Independent security review remains separate and is not performed by these functional checks", "External token/proxy/ENS/controller and off-chain authority inventory", ...(plan.config.sender.mode === CONVENTIONAL ? ["Exact-candidate real-dependency fork evidence"] : ["Delegate consensus/wallet qualification and exact-candidate real-dependency fork evidence"]), "Explorer verification acceptance", "Separate operator, economic, participant commissioning and activation approval"] });
}
async function main() {
    const [mode, input, output] = process.argv.slice(2);
    demand(["plan", "qualification-scope"].includes(mode) && input && output && process.argv.length === 5, "Usage: node scripts/mainnet-authority.js plan|qualification-scope CONFIG_AND_JOURNAL.json NEW_OUTPUT.json");
    assertOutsideCheckout(output);
    demand(!fs.existsSync(output), "Refuse to overwrite evidence");
    const revision = require('./authority-revision').reviewedRevision();
    const boundary = require('./authority-input-boundary').createInputBoundary(revision);
    boundary.pinDirectory(path.dirname(path.resolve(output)));
    const data = boundary.readJson(input); exact(data, mode === "plan" && data.config?.sender?.mode === MARKER ? ["config", "journal", "directOriginationEvidence"] : ["config", "journal"]);
    const plan = mode === "qualification-scope" ? qualificationRequest(data.config, boundary.compiled, revision, data.journal) : await makePlan(data.config, boundary.compiled, revision, data.journal, data.directOriginationEvidence);
    boundary.assertCurrent();
    require("./authority-cli").writeNew(output, plan);
    process.stdout.write(JSON.stringify({ output: path.resolve(output), readyToBroadcast: false }) + "\n");
}
module.exports = { CONVENTIONAL, EMPTY, DELEGATED, MARKER, POLICY, MAX_TRANSACTION_GAS, NAMES, OWNED, HISTORICAL_GRAPH, digest, seal, validateConfig, validateJournal, compiledContracts, qualificationRequest, makePlan, checkPlan, validateEnvelope,
    creationIntents, signingBoundary, expectedState, expectedRuntime, verifyContract, receiptEvidence, verifyGovernanceReceipt, preflight, verifyAuthority };
if (require.main === module) main().catch(error => { console.error(error.publicMessage ? error.message : "Candidate preparation failed; no signing or transmission was attempted."); process.exitCode = 1; });
