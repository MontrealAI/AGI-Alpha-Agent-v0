// SPDX-License-Identifier: Apache-2.0
// Compile every shipped contract, including legacy modules absent from Hardhat fixtures.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { SOLC_VERSION, pinnedCompiler, assertNoCompilerWarnings } = require("./compiler-policy");
const ROOT = path.resolve(__dirname, "../../..");
const SETTINGS = { optimizer: { enabled: true, runs: 200 }, viaIR: true, evmVersion: "cancun" };
const sha256 = data => crypto.createHash("sha256").update(data).digest("hex");

function productionSources(directory = ROOT) {
    const sources = {}, mirrored = [];
    function walk(relative) {
        for (const entry of fs.readdirSync(path.join(directory, relative), { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
            const name = `${relative}/${entry.name}`;
            if (entry.isSymbolicLink()) throw Error(`Production sources cannot be symbolic links: ${name}`);
            if (entry.isDirectory()) walk(name);
            else if (entry.isFile() && entry.name.endsWith(".sol")) {
                const content = fs.readFileSync(path.join(directory, name), "utf8");
                const mirror = path.join(directory, "tests/contracts", name);
                if (fs.existsSync(mirror)) {
                    if (fs.readFileSync(mirror, "utf8") !== content) throw Error(`Contract fixture differs from source: ${name}`);
                    mirrored.push(name);
                }
                sources[name] = { content };
            }
        }
    }
    walk("contracts");
    if (!Object.keys(sources).length) throw Error("No production Solidity sources found");
    return { sources, mirrored };
}

function dependencyImporter(sources) {
    const prefix = "@openzeppelin/contracts/";
    const base = fs.realpathSync(path.resolve(__dirname, "../node_modules/@openzeppelin/contracts"));
    return source => {
        try {
            if (!source.startsWith(prefix) || source.includes("\\") || path.posix.normalize(source) !== source)
                throw Error("Only normalized OpenZeppelin package imports are allowed");
            const file = fs.realpathSync(path.join(base, source.slice(prefix.length)));
            if (!file.startsWith(`${base}${path.sep}`) || !fs.statSync(file).isFile())
                throw Error("Dependency import leaves the locked OpenZeppelin package");
            const content = fs.readFileSync(file, "utf8");
            sources[source] = { content };
            return { contents: content };
        } catch (error) { return { error: `Rejected dependency ${source}: ${error.message}` }; }
    };
}

function assertCleanOutput(output) {
    const errors = (output.errors || []).filter(item => item.severity === "error");
    if (errors.length) throw Error(errors.map(item => item.formattedMessage || item.message).join("\n"));
    try { assertNoCompilerWarnings(output); }
    catch (error) {
        throw Error(`${error.message}\n${output.errors.filter(item => item.severity === "warning")
            .map(item => item.formattedMessage || item.message).join("\n")}`);
    }
}

function compileProduction(directory = ROOT) {
    const compiler = pinnedCompiler(SOLC_VERSION), solc = require("solc");
    const { sources, mirrored } = productionSources(directory);
    const productionNames = Object.keys(sources);
    // Resolve the transitive import closure before the final, fully embedded compilation.
    const discovery = JSON.parse(solc.compile(JSON.stringify({ language: "Solidity", sources,
        settings: { ...SETTINGS, outputSelection: {} } }), { import: dependencyImporter(sources) }));
    assertCleanOutput(discovery);
    const input = { language: "Solidity", sources: Object.fromEntries(Object.entries(sources).sort(([a], [b]) => a.localeCompare(b))),
        settings: { ...SETTINGS, outputSelection: { "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] } } } };
    const output = JSON.parse(solc.compile(JSON.stringify(input)));
    assertCleanOutput(output);
    const contracts = {};
    for (const source of productionNames) for (const [name, contract] of Object.entries(output.contracts[source] || {})) {
        const creationBytes = contract.evm.bytecode.object.length / 2;
        const runtimeBytes = contract.evm.deployedBytecode.object.length / 2;
        if (creationBytes) contracts[`${source}:${name}`] = { creationBytes, runtimeBytes };
    }
    const report = { schema: "agialpha.production-compilation.v1", compiler: compiler.longVersion,
        settings: SETTINGS, productionSourceCount: productionNames.length,
        dependencySourceCount: Object.keys(sources).length - productionNames.length,
        fixtureMirrorCount: mirrored.length, solidityErrors: 0, solidityWarnings: 0,
        inputSha256: sha256(JSON.stringify(input)), productionSources: productionNames,
        sources: Object.fromEntries(Object.entries(input.sources).map(([name, source]) => [name, sha256(source.content)])),
        contracts, qualification: "Compilation only; legacy v2 integration and deployment commissioning are not established." };
    return { input, output, report };
}

module.exports = { ROOT, SETTINGS, productionSources, dependencyImporter, assertCleanOutput, compileProduction };
if (require.main === module) {
    try {
        if (process.argv.length !== 2) throw Error("Usage: npm run compile:production");
        console.log(JSON.stringify(compileProduction().report, null, 2));
    } catch (error) { console.error(error.message); process.exitCode = 1; }
}
