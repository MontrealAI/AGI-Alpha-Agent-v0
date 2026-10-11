// SPDX-License-Identifier: Apache-2.0
// Unsigned Ethereum preparation and read-only verification. Never imports a signer.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");
const ethers = require("ethers");
const { verifyBuildSources, writeManifest } = require("./deployment");
const { AGIALPHA_ADDRESS } = require("../../../token.config");
const root = path.resolve(__dirname, "../../..");
const names = ["AscensionAccess", "NovaSeed", "AscensionRiskOracle", "AscensionJobMarket", "AscensionMark"];
const ENS = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e";
const WRAPPER = "0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401";
const roots = ["alpha.agi.eth", "alpha.agent.agi.eth", "alpha.club.agi.eth"];
const digest = value => crypto.createHash("sha256").update(value).digest("hex");
function canonical(value) {
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    if (value && typeof value === "object") return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(",")}}`;
    return JSON.stringify(value);
}
function requireValue(value, message) {
    if (!value) { const error = Error(message); error.publicMessage = true; throw error; }
}
function address(value) {
    let result;
    try { result = ethers.getAddress(value); } catch { requireValue(false, "A valid checksummed Ethereum address is required"); }
    requireValue(result !== ethers.ZeroAddress, "Zero address is not an operator configuration");
    return result;
}
function integer(value, minimum, maximum, label) {
    requireValue(Number.isSafeInteger(value) && value >= minimum && value <= maximum, `Invalid ${label}`);
}
function hash(value) { requireValue(/^0x[0-9a-fA-F]{64}$/.test(value) && value !== ethers.ZeroHash, "Expected reviewed nonzero code/block hash"); }
function keys(value, allowed) {
    requireValue(value && typeof value === "object" && !Array.isArray(value) &&
        Object.keys(value).length === allowed.length && Object.keys(value).every(key => allowed.includes(key)),
        "Configuration has missing or unexpected fields; use the exact example schema and keep secrets outside it");
}
function validateConfig(c) {
    keys(c, ["schema", "chainId", "deployer", "nonce", "block", "governor", "dependencies", "rootOwners", "parameters"]);
    keys(c.block, ["number", "hash"]);
    keys(c.governor, ["address", "codeHash", "owners", "threshold"]);
    keys(c.dependencies, ["token", "ens", "wrapper"]);
    for (const value of Object.values(c.dependencies)) keys(value, ["address", "codeHash"]);
    keys(c.rootOwners, roots);
    keys(c.parameters, ["minimumValidatorStake", "minimumAgentStake", "quorum", "maximumRiskBps"]);
    requireValue(c.schema === "agialpha.mainnet.config.v1" && c.chainId === 1, "Ethereum mainnet chainId 1 required");
    address(c.deployer); address(c.governor.address);
    requireValue(c.deployer.toLowerCase() !== c.governor.address.toLowerCase(), "Governance must be separate from deployer");
    integer(c.nonce, 0, Number.MAX_SAFE_INTEGER - 5, "deployer nonce");
    integer(c.block.number, 1, Number.MAX_SAFE_INTEGER, "pinned block number"); hash(c.block.hash);
    for (const [key, expected] of Object.entries({ token: AGIALPHA_ADDRESS, ens: ENS, wrapper: WRAPPER })) {
        requireValue(address(c.dependencies[key].address) === address(expected), `Noncanonical ${key} address`);
        hash(c.dependencies[key].codeHash);
    }
    hash(c.governor.codeHash);
    const owners = c.governor.owners.map(address);
    requireValue(new Set(owners).size === owners.length && owners.length <= 32, "Unique governance owners required (maximum 32)");
    integer(c.governor.threshold, 2, owners.length, "multisignature threshold");
    for (const name of roots) address(c.rootOwners[name]);
    for (const name of ["minimumValidatorStake", "minimumAgentStake"]) {
        const value = c.parameters[name];
        requireValue(typeof value === "string" && /^[1-9][0-9]*$/.test(value) && BigInt(value) < 2n ** 96n, `Invalid ${name} base units`);
    }
    integer(c.parameters.quorum, 2, 15, "quorum");
    integer(c.parameters.maximumRiskBps, 0, 10000, "maximumRiskBps");
    return c;
}
function compiledContracts() {
    const records = {}, builds = {};
    // Fixture compilation is allowed only with byte-identical repository sources.
    for (const name of [...names, "AscensionToken"]) {
        const file = `contracts/ascension/${name}.sol`;
        requireValue(fs.readFileSync(path.join(root, file)).equals(fs.readFileSync(path.join(root, "tests/contracts", file))), `Fixture/source drift: ${file}`);
    }
    const constants = "contracts/v2/Constants.sol";
    requireValue(fs.readFileSync(path.join(root, constants)).equals(fs.readFileSync(path.join(root, "tests/contracts", constants))), "Canonical token source drift");
    for (const name of names) {
        const file = path.join(root, `tests/contracts/artifacts/contracts/ascension/${name}.sol/${name}`);
        const artifact = JSON.parse(fs.readFileSync(`${file}.json`));
        const debug = JSON.parse(fs.readFileSync(`${file}.dbg.json`));
        const build = JSON.parse(fs.readFileSync(path.resolve(path.dirname(file), debug.buildInfo)));
        const output = build.output.contracts[artifact.sourceName][name];
        requireValue(build.solcVersion === "0.8.37" && build.input.settings.optimizer.enabled &&
            build.input.settings.optimizer.runs === 200 && build.input.settings.viaIR === true && build.input.settings.evmVersion === "cancun", "Unexpected compiler settings");
        requireValue(artifact.bytecode === `0x${output.evm.bytecode.object}` && artifact.deployedBytecode === `0x${output.evm.deployedBytecode.object}`, "Artifact/compiler bytecode mismatch");
        requireValue(Object.keys(artifact.linkReferences).length === 0, "Unlinked deployment bytecode");
        if (!builds[build.id]) {
            const sourceHashes = verifyBuildSources(build, source => fs.readFileSync(path.join(root, "tests/contracts", source.startsWith("@") ? "node_modules" : "", source), "utf8"));
            builds[build.id] = { compiler: build.solcLongVersion, input: build.input, inputSha256: digest(canonical(build.input)), sourceHashes };
        }
        records[name] = { abi: artifact.abi, bytecode: artifact.bytecode, runtime: artifact.deployedBytecode,
            immutableReferences: output.evm.deployedBytecode.immutableReferences, sourceName: artifact.sourceName, buildId: build.id };
    }
    return { records, builds };
}
async function makePlan(config, compiled, revision) {
    validateConfig(config);
    const addresses = Object.fromEntries(names.map((name, i) => [name, ethers.getCreateAddress({ from: config.deployer, nonce: config.nonce + i })]));
    const a = addresses, p = config.parameters, g = config.governor.address;
    const argumentsByName = {
        AscensionAccess: [ENS, WRAPPER, g], NovaSeed: [a.AscensionAccess],
        AscensionRiskOracle: [a.AscensionAccess, a.NovaSeed, p.minimumValidatorStake, p.quorum, p.maximumRiskBps, g],
        AscensionJobMarket: [a.AscensionAccess, a.AscensionRiskOracle, p.minimumAgentStake, g],
        AscensionMark: [a.NovaSeed, a.AscensionAccess, a.AscensionRiskOracle, a.AscensionJobMarket],
    };
    const transactions = [];
    for (const [i, name] of names.entries()) {
        const record = compiled.records[name];
        const factory = new ethers.ContractFactory(record.abi, record.bytecode);
        const tx = await factory.getDeployTransaction(...argumentsByName[name]);
        transactions.push({ action: `deploy ${name}`, from: config.deployer, chainId: 1, nonce: config.nonce + i,
            value: "0", data: tx.data, expectedAddress: a[name], constructorArguments: argumentsByName[name] });
    }
    const governanceCalls = [
        { action: "bind oracle marketplace", to: a.AscensionRiskOracle, method: "bindMarketplace", argument: a.AscensionJobMarket, name: "AscensionRiskOracle" },
        { action: "bind marketplace MARK", to: a.AscensionJobMarket, method: "bindMark", argument: a.AscensionMark, name: "AscensionJobMarket" },
    ].map(call => ({ action: call.action, from: g, to: call.to, chainId: 1, value: "0", operation: 0,
        data: new ethers.Interface(compiled.records[call.name].abi).encodeFunctionData(call.method, [call.argument]) }));
    const payload = { schema: "agialpha.mainnet.unsigned-plan.v1", config, revision, addresses, transactions, governanceCalls,
        builds: compiled.builds, contracts: compiled.records, readyToBroadcast: false,
        remainingGates: ["Independent review of these exact sources and dependency implementations", "Pinned mainnet-fork lifecycle and accounting rehearsal with the real token", "Multisignature operator review, current nonce/fees and transaction simulation", "Source verification and post-deployment acceptance before admissions or funding"] };
    return { ...payload, payloadSha256: digest(canonical(payload)) };
}
function checkPlan(plan) {
    const { payloadSha256, ...payload } = plan;
    requireValue(plan.schema === "agialpha.mainnet.unsigned-plan.v1" && digest(canonical(payload)) === payloadSha256, "Plan checksum mismatch");
    validateConfig(plan.config);
}
// The transport has an explicit allowlist: no signing, sending, impersonation, reset or state override.
function readOnlyRpc(url) {
    const parsed = new URL(url);
    requireValue(parsed.protocol === "https:" && !parsed.username && !parsed.password && !parsed.hash, "Use an HTTPS RPC URL without embedded user credentials");
    const allowed = new Set(["eth_chainId", "eth_getBlockByNumber", "eth_getCode", "eth_call", "eth_getTransactionCount", "eth_getBalance"]);
    return async (method, params) => {
        requireValue(allowed.has(method), "Read-only RPC method required");
        let response;
        try {
            response = await fetch(url, { method: "POST", redirect: "error", signal: AbortSignal.timeout(20000),
                headers: { "Content-Type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
            requireValue(response.ok, "RPC unavailable");
            const body = await response.json();
            requireValue(!body.error && body.result !== undefined, "RPC request rejected");
            return body.result;
        } catch { throw Error(`Read-only RPC failed for ${method}; check provider availability (URL and provider errors are redacted)`); }
    };
}
async function inspectChain(config, rpc, deployed = false) {
    validateConfig(config);
    requireValue(BigInt(await rpc("eth_chainId", [])) === 1n, "Wrong chain: Ethereum mainnet required");
    const tag = ethers.toQuantity(config.block.number);
    const block = await rpc("eth_getBlockByNumber", [tag, false]);
    requireValue(block && block.hash.toLowerCase() === config.block.hash.toLowerCase(), "Pinned block hash mismatch");
    const finalized = await rpc("eth_getBlockByNumber", ["finalized", false]);
    requireValue(finalized && BigInt(finalized.number) >= BigInt(config.block.number), "Pinned block must be finalized");
    const checks = [];
    for (const [label, dependency] of Object.entries({ ...config.dependencies, governor: config.governor })) {
        const code = await rpc("eth_getCode", [dependency.address, tag]);
        requireValue(code !== "0x" && ethers.keccak256(code).toLowerCase() === dependency.codeHash.toLowerCase(), `Reviewed ${label} code hash mismatch`);
        checks.push(`${label}-code`);
    }
    async function call(to, signature, args = []) {
        const abi = new ethers.Interface([`function ${signature}`]);
        const fn = abi.fragments[0];
        const data = await rpc("eth_call", [{ to, data: abi.encodeFunctionData(fn, args) }, tag]);
        return abi.decodeFunctionResult(fn, data)[0];
    }
    requireValue(await call(AGIALPHA_ADDRESS, "decimals() view returns (uint8)") === 18n, "Token decimals must equal 18");
    const owners = [...await call(config.governor.address, "getOwners() view returns (address[])")].map(address).sort();
    requireValue(canonical(owners) === canonical(config.governor.owners.map(address).sort()) &&
        await call(config.governor.address, "getThreshold() view returns (uint256)") === BigInt(config.governor.threshold), "Governance owners/threshold mismatch");
    for (const name of roots) {
        const node = ethers.namehash(name);
        let owner = await call(ENS, "owner(bytes32) view returns (address)", [node]);
        if (address(owner) === address(WRAPPER)) {
            const abi = new ethers.Interface(["function getData(uint256) view returns (address owner,uint32 fuses,uint64 expiry)"]);
            const raw = await rpc("eth_call", [{ to: WRAPPER, data: abi.encodeFunctionData("getData", [BigInt(node)]) }, tag]);
            const result = abi.decodeFunctionResult("getData", raw);
            requireValue(result.expiry > BigInt(block.timestamp), `ENS root expired: ${name}`);
            owner = result.owner;
        }
        requireValue(address(owner) === address(config.rootOwners[name]), `ENS root owner mismatch: ${name}`);
    }
    requireValue(await rpc("eth_getCode", [config.deployer, "latest"]) === "0x", "Deployment requires a dedicated EOA; smart-account CREATE semantics differ");
    const latestNonce = BigInt(await rpc("eth_getTransactionCount", [config.deployer, "latest"]));
    const pendingNonce = BigInt(await rpc("eth_getTransactionCount", [config.deployer, "pending"]));
    requireValue((deployed ? latestNonce >= BigInt(config.nonce + 5) : latestNonce === BigInt(config.nonce)) && pendingNonce === latestNonce, "Deployer nonce changed or transactions are pending; rebuild the plan");
    // Confirm the pinned history did not change while the reads ran.
    const end = await rpc("eth_getBlockByNumber", [tag, false]);
    requireValue(end && end.hash.toLowerCase() === config.block.hash.toLowerCase(), "Pinned history changed during preflight");
    return { schema: "agialpha.mainnet.preflight.v1", chainId: 1, block: config.block,
        configSha256: digest(canonical(config)),
        checks: [...checks, "token-decimals", "multisignature-owners-and-threshold", "ENS-role-root-owners", deployed ? "deployment-nonces-consumed" : "dedicated-deployer-and-unused-nonce"],
        preflightPassed: true, readyToBroadcast: false, externalTransactions: false,
        limitation: "Read-only configuration check, not a token behavior test, independent audit, fee quote or authorization. Repeat immediately before signing." };
}
async function verifyLive(plan, rpc) {
    checkPlan(plan);
    const final = await rpc("eth_getBlockByNumber", ["finalized", false]);
    requireValue(final && BigInt(final.number) >= BigInt(plan.config.block.number), "Finalized deployment block required");
    const config = { ...plan.config, block: { number: Number(BigInt(final.number)), hash: final.hash } };
    const preflight = await inspectChain(config, rpc, true);
    const tag = ethers.toQuantity(config.block.number);
    const a = plan.addresses, g = address(config.governor.address), p = config.parameters;
    const expected = {
        AscensionAccess: { owner: g, pendingOwner: ethers.ZeroAddress, ens: ENS, wrapper: WRAPPER },
        NovaSeed: { access: a.AscensionAccess, nextId: "0" },
        AscensionRiskOracle: { owner: g, pendingOwner: ethers.ZeroAddress, access: a.AscensionAccess, seed: a.NovaSeed,
            token: AGIALPHA_ADDRESS, marketplace: a.AscensionJobMarket, minimumStake: p.minimumValidatorStake,
            quorum: String(p.quorum), maximumRiskBps: String(p.maximumRiskBps) },
        AscensionJobMarket: { owner: g, pendingOwner: ethers.ZeroAddress, access: a.AscensionAccess, oracle: a.AscensionRiskOracle,
            token: AGIALPHA_ADDRESS, mark: a.AscensionMark, minimumStake: p.minimumAgentStake, nextId: "0" },
        AscensionMark: { seed: a.NovaSeed, access: a.AscensionAccess, oracle: a.AscensionRiskOracle,
            jobs: a.AscensionJobMarket, token: AGIALPHA_ADDRESS },
    };
    const observed = {};
    for (const name of names) {
        const record = plan.contracts[name];
        const code = await rpc("eth_getCode", [a[name], tag]);
        const mask = value => {
            const bytes = ethers.getBytes(value);
            for (const references of Object.values(record.immutableReferences))
                for (const { start, length } of references) bytes.fill(0, start, start + length);
            return ethers.hexlify(bytes);
        };
        requireValue(code !== "0x" && mask(code) === mask(record.runtime), `Runtime bytecode mismatch: ${name}`);
        const abi = new ethers.Interface(record.abi);
        for (const [getter, value] of Object.entries(expected[name])) {
            const data = await rpc("eth_call", [{ to: a[name], data: abi.encodeFunctionData(getter) }, tag]);
            requireValue(String(abi.decodeFunctionResult(getter, data)[0]).toLowerCase() === String(value).toLowerCase(), `Binding mismatch: ${name}.${getter}`);
        }
        if (name === "AscensionAccess") for (const [i, value] of roots.entries()) {
            const data = await rpc("eth_call", [{ to: a[name], data: abi.encodeFunctionData("roots", [i]) }, tag]);
            requireValue(abi.decodeFunctionResult("roots", data)[0] === ethers.namehash(value), "ENS role binding mismatch");
        }
        observed[name] = { address: a[name], runtimeCodeHash: ethers.keccak256(code) };
    }
    const end = await rpc("eth_getBlockByNumber", [tag, false]);
    requireValue(end && end.hash === config.block.hash, "Finalized history changed during verification");
    return { schema: "agialpha.mainnet.deployment-verification.v1", planSha256: plan.payloadSha256,
        revision: plan.revision, block: config.block, observed, checks: preflight.checks,
        deploymentVerified: true, readyForPublicFunding: false, externalTransactions: false,
        limitation: "Exact fresh deployment and bindings verified; independent audit, proxy implementation review, source publication and operating approval remain separate." };
}
async function main() {
    const [mode, input, output] = process.argv.slice(2);
    requireValue(["plan", "preflight", "verify"].includes(mode) && input && output && process.argv.length === 5,
        "Usage: node scripts/mainnet.js <plan|preflight|verify> <config.json> <new-output.json>");
    requireValue(!fs.existsSync(output), "Output already exists; choose a new evidence filename");
    const inputData = JSON.parse(fs.readFileSync(input, "utf8"));
    const config = validateConfig(mode === "verify" ? inputData.config : inputData);
    let result;
    let revision;
    if (mode === "plan" || mode === "verify") {
        const git = args => execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
        requireValue(!git(["status", "--porcelain", "--untracked-files=normal"]), "Mainnet plan requires a clean reviewed checkout; put operator files outside the repository");
        revision = { commit: git(["rev-parse", "HEAD"]), tree: git(["rev-parse", "HEAD^{tree}"]),
            lockSha256: digest(fs.readFileSync(path.join(root, "tests/contracts/package-lock.json"))) };
    }
    if (mode === "plan") {
        result = await makePlan(config, compiledContracts(), revision);
    } else {
        const rpc = readOnlyRpc(process.env.MAINNET_RPC_URL || "");
        if (mode === "verify") {
            checkPlan(inputData);
            requireValue(canonical(inputData.revision) === canonical(revision), "Use the exact clean source revision and dependency lock recorded in the plan");
            const rebuilt = await makePlan(config, compiledContracts(), inputData.revision);
            requireValue(canonical(rebuilt) === canonical(inputData), "Plan does not match current compiled sources");
            result = await verifyLive(inputData, rpc);
        } else result = await inspectChain(config, rpc);
    }
    writeManifest(result, output);
    process.stdout.write(JSON.stringify({ output: path.resolve(output), schema: result.schema, readyToBroadcast: false }) + "\n");
}
module.exports = { validateConfig, compiledContracts, makePlan, checkPlan, inspectChain, verifyLive, readOnlyRpc, canonical, ENS, WRAPPER, roots };
if (require.main === module) main().catch(error => {
    // Never echo arbitrary operator input, JSON fragments or RPC URLs/secrets.
    if (error.publicMessage) console.error(error.message);
    else console.error("Mainnet preparation failed. Check the configuration, clean checkout, compiled artifacts, provider and new output path. See docs/agent/MAINNET_READINESS.md.");
    process.exitCode = 1;
});
