// SPDX-License-Identifier: Apache-2.0
// Exports exact explorer inputs without importing a wallet or submitting requests.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const ethers = require("ethers");
const { ROOT, RECORD_SHA256, NAMES, loadRecord, constructorArguments } = require("./mainnet-record");
const { canonical, checkPlan, makePlan, compiledContracts, reviewedRevision } = require("./mainnet");
const sha256 = value => crypto.createHash("sha256").update(value).digest("hex");
const json = value => JSON.stringify(value, null, 2) + "\n";

function requireValue(value, message) {
    if (!value) { const error = Error(message); error.publicMessage = true; throw error; }
}

function explorerCompiler(version) {
    const match = /^(0\.8\.\d+\+commit\.[0-9a-f]{8})(?:\.Emscripten\.clang)?$/.exec(version);
    requireValue(match, "Exact release compiler version with commit hash required");
    return `v${match[1]}`;
}

function packageFiles(profile, entries) {
    const files = {}, contracts = {};
    for (const entry of entries) {
        const { name, address, compiler, inputText, sourceName, abi, args, bytecode, data } = entry;
        requireValue(NAMES.includes(name) && !contracts[name], "Unexpected or duplicate verification contract");
        const input = JSON.parse(inputText);
        requireValue(input.language === "Solidity" && typeof input.sources?.[sourceName]?.content === "string",
            "Verification requires the exact Standard JSON source and original source path");
        requireValue(Object.values(input.sources).every(source => typeof source.content === "string"),
            "Verification sources must be embedded; external URLs are not reproducible");
        const encoded = new ethers.Interface(abi).encodeDeploy(args);
        requireValue(ethers.concat([bytecode, encoded]).toLowerCase() === data.toLowerCase(),
            "Constructor arguments do not match the deployment transaction");
        const params = { chainid: "1", module: "contract", action: "verifysourcecode",
            contractaddress: ethers.getAddress(address), codeformat: "solidity-standard-json-input",
            contractname: `${sourceName}:${name}`, compilerversion: explorerCompiler(compiler),
            constructorArguments: encoded.slice(2), sourceCode: inputText };
        files[`${name}/standard-input.json`] = inputText;
        files[`${name}/constructor-arguments.txt`] = encoded.slice(2) + "\n";
        files[`${name}/etherscan-request.json`] = json(params);
        contracts[name] = { address: params.contractaddress, qualifiedName: params.contractname,
            compiler: params.compilerversion, settings: input.settings,
            constructorArguments: args, deploymentDataKeccak256: ethers.keccak256(data),
            standardInputSha256: sha256(inputText) };
    }
    requireValue(Object.keys(contracts).length === NAMES.length, "All five Ascension contracts are required");
    files["README.txt"] = [
        "ASCENSION SOURCE VERIFICATION PACKAGE — ETHEREUM MAINNET (chain ID 1)",
        `Profile: ${profile.kind}`,
        "1. Match the contract address against manifest.json before uploading anything.",
        "2. In Etherscan choose Solidity (Standard-Json-Input), then the exact compiler in manifest.json.",
        "3. Upload that contract's standard-input.json; preserve source paths, imports, metadata and all settings.",
        "4. Use the fully qualified contract name and constructor-arguments.txt (ABI hex without 0x).",
        "5. For API V2, form-encode etherscan-request.json at https://api.etherscan.io/v2/api with your API key.",
        "   The package never contains an API key and never submits a request. Keep credentials outside it.",
        "6. A returned submission GUID is pending, not success. Poll checkverifystatus and retain the final response.",
        "   Recheck the explorer address, source, compiler, constructor and bytecode match after success.",
        "Do not flatten or recompile an existing address with newer sources/compiler to remove warnings.",
        "The recorded deployment is immutable and predates later settlement fixes. New code needs new deployment review.",
        "Planned addresses are predictions, not proof of deployment. Run mainnet:verify after commissioning.",
        "Source verification establishes a code match; funding/participant commissioning remain separate.",
        "Reference: https://docs.etherscan.io/api-reference/endpoint/verifysourcecode",
        "",
    ].join("\n");
    const manifest = { schema: "agialpha.explorer-verification-package.v1", chainId: 1, profile, contracts,
        externalRequests: false, explorerSubmission: "not-performed", readyForPublicFunding: false,
        files: Object.fromEntries(Object.entries(files).map(([name, content]) => [name, sha256(content)])) };
    files["manifest.json"] = json(manifest);
    return { files, manifest };
}

function recordedPackage(directory = ROOT) {
    const { record, compiled, expected } = loadRecord(directory);
    const args = constructorArguments(record);
    const inputText = fs.readFileSync(path.join(directory, "compiler-input.json"), "utf8");
    return packageFiles({ kind: "recorded-2026-10-11", manifestSha256: RECORD_SHA256,
        sourceProfile: record.profile, sourceVerification: record.sourceVerification }, NAMES.map((name, i) => ({
        name, address: record.contracts[name].address, compiler: record.compiler.version, inputText,
        sourceName: compiled[name].sourceName, abi: compiled[name].abi, bytecode: compiled[name].bytecode,
        args: args[i], data: expected[i].data,
    })));
}

async function plannedPackage(plan, compiled = compiledContracts(), revision = reviewedRevision()) {
    checkPlan(plan);
    requireValue(canonical(plan.revision) === canonical(revision),
        "Use the exact clean source revision and dependency lock recorded in the plan");
    const rebuilt = await makePlan(plan.config, compiled, plan.revision);
    requireValue(canonical(rebuilt) === canonical(plan), "Plan differs from current compiled sources; rebuild from the reviewed checkout");
    return packageFiles({ kind: "unsigned-plan", planSha256: plan.payloadSha256, revision: plan.revision },
        NAMES.map((name, i) => {
            const contract = plan.contracts[name], build = plan.builds[contract.buildId];
            const tx = plan.transactions[i];
            return { name, address: plan.addresses[name], compiler: build.compiler, inputText: json(build.input),
                sourceName: contract.sourceName, abi: contract.abi, bytecode: contract.bytecode,
                args: tx.constructorArguments, data: tx.data };
        }));
}

function writePackage(bundle, destination) {
    const target = path.resolve(destination);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    try { fs.mkdirSync(target); }
    catch (error) {
        if (error.code === "EEXIST") requireValue(false, "Output already exists; choose a new package directory");
        throw error;
    }
    for (const [name, content] of Object.entries(bundle.files)) {
        const filename = path.join(target, name);
        fs.mkdirSync(path.dirname(filename), { recursive: true });
        fs.writeFileSync(filename, content, { flag: "wx" });
    }
    return target;
}

async function main() {
    const [mode, input, output, extra] = process.argv.slice(2);
    requireValue(!extra && ((mode === "record" && input && !output) || (mode === "plan" && input && output)),
        "Usage: mainnet:verification-package -- record NEW_DIRECTORY OR -- plan PLAN.json NEW_DIRECTORY");
    const bundle = mode === "record" ? recordedPackage() : await plannedPackage(JSON.parse(fs.readFileSync(input, "utf8")));
    const destination = writePackage(bundle, mode === "record" ? input : output);
    console.log(JSON.stringify({ output: destination, chainId: 1, contracts: NAMES.length,
        profile: bundle.manifest.profile.kind, explorerSubmission: "not-performed", externalRequests: false }));
}

module.exports = { explorerCompiler, packageFiles, recordedPackage, plannedPackage, writePackage };
if (require.main === module) main().catch(error => {
    console.error(error.publicMessage ? error.message : "Verification export failed. Check the archived record or reviewed plan, compiled artifacts and new output directory.");
    process.exitCode = 1;
});
