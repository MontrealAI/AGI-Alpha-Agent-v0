// SPDX-License-Identifier: Apache-2.0
const crypto = require("crypto");
const { ethers } = require("ethers");
const { leaf } = require("./plan");

const canonical = (value) => JSON.stringify(value, (_, v) => typeof v === "bigint" ? v.toString() : v);
const sha256 = (data) => crypto.createHash("sha256").update(data).digest("hex");
const nonzero = (value) => /^0x[0-9a-f]{64}$/i.test(value) && value !== ethers.ZeroHash;

class SignedRegistry {
    constructor() {
        const keys = crypto.generateKeyPairSync("ed25519");
        this.privateKey = keys.privateKey;
        this.publicKey = keys.publicKey.export({type: "spki", format: "pem"});
        this.seeds = new Map();
        this.events = [];
        this.nextId = 0;
    }
    append(event) {
        const payload = canonical({sequence: this.events.length, previous: this.events.at(-1)?.digest || null, event});
        const record = {payload, signature: crypto.sign(null, Buffer.from(payload), this.privateKey).toString("base64"), digest: sha256(payload)};
        this.events.push(record);
        return record;
    }
    seal({owner, capsuleHash, planRoot, evidenceHash, parent = 0, jobs, metadataURI, authority}) {
        if (!authority || authority.owner !== owner || authority.role !== "business" || authority.until <= authority.now) throw Error("business authority");
        if (![capsuleHash, planRoot, evidenceHash].every(nonzero)) throw Error("empty commitment");
        if (!Number.isInteger(jobs) || jobs < 1 || jobs > 128) throw Error("job bound");
        if (typeof metadataURI !== "string" || Buffer.byteLength(metadataURI) < 1 || Buffer.byteLength(metadataURI) > 512) throw Error("metadata URI");
        if (parent && this.seeds.get(parent)?.owner !== owner) throw Error("parent ownership");
        const id = ++this.nextId;
        this.seeds.set(id, {id, owner, capsuleHash, planRoot, evidenceHash, parent, jobs, metadataURI, posted: new Set(), green: false});
        this.append({type: "sealed", id, owner, capsuleHash, planRoot, evidenceHash, parent, jobs, metadataURI});
        return id;
    }
    approve(id, owner, authority) {
        const seed = this.seeds.get(id);
        if (!seed || seed.owner !== owner || authority.until <= authority.now || authority.owner !== owner) throw Error("scoped authority");
        seed.green = true;
        seed.authority = authority;
        this.append({type: "approved", id, owner, authority});
    }
    route(id, index, spec, proof, owner, now) {
        const seed = this.seeds.get(id);
        if (!seed || seed.owner !== owner || !seed.green || seed.authority.until <= now) throw Error("scoped authority");
        if (!Number.isInteger(index) || index < 0 || index >= seed.jobs || seed.posted.has(index)) throw Error("FusionPlan proof");
        let hash = leaf(index, spec);
        for (const other of proof) hash = ethers.keccak256(ethers.concat([hash, other].sort()));
        if (hash !== seed.planRoot) throw Error("FusionPlan proof");
        seed.posted.add(index);
        return this.append({type: "routed", id, index, spec, leaf: leaf(index, spec)});
    }
    deliver(id, index, resultHash, resultSha256) {
        const seed = this.seeds.get(id);
        if (!seed?.posted.has(index) || !nonzero(resultHash)) throw Error("delivery binding");
        return this.append({type: "delivered", id, index, resultHash, resultSha256});
    }
}

function verifyRegistry(records, pinnedPublicKey) {
    let previous = null;
    for (let i = 0; i < records.length; i++) {
        const r = records[i];
        if (r.digest !== sha256(r.payload) || !crypto.verify(null, Buffer.from(r.payload), pinnedPublicKey, Buffer.from(r.signature, "base64"))) return false;
        const payload = JSON.parse(r.payload);
        if (payload.sequence !== i || payload.previous !== previous) return false;
        previous = r.digest;
    }
    return true;
}

module.exports = {SignedRegistry, verifyRegistry, canonical, sha256};
