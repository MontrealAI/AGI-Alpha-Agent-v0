// SPDX-License-Identifier: Apache-2.0
// Exact-source, disposable integration fixture. Never accepts an external RPC URL.
const { ethers, network, artifacts } = require("hardhat");
const { createHash, randomBytes } = require("crypto");
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { pathToFileURL } = require("url");
const { fixture, now, jump } = require("./fixture");
const { requireDisposableLocalNetwork } = require("./disposable");

const root = path.resolve(__dirname, "../../..");
const names = { Access: "access", Seed: "seed", Oracle: "oracle", Jobs: "jobs", Mark: "mark", Token: "token" };
const permitted = new Set([
    "eth_chainId", "eth_accounts", "eth_requestAccounts", "eth_getBlockByNumber", "eth_getCode", "eth_call",
    "eth_estimateGas", "eth_getBalance", "eth_getTransactionCount", "eth_getTransactionReceipt",
    "eth_getTransactionByHash", "eth_sendTransaction", "eth_getLogs", "eth_blockNumber", "eth_gasPrice",
]);
const digest = bytes => createHash("sha256").update(bytes).digest("hex");

function sourceManifest() {
    const sourceDirectory = path.join(root, "contracts/ascension");
    const sources = {};
    for (const name of fs.readdirSync(sourceDirectory).filter(name => name.endsWith(".sol")).sort()) {
        const original = fs.readFileSync(path.join(sourceDirectory, name));
        const testCopy = fs.readFileSync(path.join(root, "tests/contracts/contracts/ascension", name));
        if (!original.equals(testCopy)) throw Error(`Current-source fixture differs from production contract: ${name}`);
        sources[`contracts/ascension/${name}`] = digest(original);
    }
    return {
        compiler: require("solc").version(), optimizer: { enabled: true, runs: 200 }, viaIR: true,
        evmVersion: "cancun", sources,
    };
}

async function novaFixture() {
    await requireDisposableLocalNetwork();
    const manifest = sourceManifest();
    const artifact = await artifacts.readArtifact("AscensionMark");
    const build = await artifacts.getBuildInfo(`${artifact.sourceName}:${artifact.contractName}`);
    if (!build || build.solcLongVersion !== manifest.compiler || build.input.settings.viaIR !== true ||
        build.input.settings.evmVersion !== "cancun" || build.input.settings.optimizer.enabled !== true ||
        build.input.settings.optimizer.runs !== 200)
        throw Error("Fixture compiler artifacts are missing or use a different compiler profile; compile current sources");
    for (const [name, expected] of Object.entries(manifest.sources))
        if (!build.input.sources[name] || digest(build.input.sources[name].content) !== expected)
            throw Error(`Stale fixture build input: ${name}; compile the exact current sources before acceptance`);
    manifest.dependencies = Object.fromEntries(Object.entries(build.input.sources)
        .filter(([name]) => name.startsWith("@openzeppelin/")).sort(([a], [b]) => a.localeCompare(b))
        .map(([name, source]) => [name, digest(source.content)]));
    const f = await fixture();
    const protocolFile = path.join(root, "docs/assets/ascension-wallet/protocol.mjs");
    const protocolURL = pathToFileURL(protocolFile);
    protocolURL.searchParams.set("identity", digest(fs.readFileSync(protocolFile)));
    const { protocolIdentity } = await import(protocolURL);
    const sourceSHA256 = digest(JSON.stringify(manifest));
    const block = await network.provider.request({ method: "eth_getBlockByNumber", params: ["latest", false] });
    const genesis = await network.provider.request({ method: "eth_getBlockByNumber", params: ["0x0", false] });
    const contracts = {};
    for (const [alias, key] of Object.entries(names)) {
        const address = f[key].target;
        const code = await ethers.provider.getCode(address);
        contracts[alias] = { address, sha256: digest(Buffer.from(code.slice(2), "hex")) };
    }
    const profile = {
        schema: "agialpha.nova-local-profile.v1", profile: `ascension-current-source-local-${sourceSHA256.slice(0, 16)}`,
        chainId: 31337, environment: "local-exact-source", mainnetQualification: false, newExposureEnabled: true,
        sourceSHA256, abiSHA256: digest(protocolIdentity()), genesisHash: genesis.hash,
        deploymentBlock: block.number, deploymentBlockHash: block.hash, contracts,
    };
    const actors = Object.fromEntries(
        ["governor", "business", "agent", "fastAgent", "validator1", "validator2", "validator3", "funder", "funder2", "outsider"]
            .map(name => [name, f[name].address.toLowerCase()]),
    );
    const rpc = async (actor, { method, params = [] }) => {
        if (!Object.hasOwn(actors, actor)) throw Error("Unknown local fixture actor");
        if (!permitted.has(method)) throw Error(`RPC method is not exposed by the disposable fixture: ${method}`);
        if (["eth_accounts", "eth_requestAccounts"].includes(method)) return [actors[actor]];
        if (method === "eth_sendTransaction" && params[0]?.from?.toLowerCase() !== actors[actor])
            throw Error("Selected local actor differs from transaction sender");
        return network.provider.request({ method, params });
    };
    function provider(actor) {
        const listeners = new Map();
        return {
            sends: [], lastHash: null, mode: "normal",
            on(event, fn) { listeners.set(event, fn); },
            removeListener(event) { listeners.delete(event); },
            emit(event, value) { listeners.get(event)?.(value); },
            async request(request) {
                if (request.method === "eth_sendTransaction") {
                    if (this.mode === "reject") throw Object.assign(Error("Local wallet declined"), { code: 4001 });
                    this.sends.push(request.params[0]);
                    this.lastHash = await rpc(actor, request);
                    if (this.mode === "lose-response") throw Error("Response lost after a real local EVM broadcast");
                    return this.lastHash;
                }
                return rpc(actor, request);
            },
        };
    }
    return { ...f, actors, profile, sourceManifest: manifest, provider, rpc };
}

