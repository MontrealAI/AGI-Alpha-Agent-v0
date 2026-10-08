// SPDX-License-Identifier: Apache-2.0
const fs = require("fs");
const { deployLocal, writeManifest } = require("./deployment");

async function main() {
    const output = process.env.ASCENSION_DEPLOY_OUTPUT;
    if (output && fs.existsSync(output))
        throw Error("ASCENSION_DEPLOY_OUTPUT already exists; choose a new evidence file (existing files are never overwritten)");
    const { manifest } = await deployLocal();
    const result = writeManifest(manifest, output);
    if (output) process.stdout.write(JSON.stringify({ output: result, verified: true, scope: manifest.scope }) + "\n");
    else process.stdout.write(result);
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
