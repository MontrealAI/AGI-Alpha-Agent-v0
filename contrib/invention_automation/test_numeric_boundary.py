# SPDX-License-Identifier: Apache-2.0
"""Preserve the actual scientific-token false confirmation as a regression."""

from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from alpha_factory_v1.core.runtime.invention_automation import critic_loop, evidence_critic
from alpha_factory_v1.core.runtime.invention_automation.evidence_contracts import Objection
from contrib.invention_automation import critic_verify
from contrib.invention_automation.test_critic_loop import PROVENANCE, context, request


@pytest.mark.parametrize("marker", ["e", "E"])
@pytest.mark.parametrize("suffix", ["+3", "-3", "3", "+", "-", ".3", ""])
@pytest.mark.parametrize("clipped", [False, True])
def test_scientific_token_cannot_become_a_dimension_objection(marker: str, suffix: str, clipped: bool) -> None:
    value = request()
    original = evidence_critic.investigate(value, context(value), PROVENANCE).objections[0].to_dict()
    excerpt = "high-side voltage of less than 34.5" + marker + suffix + " kVA"
    source = value["sources"][0]
    source.update(excerpt=excerpt, sha256=hashlib.sha256(excerpt.encode()).hexdigest())
    value["records"][0]["fields"]["high_side_voltage"] = {"value": "69/2", "unit": marker}
    ctx = context(value)
    if clipped:
        ctx["bindings"][0]["end"] = len("high-side voltage of less than 34.5" + marker)
    end = ctx["bindings"][0]["end"]
    original["source"].update(sha256=source["sha256"], location=f"/sources/0/excerpt#chars=0:{end}")
    original["witness"].update(value="69/2", unit=marker, end=end)
    objection = Objection.from_dict(original)
    assert not evidence_critic.investigate(value, ctx, PROVENANCE).objections
    receipt = critic_verify.adjudicate(value, ctx, objection.to_dict())
    assert receipt["verdict"] in {"REFUTED", "INCONCLUSIVE"}
    if clipped and suffix in {"+3", "-3"}:
        assert receipt["verdict"] == "REFUTED"
    with pytest.raises(ValueError, match="only a reproduced"):
        critic_loop.construct_verified(value, ctx, objection, receipt)


@pytest.mark.parametrize("separator", ["", " ", "\t"])
def test_complete_plain_decimal_and_unknown_unit_remain_supported(separator: str) -> None:
    value = request()
    source = value["sources"][0]
    source["excerpt"] = "high-side voltage of less than 34.5" + separator + "unknown"
    source["sha256"] = hashlib.sha256(source["excerpt"].encode()).hexdigest()
    value["records"][0]["fields"]["high_side_voltage"]["unit"] = "unknown"
    ctx = context(value)
    finding = evidence_critic.investigate(value, ctx, PROVENANCE)
    assert len(finding.objections) == 1
    receipt = critic_verify.adjudicate(value, ctx, finding.objections[0].to_dict())
    assert receipt["verdict"] == "CONFIRMED"
    assert receipt["candidate_executed"] is False
    safe = deepcopy(value)
    safe["baseline"] = deepcopy(safe["proposal"])
    assert not evidence_critic.investigate(safe, ctx, PROVENANCE).objections
