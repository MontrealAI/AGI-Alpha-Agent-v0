# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import itertools

import pytest

from .audit import Packet, State, audit, verify_assessment
from .reference import relational_audit


def packet(outputs: list[list[int]], views: list[str] | None = None) -> Packet:
    return Packet(
        opportunity_id="reserve-opportunity",
        mission_id="fixed-mission",
        worker_sha256="a" * 64,
        minimum_alternatives=2,
        required_state_ids=[f"s-{i}" for i in range(len(outputs))],
        states=[
            State(state_id=f"s-{i}", secret_value=i, observer_view=views[i] if views else "public-view", outputs=value)
            for i, value in enumerate(outputs)
        ],
    )


@pytest.mark.parametrize("truth_table", range(256))
def test_every_three_bit_boolean_function(truth_table: int) -> None:
    p = packet([[(truth_table >> i) & 1] for i in range(8)])
    decision, minimum = relational_audit(p.model_dump()["states"], 2)
    actual = audit(p)
    assert decision == (actual["decision"] == "eligible-for-separate-authorization")
    assert minimum == actual["minimum_alternatives"]


def test_composition_and_side_information() -> None:
    columns = [[(i >> bit) & 1 for bit in range(3)] for i in range(8)]
    for bit in range(3):
        assert audit(packet([[row[bit]] for row in columns]))["minimum_alternatives"] == 4
    assert audit(packet(columns))["decision"] == "refuse-entire-batch"
    two = [[i & 1, (i >> 1) & 1] for i in range(8)]
    assert audit(packet(two))["minimum_alternatives"] == 2
    assert audit(packet(two, [str(i >> 2) for i in range(8)]))["minimum_alternatives"] == 1


def test_denial_is_not_selected_by_actual_secret() -> None:
    p = packet([[int(i == 7)] for i in range(8)])
    original = audit(p)
    assert original["decision"] == "refuse-entire-batch"
    for order in itertools.islice(itertools.permutations(range(8)), 24):
        changed = p.model_copy(update={"states": [p.states[i] for i in order]})
        assert audit(changed)["decision"] == original["decision"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("mission_id", "different"),
        ("worker_sha256", "b" * 64),
        ("opportunity_id", "another"),
        ("minimum_alternatives", 3),
    ],
)
def test_cross_scope_or_stale_assessment_refused(field: str, value: object) -> None:
    p = packet([[i & 1] for i in range(8)])
    result = audit(p)
    changed = Packet.model_validate({**p.model_dump(), field: value})
    with pytest.raises(ValueError):
        verify_assessment(changed, result)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "short-output", "live", "bool", "unknown-field"])
def test_invalid_packets_refused(mutation: str) -> None:
    data = packet([[i & 1, (i >> 1) & 1] for i in range(8)]).model_dump()
    if mutation == "missing":
        data["states"].pop()
    elif mutation == "duplicate":
        data["states"][1]["state_id"] = data["states"][0]["state_id"]
    elif mutation == "short-output":
        data["states"][0]["outputs"].pop()
    elif mutation == "live":
        data["mode"] = "live"
    elif mutation == "bool":
        data["states"][0]["outputs"][0] = True
    else:
        data["authority"] = "production-approved"
    with pytest.raises(ValueError):
        Packet.model_validate(data)


def test_round_trip_and_imported_authority() -> None:
    p = packet([[i & 1] for i in range(8)])
    restored = Packet.model_validate_json(p.model_dump_json())
    assert audit(restored) == audit(p)
    result = copy.deepcopy(audit(p))
    result["authority"] = "production-approved"
    with pytest.raises(ValueError):
        verify_assessment(restored, result)


def test_known_output_is_not_called_informative() -> None:
    p = packet([[i & 1] for i in range(8)], [str(i & 1) for i in range(8)])
    assert audit(p)["nonconstant"] is False
    result = copy.deepcopy(audit(p))
    result["minimum_alternatives"] = 4.0
    with pytest.raises(ValueError):
        verify_assessment(p, result)
