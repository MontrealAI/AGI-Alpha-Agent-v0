// SPDX-License-Identifier: Apache-2.0
const fs = require("fs");
const os = require("os");
const path = require("path");
const { expect } = require("chai");
const hre = require("hardhat");
const solc = require("solc");
const { ROOT, SETTINGS, productionSources, dependencyImporter, assertCleanOutput } = require("../scripts/compile-production");
const { SOLC_VERSION } = require("../scripts/compiler-policy");

describe("Complete production-source compilation gate", () => {
    it("includes the production modules absent from Hardhat fixtures and matches its compiler profile", () => {
        const { sources, mirrored } = productionSources();
        for (const name of ["DisputeModule", "ReputationEngine", "TokenUtils"]) {
            const source = `contracts/v2/${name}.sol`;
            expect(sources[source].content).to.equal(fs.readFileSync(path.join(ROOT, source), "utf8"));
            expect(mirrored).not.to.include(source);
        }
        expect(Object.keys(sources)).to.have.length(15);
        expect(mirrored).to.have.length(12);
        const compiler = hre.config.solidity.compilers[0];
        expect(compiler.version).to.equal(SOLC_VERSION);
        for (const key of ["optimizer", "viaIR", "evmVersion"]) expect(compiler.settings[key]).to.deep.equal(SETTINGS[key]);
    });

    it("rejects actual Solidity warnings and errors instead of excluding their source", () => {
        const output = source => JSON.parse(solc.compile(JSON.stringify({ language: "Solidity",
            sources: { "contracts/Test.sol": { content: source } }, settings: { ...SETTINGS, outputSelection: {} } })));
        const warning = output("pragma solidity ^0.8.24; contract Test {}");
        expect(warning.errors.some(item => item.severity === "warning")).to.equal(true);
        expect(() => assertCleanOutput(warning)).to.throw("warning(s)");
        const error = output("// SPDX-License-Identifier: Apache-2.0\npragma solidity ^0.8.24; contract Test { uint public missing = unknown; }");
        expect(error.errors.some(item => item.severity === "error")).to.equal(true);
        expect(() => assertCleanOutput(error)).to.throw("Undeclared identifier");
    });

    it("rejects source/fixture drift and symbolic-link exclusions", () => {
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "ascension-production-sources-"));
        try {
            fs.mkdirSync(path.join(temporary, "contracts/v2"), { recursive: true });
            fs.mkdirSync(path.join(temporary, "tests/contracts/contracts/v2"), { recursive: true });
            fs.writeFileSync(path.join(temporary, "contracts/v2/Test.sol"), "source");
            fs.writeFileSync(path.join(temporary, "tests/contracts/contracts/v2/Test.sol"), "stale fixture");
            expect(() => productionSources(temporary)).to.throw("fixture differs from source");
            fs.writeFileSync(path.join(temporary, "tests/contracts/contracts/v2/Test.sol"), "source");
            expect(Object.keys(productionSources(temporary).sources)).to.deep.equal(["contracts/v2/Test.sol"]);
            fs.symlinkSync(path.join(temporary, "contracts/v2/Test.sol"), path.join(temporary, "contracts/v2/Linked.sol"));
            expect(() => productionSources(temporary)).to.throw("cannot be symbolic links");
        } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
    });

    it("embeds only normalized imports from the locked OpenZeppelin package", () => {
        const sources = {}, read = dependencyImporter(sources);
        const name = "@openzeppelin/contracts/access/Ownable.sol";
        const resolved = read(name);
        expect(resolved.contents).to.be.a("string");
        expect(sources[name].content).to.equal(resolved.contents);
        for (const name of ["/etc/passwd", "contracts/Unknown.sol", "@openzeppelin/contracts/../../package.json",
            "@openzeppelin/contracts/access/../access/Ownable.sol", "@openzeppelin/contracts/\\access/Ownable.sol"])
            expect(read(name).error).to.include("Rejected dependency");
    });
});