async function serve() {
    const f = await novaFixture();
    const directory = path.resolve(process.env.NOVA_FIXTURE_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), "nova-fixture-")));
    if (directory === root || directory.startsWith(path.join(root, "docs") + path.sep))
        throw Error("Fixture output must not be written into the production docs tree");
    fs.mkdirSync(directory, { recursive: true });
    const token = randomBytes(32).toString("hex");
    const server = http.createServer(async (request, response) => {
        response.setHeader("Content-Type", "application/json");
        response.setHeader("Cache-Control", "no-store");
        try {
            if (request.headers.authorization !== `Bearer ${token}`) {
                response.writeHead(403); response.end(JSON.stringify({ error: "Local fixture authorization required" })); return;
            }
            if (request.method !== "POST") throw Error("POST required");
            let bytes = 0, body = "";
            for await (const chunk of request) {
                bytes += chunk.length;
                if (bytes > 1000000) throw Error("Request exceeds fixture limit");
                body += chunk;
            }
            const data = JSON.parse(body);
            let result;
            if (request.url === "/rpc") result = await f.rpc(data.actor, data.request);
            else if (request.url === "/advance") {
                await requireDisposableLocalNetwork();
                const timestamp = Number(data.timestamp);
                if (!Number.isSafeInteger(timestamp) || timestamp <= await now()) throw Error("Invalid future timestamp");
                await jump(timestamp); result = await now();
            } else throw Error("Unknown local fixture endpoint");
            response.end(JSON.stringify({ result }));
        } catch (error) {
            response.writeHead(400);
            response.end(JSON.stringify({ error: { message: error.message, code: error.code || -32000 } }));
        }
    });
    await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
    const info = {
        schema: "agialpha.nova-disposable-fixture.v1", endpoint: `http://127.0.0.1:${server.address().port}`,
        token, actors: f.actors, profile: f.profile, sourceManifest: f.sourceManifest,
        note: "Disposable unforked local EVM. Actors, ENS, token and approvals are fixtures, not independent real-world participants.",
    };
    fs.writeFileSync(path.join(directory, "profile.json"), JSON.stringify(f.profile, null, 2) + "\n");
    fs.writeFileSync(path.join(directory, "fixture.json"), JSON.stringify(info, null, 2) + "\n", { mode: 0o600 });
    process.stdout.write(`Nova disposable fixture ready: ${path.join(directory, "fixture.json")}\n`);
    const stop = () => server.close(() => process.exit(0));
    process.on("SIGTERM", stop); process.on("SIGINT", stop);
}

module.exports = { novaFixture, sourceManifest };
if (require.main === module) serve().catch(error => { process.stderr.write(`${error.stack}\n`); process.exitCode = 1; });
