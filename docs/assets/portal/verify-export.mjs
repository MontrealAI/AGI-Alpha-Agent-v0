// SPDX-License-Identifier: Apache-2.0
// Verify original Python canonical bytes without converting large integers or float representations.
const hex = (value) =>
    Uint8Array.from(value.match(/../g), (pair) => parseInt(pair, 16));
const hash = async (text) =>
    [
        ...new Uint8Array(
            await crypto.subtle.digest(
                "SHA-256",
                new TextEncoder().encode(text),
            ),
        ),
    ]
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
function equivalent(a, b) {
    if (
        a === null ||
        b === null ||
        typeof a !== "object" ||
        typeof b !== "object"
    )
        return a === b;
    if (Array.isArray(a) !== Array.isArray(b)) return false;
    const left = Object.keys(a).sort(),
        right = Object.keys(b).sort();
    return (
        left.length === right.length &&
        left.every((key, i) => key === right[i] && equivalent(a[key], b[key]))
    );
}
export async function verifyAgentExport(artifact, trustedKey) {
    if (!/^[0-9a-f]{64}$/.test(trustedKey))
        throw new Error(
            "Paste the agent’s independently trusted public key: 64 lowercase hexadecimal characters.",
        );
    if (artifact?.schema !== 1 || artifact.public_key !== trustedKey)
        throw new Error(
            "The export does not match that trusted agent identity.",
        );
    const receipt = artifact.receipt;
    if (
        typeof receipt?.canonical_body !== "string" ||
        typeof receipt.canonical_result !== "string"
    )
        throw new Error(
            "This older export lacks portable canonical bytes. Re-export it with agent v1.4.0 or use alpha-agent verify-export locally.",
        );
    if (
        receipt.canonical_body.length > 2000000 ||
        receipt.canonical_result.length > 1000000
    )
        throw new Error(
            "Receipt exceeds browser verification limits. Verify it with the local agent.",
        );
    if (
        !/^[0-9a-f]{64}$/.test(receipt.hash) ||
        (await hash(receipt.canonical_body)) !== receipt.hash
    )
        throw new Error("Signed receipt content was changed or corrupted.");
    if (
        typeof receipt.signature !== "string" ||
        !/^[A-Za-z0-9+/]{86}==$/.test(receipt.signature)
    )
        throw new Error("Malformed Ed25519 signature.");
    const signature = Uint8Array.from(atob(receipt.signature), (char) =>
        char.charCodeAt(0),
    );
    const key = await crypto.subtle.importKey(
        "raw",
        hex(trustedKey),
        { name: "Ed25519" },
        false,
        ["verify"],
    );
    if (
        !(await crypto.subtle.verify(
            "Ed25519",
            key,
            signature,
            hex(receipt.hash),
        ))
    )
        throw new Error("Ed25519 signature verification failed.");
    const body = JSON.parse(receipt.canonical_body);
    if (
        body.identity !== `urn:agialpha:ed25519:${trustedKey}` ||
        body.schema !== 1
    )
        throw new Error("Signed identity or receipt schema mismatch.");
    const document = body.document;
    if (
        document?.state !== "completed" ||
        document.review?.result_hash !== (await hash(receipt.canonical_result))
    )
        throw new Error("The signed record is not an approved, intact result.");
    if (
        !equivalent(body, receipt.body) ||
        !equivalent(document.result, JSON.parse(receipt.canonical_result))
    )
        throw new Error(
            "Displayed data differs from the authenticated canonical data.",
        );
    return {
        identity: body.identity,
        mission: body.mission,
        hash: receipt.hash,
        canonical: receipt.canonical_body,
    };
}
