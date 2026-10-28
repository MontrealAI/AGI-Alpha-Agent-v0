# SPDX-License-Identifier: Apache-2.0
"""Conservation, adversarial contracts, current controls and independent parity."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contrib.production_frontier.cases import case
from contrib.production_frontier.engine import ConstructionPolicy, ProductionBrief, ablate, construct
from contrib.production_frontier.manifest import freeze, verify_freeze
from contrib.production_frontier.native import LiveAdapter, proposal
from contrib.production_frontier.verify import exhaustive, replay, verify


@pytest.mark.parametrize("domain", ["transformer", "metrology"])
@pytest.mark.parametrize("seed", range(101, 113))
def test_fresh_numerical_and_eligibility_cases_match_strong_conventional(domain: str, seed: int) -> None:
    brief = case(domain, seed)
    result, baseline = construct(brief), exhaustive(brief)
    assert result["search_complete"] is True
    assert (result["best"] is None) == (baseline is None)
    if baseline:
        assert result["best"]["rank"] == baseline["rank"]
        assert verify(brief, ConstructionPolicy(), result)
    assert result["authority_granted"] is False


def ready() -> ProductionBrief:
    raw = case("transformer", 103).model_dump()
    raw["cost_cap_micro_usd"] = 15_000_000_000
    raw["seconds_cap"] = 10_800
    return ProductionBrief.model_validate(raw)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(authority_granted=True),
        lambda r: r.update(real_actions_executed=True),
        lambda r: r.update(scientific_or_commercial_acceptance=True),
        lambda r: r.update(binding="0" * 64),
        lambda r: r.update(adapter="live"),
        lambda r: r.update(disabled=["shared-batch"]),
        lambda r: r.update(conventional_only=True),
        lambda r: r.update(states=True),
        lambda r: r.update(status="customer-accepted"),
        lambda r: r.update(input_mode="authorized-measurements"),
    ],
)
def test_forged_result_headers_refuse(mutate) -> None:
    brief = ready()
    report = construct(brief)
    mutate(report)
    assert not verify(brief, ConstructionPolicy(), report)


@pytest.mark.parametrize(
    "field,value",
    [
        ("estimated_cost_micro_usd", 0),
        ("seconds", False),
        ("pending_permissions", ["hidden-approval"]),
        ("capabilities", ["new-authority"]),
        ("stock", {"usable-a": 99999}),
        ("steps", ["invented-recipe"]),
    ],
)
def test_forged_witnesses_refuse(field: str, value) -> None:
    brief = ready()
    report = construct(brief)
    report["candidates"][0][field] = value
    assert not verify(brief, ConstructionPolicy(), report)


def test_consumable_resource_is_not_a_monotone_fact() -> None:
    raw = ready().model_dump()
    raw["stock"]["material"] = 1
    brief = ProductionBrief.model_validate(raw)
    assert construct(brief)["status"] == "no-plan"


def test_destructive_order_and_fresh_validation_material_survive() -> None:
    raw = case("metrology", 101).model_dump()
    raw["cost_cap_micro_usd"] = 6_000_000_000
    raw["seconds_cap"] = 10_800
    brief = ProductionBrief.model_validate(raw)
    result = construct(brief)
    if raw["stock"]["blank"] >= 5:
        assert result["best"]
        steps = result["best"]["steps"]
        assert steps.index("image-interior") < steps.index("destructive-test")
        assert verify(brief, ConstructionPolicy(), result)
    raw["stock"]["blank"] = 3
    raw["recipes"] = [r for r in raw["recipes"] if r["recipe_id"] != "conventional-laboratory"]
    assert construct(ProductionBrief.model_validate(raw))["status"] == "no-plan"


def test_all_original_obligations_required() -> None:
    raw = ready().model_dump()
    for r in raw["recipes"]:
        r["preserves"] = ["no-inferred-authority"]
    assert construct(ProductionBrief.model_validate(raw))["status"] == "no-plan"


def test_forbidden_resource_not_used_and_old_result_not_reused() -> None:
    brief = ready()
    report = construct(brief)
    changed = brief.model_dump()
    changed["recipes"][0]["permission"] = "denied"
    changed = ProductionBrief.model_validate(changed)
    assert not verify(changed, ConstructionPolicy(), report)
    rebuilt = construct(changed)
    assert changed.recipes[0].recipe_id not in (rebuilt["best"] or {}).get("steps", [])


def test_budget_exhaustion_and_cancellation_are_not_no_plan_proofs() -> None:
    raw = ready().model_dump()
    raw["state_cap"] = 1
    assert construct(ProductionBrief.model_validate(raw))["status"] == "incomplete"
    result = construct(ready(), cancelled=lambda: True)
    assert result["status"] == "cancelled" and result["search_complete"] is False
    assert not result["best"]


def test_ablations_credit_available_conventional_replacement() -> None:
    brief = ready()
    result = ablate(brief)
    assert result["original"]["best"]
    for row in result["ablations"]:
        assert row["verdict"] in {"necessary-in-declared-model", "improves-declared-objective", "not-necessary"}
        alternate = row["result"]
        if alternate["best"]:
            assert verify(brief, ConstructionPolicy(), alternate, disabled=frozenset({row["removed"]}))
    conventional = construct(brief, conventional_only=True)
    assert conventional["best"]
    assert verify(brief, ConstructionPolicy(), conventional, conventional_only=True)


def test_existing_library_with_same_asset_is_not_claimed_retained_alpha() -> None:
    brief = ready()
    first = construct(brief)
    reused = construct(ProductionBrief.model_validate_json(brief.model_dump_json()))
    assert first == reused
    assert first["best"]["rank"] == exhaustive(brief)["rank"]


@pytest.mark.parametrize("change", ["policy", "case", "source", "acceptance"])
def test_modified_configuration_cannot_pass_old_frozen_manifest(tmp_path: Path, change: str) -> None:
    paths = ["policy", "case", "source", "acceptance"]
    for name in paths:
        (tmp_path / name).write_text(json.dumps({name: "v1"}))
    manifest = freeze(tmp_path, paths, tmp_path / "FREEZE.json")
    verify_freeze(tmp_path, manifest)
    (tmp_path / change).write_text(json.dumps({change: "v2"}))
    with pytest.raises(ValueError, match="frozen input changed"):
        verify_freeze(tmp_path, manifest)
    with pytest.raises(FileExistsError):
        freeze(tmp_path, paths, tmp_path / "FREEZE.json")


def test_source_paths_cannot_escape_or_be_symlinks(tmp_path: Path) -> None:
    (tmp_path / "escape").symlink_to(__file__)
    with pytest.raises(ValueError):
        freeze(tmp_path, ["escape"], tmp_path / "FREEZE.json")
    with pytest.raises(ValueError):
        verify_freeze(tmp_path, {"schema": "production-frontier-freeze/v1", "files": {"escape": "0" * 64}})


@pytest.mark.parametrize("mutation", ["unknown-resource", "duplicate-recipe", "bool-cost", "unknown-source"])
def test_input_contract_refuses_semantic_ambiguities(mutation: str) -> None:
    raw = ready().model_dump()
    if mutation == "unknown-resource":
        raw["stock"]["unclear-unit"] = 1
    elif mutation == "duplicate-recipe":
        raw["recipes"][1]["recipe_id"] = raw["recipes"][0]["recipe_id"]
    elif mutation == "bool-cost":
        raw["recipes"][0]["estimated_cost_micro_usd"] = False
    else:
        raw["recipes"][0]["sources"] = ["fabricated-source"]
    with pytest.raises(ValidationError):
        ProductionBrief.model_validate(raw)


def test_native_proposal_reuses_schema_without_saving_or_granting() -> None:
    obj = proposal(ready())
    assert obj.mode == "simulation" and obj.needs[0].evidence_kind == "synthetic"
    assert obj.parent_opportunity is None
    assert len(obj.formulations) == 2
    assert obj.needs[0].evidence[0].journal_key.startswith("@production-frontier-proposal:")


def test_unavailable_live_adapter_never_returns_simulated_success() -> None:
    adapter = LiveAdapter()
    assert adapter.status()["ready_for_signed_permit"] is False
    assert adapter.status()["simulated_fallback"] is False
    with pytest.raises(ValueError, match="live frontier access unavailable"):
        adapter.run(None, None)


def test_duplicate_and_wrong_order_witnesses_refuse() -> None:
    brief = ready()
    steps = construct(brief)["best"]["steps"]
    with pytest.raises(ValueError):
        replay(brief, steps + steps, disabled=[], conventional_only=False)
    with pytest.raises(ValueError):
        replay(brief, list(reversed(steps)), disabled=[], conventional_only=False)


def test_reordering_recipe_records_preserves_optimum() -> None:
    brief = ready()
    raw = copy.deepcopy(brief.model_dump())
    raw["recipes"].reverse()
    changed = ProductionBrief.model_validate(raw)
    assert construct(brief)["best"] == construct(changed)["best"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope", "PHYSICAL TRUTH AND REAL APPROVAL ESTABLISHED"),
        ("retained_alpha", True),
        ("candidate_count", 0),
        ("candidate_count", "1"),
    ],
)
def test_review_found_unsupported_envelope_claims_refuse(field: str, value) -> None:
    brief = ready()
    report = construct(brief)
    report[field] = value
    assert not verify(brief, ConstructionPolicy(), report)


def test_review_found_shallow_model_mutation_refuses() -> None:
    brief = ready()
    report = construct(brief)
    brief.recipes[0].consumes["material"] = -1
    assert not verify(brief, ConstructionPolicy(), report)
    with pytest.raises(ValidationError):
        replay(brief, report["best"]["steps"], disabled=[], conventional_only=False)


def test_review_found_dangling_freeze_destination_refuses(tmp_path: Path) -> None:
    (tmp_path / "source").write_text("unchanged")
    (tmp_path / "FREEZE.json").symlink_to(tmp_path / "uncreated-target")
    with pytest.raises(FileExistsError):
        freeze(tmp_path, ["source"], tmp_path / "FREEZE.json")
    assert not (tmp_path / "uncreated-target").exists()


def test_review_found_string_steps_and_duplicate_candidates_refuse() -> None:
    brief = ready()
    report = construct(brief)
    report["candidates"][0]["steps"] = "a"
    assert not verify(brief, ConstructionPolicy(), report)


def test_review_found_offered_best_cannot_ignore_a_cheaper_offered_candidate() -> None:
    brief = ready()
    report = construct(brief)
    assert len(report["candidates"]) > 1
    report["candidates"][0], report["candidates"][1] = report["candidates"][1], report["candidates"][0]
    report["best"] = report["candidates"][0]
    assert not verify(brief, ConstructionPolicy(), report)
    report = construct(brief)
    report["candidates"] = [report["best"]] * 8
    report["candidate_count"] = 8
    assert not verify(brief, ConstructionPolicy(), report)
