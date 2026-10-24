// SPDX-License-Identifier: Apache-2.0
const fs = require("fs");
const crypto = require("crypto");
const assert = require("assert/strict");
const sha256 = value => crypto.createHash("sha256").update(value).digest("hex");
if (process.argv.length !== 5) throw Error("Usage: node writer10-verify.js results.json exact-input.json independently-pinned-public-key.pem");
const result = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const input = fs.readFileSync(process.argv[3]);
const publicKey = fs.readFileSync(process.argv[4], "utf8");
assert.equal(sha256(input), result.input.sha256);
assert.equal(input.length, result.input.bytes);
assert.equal(result.offchainRegistry.publicKey, publicKey);
let previous = null;
for (const [i, record] of result.offchainRegistry.records.entries()) {
    assert.equal(record.digest, sha256(record.payload));
    assert(crypto.verify(null, Buffer.from(record.payload), publicKey, Buffer.from(record.signature, "base64")));
    const payload = JSON.parse(record.payload);
    assert.equal(payload.sequence, i);
    assert.equal(payload.previous, previous);
    if (payload.event.type === "delivered") assert.equal(payload.event.resultSha256, result.input.sha256);
    previous = record.digest;
}
console.log(JSON.stringify({verified: true, exactEvidenceBytes: input.length, signatureRecords: result.offchainRegistry.records.length, terminalDigest: previous, boundary: "Authenticates this supplied record sequence and byte commitment under the independently pinned key. It does not establish physical truth, registry completeness, public consensus, or feasibility of the underlying workload."}));
