// SPDX-License-Identifier: Apache-2.0
// Reproducible local deployment. No RPC URL, wallet key, or external-network option.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");
const { AGIALPHA_ADDRESS, AGIALPHA_DECIMALS } = require("../../../token.config");

const root = path.resolve(__dirname, "../../..");
const names = ["AscensionAccess", "NovaSeed", "AscensionRiskOracle", "AscensionJobMarket", "AscensionMark"];
const minimumStake = "10000000000000000000";
const sha256 = bytes => crypto.createHash("sha256").update(bytes).digest("hex");

function deploymentPlan(env = process.env) {
    if ((env.AGIALPHA_ADDRESS && env.AGIALPHA_ADDRESS.toLowerCase() !== AGIALPHA_ADDRESS.toLowerCase()) ||
        (env.AGIALPHA_DECIMALS && env.AGIALPHA_DECIMALS !== String(AGIALPHA_DECIMALS)))
        throw Error("Token overrides conflict with canonical $AGIALPHA. Restore token.config.js values; no migration occurs.");
    const sources = {};
    for (const relative of [...names, "AscensionToken"].map(name => `contracts/ascension/${name}.sol`)
        .concat("contracts/v2/Constants.sol")) {
        const source = fs.readFileSync(path.join(root, relative));
        const fixture = fs.readFileSync(path.join(root, "tests/contracts", relative));
        if (!source.equals(fixture)) throw Error(`Contract fixture differs from source: ${relative}`);
        sources[relative] = sha256(source);
    }
    for (const relative of ["token.config.js", "tests/contracts/hardhat.config.js", "tests/contracts/package-lock.json",
        "tests/contracts/scripts/deployment.js", "tests/contracts/scripts/deploy.js", "tests/contracts/scripts/disposable.js",
        "tests/contracts/scripts/check-deployment-config.js",
        "tests/contracts/test/utils/token.js", "tests/contracts/contracts/v2/mocks/MockAGI.sol",
        "tests/contracts/contracts/ascension/MockENS.sol"])
        sources[relative] = sha256(fs.readFileSync(path.join(root, relative)));
    let revision = null;
    try {
        const git = args => execFileSync("git", args, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
        revision = { commit: git(["rev-parse", "HEAD"]), tree: git(["rev-parse", "HEAD^{tree}"]),
            worktreeDirty: git(["status", "--porcelain", "--untracked-files=normal"]).length > 0 };
    } catch { /* Source archives may omit git; exact file digests remain authoritative. */ }
    return {
        schema: "agialpha.ascension.deployment-plan.v1",
        scope: "disposable-local-fixture",
        chainId: "31337",
        network: "hardhat",
        externalTransactions: false,
        token: { symbol: "AGIALPHA", address: AGIALPHA_ADDRESS, decimals: AGIALPHA_DECIMALS, mock: true },
        governance: "first ephemeral Hardhat signer; no imported key",
        parameters: { minimumValidatorStake: minimumStake, minimumAgentStake: minimumStake, quorum: 2, maximumRiskBps: 2000 },
        deploymentOrder: ["MockAGI at canonical address", "MockAscensionENS", "MockAscensionWrapper", ...names],
        oneTimeBindings: ["oracle.bindMarketplace(jobs)", "jobs.bindMark(mark)"],
        migration: "Fresh local state only; no balances, identities, permissions, proofs, or jobs are imported.",
        revision, sources,
    };
}

function verifyBuildSources(build, readSource) {
    const hashes = {};
    for (const [name, source] of Object.entries(build.input.sources)) {
        const current = readSource(name);
        if (current !== source.content)
            throw Error(`Compiled source is stale: ${name}. Run npm run compile before deployment.`);
        hashes[name] = sha256(Buffer.from(current));
    }
    return hashes;
}

async function compiledEvidence() {
    const { artifacts } = require("hardhat");
    const builds = {};
    for (const name of [...names, "MockAscensionENS", "MockAscensionWrapper", "contracts/v2/mocks/MockAGI.sol:MockAGI"]) {
        const artifact = await artifacts.readArtifact(name);
        const build = await artifacts.getBuildInfo(`${artifact.sourceName}:${artifact.contractName}`);
        if (!build) throw Error("Compiler build information is missing. Run npm run compile before deployment.");
        const output = build.output.contracts[artifact.sourceName][artifact.contractName];
        if (artifact.bytecode !== `0x${output.evm.bytecode.object}`)
            throw Error(`Deployment bytecode differs from compiler output: ${name}. Run npm run compile.`);
        if (!builds[build.id]) {
            const sourceHashes = verifyBuildSources(build, source => fs.readFileSync(path.join(root, "tests/contracts",
                source.startsWith("@") ? "node_modules" : "", source), "utf8"));
            builds[build.id] = { solcVersion: build.solcVersion, solcLongVersion: build.solcLongVersion,
                inputSha256: sha256(Buffer.from(JSON.stringify(build.input))), settings: build.input.settings, sourceHashes };
        }
    }
    return builds;
}

async function verifyDeployment(contracts, governor) {
    const { ethers } = require("hardhat");
    const { token, ens, wrapper, access, seed, oracle, jobs, mark } = contracts;
    const same = (actual, expected, label) => {
        if (String(actual).toLowerCase() !== String(expected).toLowerCase())
            throw Error(`Deployment verification failed: ${label}`);
    };
    same((await ethers.provider.getNetwork()).chainId, 31337n, "chain ID");
    for (const [name, contract] of Object.entries(contracts)) {
        if (await ethers.provider.getCode(contract.target) === "0x")
            throw Error(`Deployment verification failed: ${name} has no bytecode`);
    }
    same(token.target, AGIALPHA_ADDRESS, "token address");
    same(await token.decimals(), AGIALPHA_DECIMALS, "token decimals");
    for (const contract of [oracle, jobs, mark]) same(await contract.token(), token.target, "token binding");
    for (const contract of [access, oracle, jobs]) same(await contract.owner(), governor, "governance owner");
    same(await access.ens(), ens.target, "ENS binding");
    same(await access.wrapper(), wrapper.target, "wrapper binding");
    for (const [index, name] of ["alpha.agi.eth", "alpha.agent.agi.eth", "alpha.club.agi.eth"].entries())
        same(await access.roots(index), ethers.namehash(name), "ENS role root");
    for (const contract of [seed, oracle, jobs, mark]) same(await contract.access(), access.target, "access binding");
    for (const contract of [oracle, mark]) same(await contract.seed(), seed.target, "seed binding");
    for (const contract of [jobs, mark]) same(await contract.oracle(), oracle.target, "oracle binding");
    same(await oracle.marketplace(), jobs.target, "one-time marketplace binding");
    same(await jobs.mark(), mark.target, "one-time MARK binding");
    same(await mark.jobs(), jobs.target, "MARK marketplace binding");
    same(await oracle.minimumStake(), minimumStake, "validator stake");
    same(await jobs.minimumStake(), minimumStake, "agent stake");
    same(await oracle.quorum(), 2, "review quorum");
    same(await oracle.maximumRiskBps(), 2000, "risk limit");
    same(await token.totalSupply(), 0, "fresh token supply");
    same(await seed.nextId(), 0, "fresh seeds");
    same(await jobs.nextId(), 0, "fresh jobs");
    return true;
}

async function deployLocal() {
    const plan = deploymentPlan();
    const { ethers, config } = require("hardhat");
    const { requireDisposableLocalNetwork } = require("./disposable");
    await requireDisposableLocalNetwork();
    if ((await ethers.provider.getNetwork()).chainId !== 31337n)
        throw Error("Local deployment requires chain ID 31337");
    // Refuse to erase a used provider. Each CLI invocation gets its own new EVM.
    if (await ethers.provider.getBlockNumber() !== 0)
        throw Error("Deployment requires a fresh Hardhat process; existing chain state will not be reset");
    const builds = await compiledEvidence();
    const [governor] = await ethers.getSigners();
    const transactions = [];
    async function record(action, transaction) {
        const receipt = await transaction.wait();
        if (!receipt || receipt.status !== 1) throw Error(`Local transaction failed: ${action}`);
        transactions.push({ action, hash: receipt.hash, blockNumber: receipt.blockNumber, gasUsed: receipt.gasUsed.toString() });
    }
    async function deploy(name, ...args) {
        const contract = await (await ethers.getContractFactory(name)).deploy(...args);
        await record(`deploy ${name}`, contract.deploymentTransaction());
        await contract.waitForDeployment();
        return contract;
    }
    const tokenImplementation = await deploy("contracts/v2/mocks/MockAGI.sol:MockAGI", AGIALPHA_DECIMALS);
    await ethers.provider.send("hardhat_setCode", [AGIALPHA_ADDRESS,
        await ethers.provider.getCode(tokenImplementation.target)]);
    const token = tokenImplementation.attach(AGIALPHA_ADDRESS);
    const ens = await deploy("MockAscensionENS");
    const wrapper = await deploy("MockAscensionWrapper");
    const access = await deploy("AscensionAccess", ens.target, wrapper.target, governor.address);
    const seed = await deploy("NovaSeed", access.target);
    const oracle = await deploy("AscensionRiskOracle", access.target, seed.target, minimumStake, 2, 2000, governor.address);
    const jobs = await deploy("AscensionJobMarket", access.target, oracle.target, minimumStake, governor.address);
    const mark = await deploy("AscensionMark", seed.target, access.target, oracle.target, jobs.target);
    await record("bind oracle marketplace", await oracle.bindMarketplace(jobs.target));
    await record("bind marketplace MARK", await jobs.bindMark(mark.target));
    const contracts = { token, ens, wrapper, access, seed, oracle, jobs, mark };
    await verifyDeployment(contracts, governor.address);
    const deployed = {};
    for (const [name, contract] of Object.entries(contracts)) {
        deployed[name] = { address: contract.target, runtimeCodeHash: ethers.keccak256(await ethers.provider.getCode(contract.target)) };
    }
    const block = await ethers.provider.getBlock("latest");
    return {
        contracts,
        manifest: {
            ...plan, schema: "agialpha.ascension.local-deployment.v1", governor: governor.address,
            instanceId: (await ethers.provider.send("hardhat_metadata", [])).instanceId,
            hardhatVersion: require("hardhat/package.json").version,
            compiler: config.solidity.compilers[0], builds, deployed, transactions,
            tokenInstallation: "Mock runtime copied with hardhat_setCode; no canonical-token deployment transaction",
            tokenImplementation: tokenImplementation.target,
            verifiedAt: { number: block.number, hash: block.hash }, verified: true,
            persistence: "EVM state ends when this process exits. This manifest is evidence, not a live deployment.",
            productionAuthority: false,
        },
    };
}

function writeManifest(manifest, destination) {
    const json = JSON.stringify(manifest, null, 2) + "\n";
    if (destination) {
        const target = path.resolve(destination);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, json, { flag: "wx", mode: 0o600 });
        return target;
    }
    return json;
}

module.exports = { deploymentPlan, deployLocal, verifyDeployment, verifyBuildSources, writeManifest };
if (require.main === module) {
    if (process.argv.length !== 2) {
        console.error("Usage: npm run deploy:plan (prints a read-only local deployment plan)");
        process.exitCode = 1;
    } else {
        try { process.stdout.write(JSON.stringify(deploymentPlan(), null, 2) + "\n"); }
        catch (error) { console.error(error.message); process.exitCode = 1; }
    }
}
