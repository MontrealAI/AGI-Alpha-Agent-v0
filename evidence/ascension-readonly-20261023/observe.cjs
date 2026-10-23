// SPDX-License-Identifier: Apache-2.0
// One finite read-only provider observation. No signer, retries or fallback provider.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const os = require("node:os");
const cp = require("node:child_process");
const ethers = require("/workspace/scratch/5d02e86cc826/ascension-evm-local/source/tests/contracts/node_modules/ethers");
const REPO = "/workspace/scratch/5d02e86cc826/alpha-thermal-native";
const OUT = __dirname;
const TRANSPORT = "tests/contracts/scripts/authority-rpc.js";
const { createReadOnlyRpc, LIMITS } = require(path.join(REPO, TRANSPORT));
const ENDPOINT = "https://cloudflare-eth.com/";
const REPORT = path.join(OUT, "observation.json");
const TRACE = path.join(OUT, "rpc-trace.jsonl");
const MANIFEST = "docs/deployments/2026-10-18/manifest.json";
const manifestBytes = fs.readFileSync(path.join(REPO, MANIFEST));
const manifest = JSON.parse(manifestBytes);
const sha = value => crypto.createHash("sha256").update(value).digest("hex");
const json = value => JSON.stringify(value, (_, x) => typeof x === "bigint" ? x.toString() : x, 2) + "\n";
const now = () => new Date().toISOString();
const git = args => cp.execFileSync("git", args, { cwd: REPO, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
const equal = (a, b) => typeof a === "string" && typeof b === "string" ? a.toLowerCase() === b.toLowerCase() : a === b;
const need = (ok, message) => { if (!ok) throw Error(message); };
const asAddress = value => ethers.getAddress(value.toLowerCase());
const contracts = Object.fromEntries(manifest.contracts.map(c => [c.name, c]));
const A = Object.fromEntries(manifest.contracts.map(c => [c.name, asAddress(c.address)]));
const token = asAddress(contracts.AscensionRiskOracle.values.token);
const ens = asAddress(contracts.AscensionAccess.values.ens);
const wrapper = asAddress(contracts.AscensionAccess.values.wrapper);
const actor = asAddress(manifest.governor);
const addresses = [...Object.values(A), token, ens, wrapper, actor];
const slots = Object.fromEntries(["implementation", "admin", "beacon"].map(name => [name, ethers.toBeHex(BigInt(ethers.id("eip1967.proxy." + name)) - 1n, 32)]));
const storage = addresses.slice(0, 8).flatMap(address => Object.values(slots).map(slot => ({ address, slot })));
const scope = { graph: Object.values(A), all: addresses, earliestBlock: 26215174, storage, noCall: [actor] };
const reducedLimits = { requests: 128, timeoutMs: 5000, deadlineMs: 60000, responseBytes: 512 * 1024, requestBytes: 16 * 1024, totalBytes: 8 * 1024 * 1024 };
const files = [MANIFEST, "docs/agent/CURRENT_MAINNET_DEPLOYMENT.md", TRANSPORT,
    "contracts/ascension/AscensionAccess.sol", "contracts/ascension/NovaSeed.sol", "contracts/ascension/AscensionRiskOracle.sol",
    "contracts/ascension/AscensionJobMarket.sol", "contracts/ascension/AscensionMark.sol", "contracts/ascension/AscensionToken.sol",
    "contracts/v2/Constants.sol", "tests/contracts/package.json", "tests/contracts/package-lock.json"];
const sourceBindings = files.map(file => {
    const data = fs.readFileSync(path.join(REPO, file));
    const target = path.join(OUT, "source", file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, data, { flag: "wx", mode: 0o600 });
    let historicalSha256 = null, historicalComparison = "not-a-deployed-source-file";
    if (file.startsWith("contracts/")) {
        try {
            historicalSha256 = sha(cp.execFileSync("git", ["show", manifest.source.commit + ":" + file], { cwd: REPO, stdio: ["ignore", "pipe", "pipe"] }));
            historicalComparison = historicalSha256 === sha(data) ? "same-bytes" : "different-bytes";
        } catch { historicalComparison = "historical-object-unavailable-locally"; }
    }
    return { file, bytes: data.length, sha256: sha(data), historicalSha256, historicalComparison };
});
const ethersRoot = "/workspace/scratch/5d02e86cc826/ascension-evm-local/source/tests/contracts/node_modules/ethers";
const packageFiles = ["package.json", "lib.commonjs/index.js", "lib.commonjs/providers/provider-cloudflare.js"].map(file => ({ file, sha256: sha(fs.readFileSync(path.join(ethersRoot, file))) }));
const source = {
    observerSha256: sha(fs.readFileSync(__filename)), observerPath: __filename,
    checkout: { path: REPO, head: git(["rev-parse", "HEAD"]), status: git(["status", "--short"]) },
    deploymentSource: manifest.source, manifestSha256: sha(manifestBytes), files: sourceBindings,
    dependency: { name: "ethers", version: ethers.version, root: ethersRoot, files: packageFiles,
        note: "Existing read-only installed closure; no package installation in this observation." }
};
fs.writeFileSync(path.join(OUT, "source-bindings.json"), json(source), { flag: "wx", mode: 0o600 });
const report = {
    schema: "agialpha.bounded-readonly-mainnet-observation.v1",
    startedAt: now(), completedAt: null, endpoint: ENDPOINT, status: "NOT_STARTED",
    source,
    environment: { node: process.version, versions: process.versions, platform: process.platform, arch: process.arch,
        osRelease: os.release(), nodeExecutable: process.execPath, nodeExecutableSha256: sha(fs.readFileSync(process.execPath)),
        nodePathForTransportResolution: "/workspace/scratch/5d02e86cc826/ascension-evm-local/source/tests/contracts/node_modules",
        tlsVerification: "default-enabled; no override", credentialsUsed: false },
    policy: { methods: ["eth_chainId", "eth_getBlockByNumber", "eth_getCode", "eth_getStorageAt", "eth_call"],
        retries: 0, fallbackEndpoints: [], plannedMaximumRequests: 98, scope, limits: { ...LIMITS, ...reducedLimits },
        allStateReadsAtOneNumericFinalizedBlock: true, stopAtFirstErrorOrIdentityMismatch: true,
        signs: false, sendsTransactions: false, installsPackages: false, writesRepositoryFiles: false },
    historicalAuthorityBlock: manifest.authorityBlock, pinnedBlock: null, canonicalFinalBracket: false,
    code: [], proxySlots: [], getters: [], roots: [], token: {}, actorSample: { address: actor, basis: "Historical governor only; not a worker/reviewer census", reads: [] },
    comparisons: [], rpc: [], stopReason: null, transportStats: null,
    activationAllowed: false, readyForPublicFunding: false, productionReady: false,
    limitations: [
        "A single trusted HTTPS provider supplies observations; this is not an independent chain proof or an audit.",
        "Numeric pinned-block reads are bracketed by block hashes; the existing transport does not support EIP-1898 blockHash call parameters.",
        "Only the five historical suite addresses, token, ENS registry, wrapper and historical governor are in scope.",
        "EIP-1967 implementation/admin/beacon words are sampled only. Zero words do not exclude arbitrary proxy patterns. Nonzero targets are not traversed.",
        "No global event or participant enumeration. The governor sample cannot establish worker/reviewer eligibility, independence, current job availability or funded readiness.",
        "Current explorer ABI/source and external token/ENS upgrade-authority inventories are not independently refreshed.",
        "Manifest hashes and local Solidity-bound ABI fragments are reference inputs; the historical deployment record is not modified.",
        "The existing transport exposes validated raw JSON-RPC result values. It deliberately discards rejected HTTP/RPC wire bodies and redacts network failure details; those unavailable bodies cannot be preserved here.",
        "No activation, funding, admission, governance, token approval, signing, transaction or deployment is authorized by this report."
    ]
};
fs.writeFileSync(REPORT, json(report), { flag: "wx", mode: 0o600 });
fs.writeFileSync(TRACE, "", { flag: "wx", mode: 0o600 });
const persist = () => fs.writeFileSync(REPORT, json(report), { mode: 0o600 });
const trace = event => fs.appendFileSync(TRACE, JSON.stringify(event, (_, x) => typeof x === "bigint" ? x.toString() : x) + "\n");
let transport = null;
let tag = null;
async function rpc(method, params) {
    const item = { index: report.rpc.length + 1, startedAt: now(), method, params, status: "ATTEMPTED" };
    report.rpc.push(item); trace({ kind: "intent", ...item }); persist();
    try {
        const result = await transport(method, params);
        item.status = "RESULT"; item.completedAt = now(); item.result = result;
        trace({ kind: "result", ...item }); persist(); return result;
    } catch (error) {
        item.status = "FAILED"; item.completedAt = now(); item.error = { message: String(error.message), publicTransportMessage: error.publicMessage === true, rawWireResponse: null };
        trace({ kind: "failure", ...item }); persist(); throw error;
    }
}
function comparison(label, observed, expected, immutable) {
    const matches = equal(observed, expected);
    report.comparisons.push({ label, observed, expected, matches, expectationKind: immutable ? "required-identity-or-fixed-binding" : "historical-mutable-observation" });
    persist(); if (immutable) need(matches, "Identity or fixed-binding mismatch: " + label);
}
async function getter(address, signature, args = []) {
    const abi = new ethers.Interface([signature]);
    const fragment = abi.fragments[0];
    const data = abi.encodeFunctionData(fragment, args);
    const raw = await rpc("eth_call", [{ to: address, data }, tag]);
    const decoded = abi.decodeFunctionResult(fragment, raw);
    return { address, signature, args, raw, value: decoded.length === 1 ? decoded[0] : [...decoded] };
}
async function main() {
    need(ethers.version === "6.17.0", "Unexpected ethers version");
    need(manifest.chainId === 1 && manifest.contracts.length === 5, "Unexpected deployment manifest");
    need(sourceBindings.filter(x => x.file.startsWith("contracts/")).every(x => x.historicalComparison !== "different-bytes"), "Current ABI source differs from historical source");
    transport = createReadOnlyRpc(ENDPOINT, scope, { limits: reducedLimits });
    report.status = "IN_PROGRESS"; persist();
    comparison("chainId", await rpc("eth_chainId", []), "0x1", true);
    const pinned = await rpc("eth_getBlockByNumber", ["finalized", false]);
    need(pinned && /^0x[0-9a-f]+$/.test(pinned.number) && /^0x[0-9a-fA-F]{64}$/.test(pinned.hash) && /^0x[0-9a-f]+$/.test(pinned.timestamp), "Invalid finalized block identity");
    need(BigInt(pinned.number) >= BigInt(manifest.authorityBlock.number), "Finalized block predates historical authority anchor");
    tag = pinned.number;
    report.pinnedBlock = { tag, number: BigInt(tag).toString(), hash: pinned.hash, timestamp: BigInt(pinned.timestamp).toString(), timestampUtc: new Date(Number(BigInt(pinned.timestamp)) * 1000).toISOString() }; persist();
    const anchor = await rpc("eth_getBlockByNumber", [ethers.toQuantity(manifest.authorityBlock.number), false]);
    comparison("historicalAuthorityBlock.number", anchor?.number, ethers.toQuantity(manifest.authorityBlock.number), true);
    comparison("historicalAuthorityBlock.hash", anchor?.hash, manifest.authorityBlock.hash, true);
    for (const address of addresses) {
        const raw = await rpc("eth_getCode", [address, tag]);
        const item = { address, bytes: (raw.length - 2) / 2, keccak256: ethers.keccak256(raw), raw };
        report.code.push(item);
        const historical = manifest.contracts.find(c => equal(c.address, address));
        if (historical) comparison(historical.name + ".runtimeCodeHash", item.keccak256, historical.codeHash, true);
        else item.expectedCodeHash = null;
    }
    for (const address of addresses.slice(0, 8)) for (const [label, slot] of Object.entries(slots)) {
        const word = await rpc("eth_getStorageAt", [address, slot, tag]);
        report.proxySlots.push({ address, label, slot, word, low160BitsAddress: ethers.getAddress("0x" + word.slice(-40)),
            nonzero: BigInt(word) !== 0n, interpretation: "Conventional slot sample only; any nonzero target authority remains unresolved" });
    }
    const definitions = {
        AscensionAccess: { owner: "address", pendingOwner: "address", ens: "address", wrapper: "address" },
        NovaSeed: { access: "address", nextId: "uint256" },
        AscensionRiskOracle: { owner: "address", pendingOwner: "address", access: "address", seed: "address", token: "address", marketplace: "address", minimumStake: "uint256", quorum: "uint16", maximumRiskBps: "uint16" },
        AscensionJobMarket: { owner: "address", pendingOwner: "address", access: "address", oracle: "address", token: "address", mark: "address", minimumStake: "uint256", nextId: "uint256" },
        AscensionMark: { seed: "address", access: "address", oracle: "address", jobs: "address", token: "address" }
    };
    for (const [name, fields] of Object.entries(definitions)) {
        for (const [field, type] of Object.entries(fields)) {
            const result = await getter(A[name], `function ${field}() view returns (${type})`);
            report.getters.push({ contract: name, field, ...result });
            comparison(name + "." + field, typeof result.value === "bigint" ? result.value.toString() : result.value,
                contracts[name].values[field], !["owner", "pendingOwner", "nextId"].includes(field));
        }
        if (name === "AscensionAccess") for (const [role, root] of ["alpha.agi.eth", "alpha.agent.agi.eth", "alpha.club.agi.eth"].entries()) {
            const result = await getter(A[name], "function roots(uint8) view returns (bytes32)", [role]);
            report.getters.push({ contract: name, field: "roots", role, root, ...result });
            comparison(name + ".roots(" + role + ")", result.value, ethers.namehash(root), true);
        }
    }
    for (const name of ["alpha.agi.eth", "alpha.agent.agi.eth", "alpha.club.agi.eth"]) {
        const node = ethers.namehash(name);
        const owner = await getter(ens, "function owner(bytes32) view returns (address)", [node]);
        const item = { name, node, ensOwner: owner, wrapper: null };
        if (equal(owner.value, wrapper)) {
            const wrapped = await getter(wrapper, "function getData(uint256) view returns (address owner,uint32 fuses,uint64 expiry)", [BigInt(node)]);
            item.wrapper = wrapped; item.wrapperUnexpiredAtPinnedBlock = wrapped.value[2] > BigInt(pinned.timestamp);
        }
        report.roots.push(item);
    }
    report.token.decimals = await getter(token, "function decimals() view returns (uint8)");
    comparison("token.decimals", report.token.decimals.value.toString(), "18", true);
    report.token.totalSupply = await getter(token, "function totalSupply() view returns (uint256)");
    report.token.suiteBalances = [];
    for (const address of Object.values(A)) report.token.suiteBalances.push(await getter(token, "function balanceOf(address) view returns (uint256)", [address]));
    for (const signature of ["function admission(address) view returns (bytes32 evidence,uint64 until)", "function admitted(address) view returns (bool)"]) {
        report.actorSample.reads.push(await getter(A.AscensionAccess, signature, [actor]));
    }
    for (let role = 0; role < 3; role++) for (const signature of ["function names(address,uint8) view returns (bytes32)", "function eligible(address,uint8) view returns (bool)"]) {
        report.actorSample.reads.push(await getter(A.AscensionAccess, signature, [actor, role]));
    }
    for (const [field, type] of Object.entries({ isValidator: "bool", stake: "uint256", lockedUntil: "uint64", activeJobs: "uint32", jobCapacity: "uint32" })) {
        report.actorSample.reads.push(await getter(A.AscensionRiskOracle, `function ${field}(address) view returns (${type})`, [actor]));
    }
    for (const [field, type] of Object.entries({ stake: "uint256", locked: "uint256", reputation: "uint32" })) {
        report.actorSample.reads.push(await getter(A.AscensionJobMarket, `function ${field}(address) view returns (${type})`, [actor]));
    }
    const end = await rpc("eth_getBlockByNumber", [tag, false]);
    comparison("finalPinnedBlock.number", end?.number, tag, true);
    comparison("finalPinnedBlock.hash", end?.hash, pinned.hash, true);
    comparison("finalChainId", await rpc("eth_chainId", []), "0x1", true);
    report.canonicalFinalBracket = true;
    report.status = "COMPLETE_WITH_EXPLICIT_SCOPE_LIMITS";
}
main().catch(error => {
    report.status = "INCOMPLETE_STOPPED";
    report.stopReason = { message: String(error.message), publicTransportMessage: error.publicMessage === true,
        lastAttempt: report.rpc.at(-1)?.index ?? null, retried: false, fallbackUsed: false,
        failedTransportDetailNotAvailable: error.publicMessage === true };
    process.exitCode = 2;
}).finally(() => {
    report.completedAt = now(); report.transportStats = transport?.stats() ?? null; persist();
    const summary = { status: report.status, startedAt: report.startedAt, completedAt: report.completedAt,
        successfulRpcCalls: report.rpc.filter(x => x.status === "RESULT").length, attemptedRpcCalls: report.rpc.length,
        pinnedBlock: report.pinnedBlock, canonicalFinalBracket: report.canonicalFinalBracket,
        codeObserved: report.code.length, getterObservations: report.getters.length, proxySlotObservations: report.proxySlots.length,
        actorSampleObservations: report.actorSample.reads.length, stopReason: report.stopReason, transportStats: report.transportStats,
        activationAllowed: false, readyForPublicFunding: false, productionReady: false,
        reportPath: REPORT, reportSha256: sha(fs.readFileSync(REPORT)), tracePath: TRACE, traceSha256: sha(fs.readFileSync(TRACE)),
        sourceBindingsSha256: sha(fs.readFileSync(path.join(OUT, "source-bindings.json"))), observerSha256: source.observerSha256 };
    fs.writeFileSync(path.join(OUT, "summary.json"), json(summary), { flag: "wx", mode: 0o600 });
    process.stdout.write(json(summary));
});
