// SPDX-License-Identifier: Apache-2.0
// Portable Nova-Seed capsules using browser/Node Web Crypto, not a custom cipher.
const encoder = new TextEncoder();
const MAX_BYTES = 250000;
const ITERATIONS = 600000;
const fail = (message) => {
    throw new Error(message);
};

export function canonicalJSON(value) {
    const seen = new Set();
    function encode(item, depth = 0) {
        if (depth > 24) fail("Document nesting exceeds 24 levels.");
        if (
            item === null ||
            typeof item === "string" ||
            typeof item === "boolean"
        )
            return JSON.stringify(item);
        if (typeof item === "number") {
            if (!Number.isFinite(item))
                fail("Document numbers must be finite.");
            return JSON.stringify(item);
        }
        if (!item || typeof item !== "object" || seen.has(item))
            fail("Document must contain acyclic JSON data.");
        seen.add(item);
        let result;
        if (Array.isArray(item)) {
            if (
                Object.keys(item).length !== item.length ||
                !Array.from({ length: item.length }, (_, i) =>
                    Object.hasOwn(item, i),
                ).every(Boolean)
            )
                fail("Sparse or extended arrays are not JSON data.");
            result =
                "[" +
                item.map((part) => encode(part, depth + 1)).join(",") +
                "]";
        } else {
            if (
                Object.getPrototypeOf(item) !== Object.prototype &&
                Object.getPrototypeOf(item) !== null
            )
                fail("Document must contain plain JSON objects.");
            result =
                "{" +
                Object.keys(item)
                    .sort()
                    .map(
                        (key) =>
                            JSON.stringify(key) +
                            ":" +
                            encode(item[key], depth + 1),
                    )
                    .join(",") +
                "}";
        }
        seen.delete(item);
        return result;
    }
    const encoded = encode(value);
    if (encoder.encode(encoded).length > MAX_BYTES)
        fail("Document exceeds 250 KB.");
    return encoded;
}

const base64 = (bytes) => {
    let binary = "";
    for (let i = 0; i < bytes.length; i += 16384)
        binary += String.fromCharCode(...bytes.subarray(i, i + 16384));
    return btoa(binary);
};
const fromBase64 = (value, length) => {
    if (
        typeof value !== "string" ||
        value.length > 350000 ||
        !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(
            value,
        )
    )
        fail("Invalid capsule encoding.");
    const bytes = Uint8Array.from(atob(value), (c) => c.charCodeAt(0));
    if (length !== undefined && bytes.length !== length)
        fail("Invalid capsule field length.");
    return bytes;
};

export async function hashObject(value) {
    const result = await crypto.subtle.digest(
        "SHA-256",
        encoder.encode(canonicalJSON(value)),
    );
    return [...new Uint8Array(result)]
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
}

async function deriveKey(passphrase, salt, usage) {
    if (
        typeof passphrase !== "string" ||
        passphrase.length < 12 ||
        passphrase.length > 256
    )
        fail(
            "Use a private passphrase of 12–256 characters. Keep it outside the capsule.",
        );
    const source = await crypto.subtle.importKey(
        "raw",
        encoder.encode(passphrase),
        "PBKDF2",
        false,
        ["deriveKey"],
    );
    return crypto.subtle.deriveKey(
        { name: "PBKDF2", salt, iterations: ITERATIONS, hash: "SHA-256" },
        source,
        { name: "AES-GCM", length: 256 },
        false,
        [usage],
    );
}

export async function sealSeed(payload, passphrase) {
    if (payload?.schema !== "agialpha.novaseed.genome.v1")
        fail("Seal a Nova-Seed genome.");
    const blind = base64(crypto.getRandomValues(new Uint8Array(32)));
    const plaintext = canonicalJSON({ blind, payload });
    const header = {
        schema: "agialpha.novaseed.sealed.v1",
        cipher: "AES-256-GCM",
        kdf: "PBKDF2-HMAC-SHA256",
        iterations: ITERATIONS,
        salt: base64(crypto.getRandomValues(new Uint8Array(16))),
        iv: base64(crypto.getRandomValues(new Uint8Array(12))),
        commitment: await hashObject({ blind, payload }),
    };
    const key = await deriveKey(
        passphrase,
        fromBase64(header.salt, 16),
        "encrypt",
    );
    const ciphertext = await crypto.subtle.encrypt(
        {
            name: "AES-GCM",
            iv: fromBase64(header.iv, 12),
            additionalData: encoder.encode(canonicalJSON(header)),
            tagLength: 128,
        },
        key,
        encoder.encode(plaintext),
    );
    return { ...header, ciphertext: base64(new Uint8Array(ciphertext)) };
}

export async function openSeed(capsule, passphrase) {
    if (!capsule || typeof capsule !== "object" || Array.isArray(capsule))
        fail("Import a sealed Nova-Seed file.");
    const fields = [
        "schema",
        "cipher",
        "kdf",
        "iterations",
        "salt",
        "iv",
        "commitment",
        "ciphertext",
    ];
    if (
        Object.keys(capsule).length !== fields.length ||
        !fields.every((field) => Object.hasOwn(capsule, field)) ||
        capsule.schema !== "agialpha.novaseed.sealed.v1" ||
        capsule.cipher !== "AES-256-GCM" ||
        capsule.kdf !== "PBKDF2-HMAC-SHA256" ||
        capsule.iterations !== ITERATIONS ||
        typeof capsule.commitment !== "string" ||
        !/^[0-9a-f]{64}$/.test(capsule.commitment)
    )
        fail("Unsupported or altered Nova-Seed header.");
    const { ciphertext, ...header } = capsule;
    const salt = fromBase64(header.salt, 16),
        iv = fromBase64(header.iv, 12),
        data = fromBase64(ciphertext);
    if (data.length < 16 || data.length > MAX_BYTES + 16)
        fail("Invalid capsule size.");
    const key = await deriveKey(passphrase, salt, "decrypt");
    let decoded;
    try {
        const result = await crypto.subtle.decrypt(
            {
                name: "AES-GCM",
                iv,
                additionalData: encoder.encode(canonicalJSON(header)),
                tagLength: 128,
            },
            key,
            data,
        );
        decoded = JSON.parse(
            new TextDecoder("utf-8", { fatal: true }).decode(result),
        );
    } catch {
        fail(
            "Could not open this seed. Check the passphrase and file integrity.",
        );
    }
    if (
        decoded?.payload?.schema !== "agialpha.novaseed.genome.v1" ||
        typeof decoded.blind !== "string" ||
        fromBase64(decoded.blind, 32).length !== 32 ||
        (await hashObject(decoded)) !== capsule.commitment
    )
        fail("Nova-Seed commitment verification failed.");
    return decoded.payload;
}
