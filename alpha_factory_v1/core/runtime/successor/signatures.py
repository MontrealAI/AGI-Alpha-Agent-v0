# SPDX-License-Identifier: Apache-2.0
"""Admit canonical, non-small-order Ed25519 encodings before library verification.

Signature arithmetic stays in cryptography/OpenSSL. Some supported backends accept
small-order public keys, including message-dependent zero-key/zero-signature forgeries.
These public-input checks make the SUCCESSOR boundary deterministic across backends;
they are not a replacement curve implementation or a full subgroup-membership test.

Encoding bounds: RFC 8032 sections 5.1.3 and 5.1.7.
https://www.rfc-editor.org/rfc/rfc8032#section-5.1.7
The five sign-independent torsion y coordinates were cross-checked against the
repository-locked @noble/curves 1.2.0 ED25519_TORSION_SUBGROUP (MIT, Paul Miller):
https://github.com/paulmillr/noble-curves/blob/1.2.0/src/ed25519.ts
Libsodium also excludes small-order public keys and R in signature verification:
https://github.com/jedisct1/libsodium/blob/master/src/libsodium/crypto_sign/ed25519/ref10/open.c
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_FIELD = 2**255 - 19
_ORDER = 2**252 + 27742317777372353535851937790883648493
_LOW_ORDER_Y = frozenset(
    {
        0,
        1,
        _FIELD - 1,
        int.from_bytes(bytes.fromhex("26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05"), "little"),
        int.from_bytes(bytes.fromhex("c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a"), "little"),
    }
)


def validate_ed25519_point(encoded: bytes) -> None:
    """Reject noncanonical field encodings and all eight torsion points, with either sign."""
    if len(encoded) != 32:
        raise ValueError("Ed25519 point must contain exactly 32 bytes")
    y = int.from_bytes(encoded, "little") & (2**255 - 1)
    if y >= _FIELD or y in _LOW_ORDER_Y:
        raise ValueError("Ed25519 point encoding is noncanonical or has small order")


def verify_ed25519(public_key: bytes, signature: bytes, message: bytes) -> None:
    """Apply strict encoding admission, then delegate the signature equation to OpenSSL."""
    validate_ed25519_point(public_key)
    if len(signature) != 64:
        raise ValueError("Ed25519 signature must contain exactly 64 bytes")
    validate_ed25519_point(signature[:32])
    if int.from_bytes(signature[32:], "little") >= _ORDER:
        raise ValueError("Ed25519 signature scalar is noncanonical")
    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
