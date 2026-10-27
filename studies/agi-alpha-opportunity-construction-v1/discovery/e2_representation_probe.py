"""Public-source-informed feasibility probe; no deployed vulnerability claim.

Reimplements the field accumulation in circomlib Bits2Num, not the Circom
compiler or a SNARK. The application integer-identity requirement is synthetic.
Public references are recorded in the emitted result. Strict range checking and
two-limb encodings are established techniques, used as controls here.
"""
import hashlib
import json
import random
from pathlib import Path

P = 21888242871839275222246405745257275088548364400416034343698204186575808495617
LIMIT = 1 << 256
LIMB = 1 << 128


def bits2num(bits):
    return sum(bit * (1 << i) for i, bit in enumerate(bits)) % P


def bits(x, width=256):
    assert 0 <= x < (1 << width)
    return [(x >> i) & 1 for i in range(width)]


def strict(x):
    if not 0 <= x < P:
        raise ValueError("noncanonical field integer")
    return x


def limbs(x):
    assert 0 <= x < LIMIT
    return (x % LIMB, x // LIMB)


def decode(pair):
    lo, hi = pair
    assert 0 <= lo < LIMB and 0 <= hi < LIMB
    return lo + LIMB * hi


def digest(x):
    return hashlib.sha256(str(x).encode()).hexdigest()


collision = []
for x in [0, 1, 42, P - 1]:
    y = x + P
    assert y < LIMIT
    a, b = bits2num(bits(x)), bits2num(bits(y))
    assert a == b and x != y and digest(x) != digest(y)
    assert limbs(x) != limbs(y)
    collision.append({"left_integer": str(x), "right_integer": str(y),
                      "same_field_value": str(a), "external_sha256_differs": True})

rng = random.Random(7821)
samples = [0, 1, P - 1, P, P + 1, LIMB - 1, LIMB, LIMIT - 1]
samples += [rng.randrange(LIMIT) for _ in range(10000)]
roundtrip = all(decode(limbs(x)) == x for x in samples)
strict_rejects = sum(x >= P for x in samples)
for x in samples:
    try:
        encoded = strict(x)
        assert x < P and encoded == x
    except ValueError:
        assert x >= P

result = {
    "status": "KNOWN_CLASS_REPRODUCED_WITH_CONTROLS",
    "source": "https://github.com/iden3/circomlib/blob/master/circuits/bitify.circom",
    "strict_control_source": "https://github.com/iden3/circomlib/blob/master/circuits/aliascheck.circom",
    "requirements_source": "https://docs.zkproof.org/pages/reference/versions/ZkpComRef-0-2.pdf",
    "synthetic_assumption": "External records distinguish every uint256 integer; encoding reduces one such integer into one BN254 scalar field element.",
    "executed": "Python transcription of public field-accumulation behavior, with a synthetic external-record boundary.",
    "not_executed": "Circom compilation, proof generation, real application integration, automatic code extraction, or benchmark against zkFuzz.",
    "collision_cases": collision,
    "strict_field_control_rejects_aliases": True,
    "strict_field_control_rejected_samples": strict_rejects,
    "strict_field_limitation": "Rejecting integers >= P is insufficient when the declared external domain is all uint256 values.",
    "generated_bridge": "uint256 x maps to (x mod 2^128, floor(x/2^128)); require each limb in [0,2^128).",
    "limb_roundtrips": len(samples) if roundtrip else 0,
    "limb_aliases_separated": len(collision),
    "all_domain_argument": "Euclidean division has unique quotient and remainder; because 2^128 < P, both constrained limbs embed injectively. This is a mathematical argument, not a machine-checked proof.",
    "interpretation": "A perfectly deterministic field computation can violate an external integer-identity requirement. Existing strict and limb techniques already fix the class. Only automatic derivation and verification of such boundary contracts remains a candidate opportunity; this probe does not establish it."
}
out = Path(__file__).with_name("e2_probe_results.json")
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"result": str(out), "collision_pairs": len(collision),
                  "limb_roundtrips": len(samples), "strict_rejects": strict_rejects,
                  "novel_bug_claim": False}))
