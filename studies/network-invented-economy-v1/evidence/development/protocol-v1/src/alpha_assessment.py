# SPDX-License-Identifier: Apache-2.0
"""Pure, explicit net-advantage arithmetic, not a truth or novelty oracle.

Paired observations compare the candidate (or complete bundle) with competent,
versioned Beta plus its declared available capabilities. Gains precede the listed
incremental lifecycle costs. Every monetary item must use the same unit and scope.
The supplied uncertainty margin is a declared bound; this module does not infer
frequentist coverage from a small sample or turn modeled gains into observations.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass

ALPHA_SCHEMA = "beyond-beta.alpha-assessment.v1"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_SOURCES = frozenset({"actual-local-experiment", "simulation", "simulation-fixture", "reported-measurement"})


def _finite(value: float, name: str, *, nonnegative: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be finite numeric data")
    if nonnegative and value < 0:
        raise ValueError(name + " cannot be negative")


def _hash(value: object) -> str:
    encoded = json.dumps([ALPHA_SCHEMA, value], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class AlphaCosts:
    """TOTAL incremental lifecycle costs, including explicit zeros, never rates.

Construction includes unsuccessful search allocated to this campaign; validation
includes independent confirmation; integration includes adaptation/recovery;
operating includes incremental delivery/tool cost; risk is expected residual loss.
Costs already deducted in a paired gain must not be entered a second time. A
cost-accounting protocol must therefore define gains before these listed costs.
"""

    acquisition: float = 0.0
    construction: float = 0.0
    validation: float = 0.0
    integration: float = 0.0
    operating: float = 0.0
    risk: float = 0.0
    maintenance: float = 0.0
    migration: float = 0.0
    distribution: float = 0.0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            _finite(value, name, nonnegative=True)

    @property
    def total(self) -> float:
        return math.fsum(asdict(self).values())


@dataclass(frozen=True)
class BetaBaseline:
    """Versioned competent-comparator specification; content is externally justified.

configuration_hash covers exact models/settings/tools/decomposition and prior
capabilities. Merely filling this record does not establish competent model use.
"""

    beta_id: str
    configuration_hash: str
    description: str
    source_kind: str

    def __post_init__(self) -> None:
        if not self.beta_id or not self.description or self.source_kind not in _SOURCES:
            raise ValueError("a versioned, described Beta provenance is required")
        if not isinstance(self.configuration_hash, str) or _DIGEST.fullmatch(self.configuration_hash) is None:
            raise ValueError("Beta configuration requires an exact SHA256 digest")

    @property
    def hash(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class AlphaAssessment:
    """Scoped paired advantage over Beta plus a pinned capability-set snapshot.

planned_reuse is a declared prospective reuse expectation, not observed demand.
dependency_hashes pins the complete assessed bundle's direct prerequisites and
candidate-only components. A bundle can pass even when its components cannot.
"""

    beta_id: str
    comparator_capability_set_hash: str
    scope: tuple[str, ...]
    paired_gains: tuple[float, ...]
    planned_reuse: float
    costs: AlphaCosts
    uncertainty_margin_per_use: float
    source_kind: str
    protocol_id: str
    evidence_hash: str
    dependency_hashes: tuple[str, ...] = ()
    redundant: bool = False
    unit: str = "USD"
    paired_weights: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if not self.beta_id or not self.protocol_id or not self.unit or self.source_kind not in _SOURCES:
            raise ValueError("Beta, protocol, common unit and supported provenance are required")
        if not isinstance(self.scope, tuple) or not self.scope or not all(isinstance(s, str) and s for s in self.scope):
            raise ValueError("assessment scope must be an immutable nonempty tuple")
        if len(set(self.scope)) != len(self.scope):
            raise ValueError("duplicate assessment scopes")
        if not isinstance(self.paired_gains, tuple) or len(self.paired_gains) < 2:
            raise ValueError("at least two paired observations are required")
        for gain in self.paired_gains:
            _finite(gain, "paired gain")
        if not isinstance(self.paired_weights, tuple):
            raise ValueError("paired weights must be immutable")
        if self.paired_weights:
            if len(self.paired_weights) != len(self.paired_gains):
                raise ValueError("paired weights must match paired observations")
            for weight in self.paired_weights:
                _finite(weight, "paired weight", nonnegative=True)
            if not math.fsum(self.paired_weights) > 0:
                raise ValueError("paired weights must have positive total mass")
        _finite(self.planned_reuse, "planned reuse", nonnegative=True)
        _finite(self.uncertainty_margin_per_use, "uncertainty margin", nonnegative=True)
        if not isinstance(self.costs, AlphaCosts) or type(self.redundant) is not bool:
            raise ValueError("immutable complete costs and explicit redundancy decision are required")
        if not isinstance(self.dependency_hashes, tuple) or len(set(self.dependency_hashes)) != len(self.dependency_hashes):
            raise ValueError("dependency hashes must be an immutable unique tuple")
        for value in (self.comparator_capability_set_hash, self.evidence_hash, *self.dependency_hashes):
            if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
                raise ValueError("assessment bindings require exact SHA256 digests")

    @property
    def hash(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class AlphaDecision:
    """Arithmetic decision within the supplied scope, assumptions and uncertainty."""

    accepted: bool
    lower_net: float
    expected_net: float
    upper_net: float
    reason: str
    assessment_hash: str
    beta_id: str
    source_kind: str


def evaluate_alpha(assessment: AlphaAssessment) -> AlphaDecision:
    """Require a strictly positive lower net bound after every declared cost.

This pure numeric gate neither validates observations nor chooses the margin,
demand forecast, comparator competence, cost completeness or admissible scope.
Those are recorded scientific/policy responsibilities; graph validation binds
the exact assessment to independent eligible attestations before admission.
"""
    weights = assessment.paired_weights or tuple(1.0 for _ in assessment.paired_gains)
    mean = math.fsum(value * weight for value, weight in zip(assessment.paired_gains, weights)) / math.fsum(weights)
    net = mean * assessment.planned_reuse - assessment.costs.total
    radius = assessment.uncertainty_margin_per_use * assessment.planned_reuse
    lower, upper = net - radius, net + radius
    if not all(math.isfinite(value) for value in (net, radius, lower, upper)):
        raise ValueError("assessment arithmetic exceeds finite range")
    accepted = lower > 0 and not assessment.redundant
    reason = "positive-lower-net-bound" if accepted else (
        "redundant-with-comparator" if assessment.redundant else "nonpositive-lower-net-bound"
    )
    return AlphaDecision(accepted, lower, net, upper, reason, assessment.hash, assessment.beta_id,
                         assessment.source_kind)
