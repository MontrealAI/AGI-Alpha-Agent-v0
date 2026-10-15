# SPDX-License-Identifier: Apache-2.0
"""Separate supplier contract and observed-output checks; no provider or Docker claim."""
import json
import pytest
from alpha_factory_v1.core.runtime.supplier_browser_spec import (
    SupplierSpec,
    read_spec,
    computer_task,
    expected_report,
    extract_artifacts,
    BEGIN,
    END,
)
from alpha_factory_v1.core.runtime.work_spec import read_spec as read_compute_spec


def specification():
    return SupplierSpec.model_validate(
        {
            "schema": "agialpha.supplier-browser-spec.v1",
            "market": "agijobsv0-jobregistry-v2",
            "executor": "alpha-supplier-browser-v1",
            "input_rights": "synthetic",
            "maxDeliveryDays": 7,
            "quotes": [
                {"supplier": "Boreal", "quantity": 40, "unitCents": 1250, "shippingCents": 3000, "deliveryDays": 5},
                {
                    "supplier": "Laurentian",
                    "quantity": 40,
                    "unitCents": 1100,
                    "shippingCents": 2000,
                    "deliveryDays": 12,
                },
                {"supplier": "Stellar", "quantity": 40, "unitCents": 1200, "shippingCents": 1000, "deliveryDays": 7},
            ],
        }
    )


def visible(value):
    return BEGIN + "\n" + json.dumps(value) + "\n" + END


def test_separate_spec_exact_commitment_and_old_contract_refusal():
    spec = specification()
    raw = spec.model_dump_json(by_alias=True).encode()
    assert read_spec(raw)[0] == spec
    assert read_spec(raw)[1] != read_spec(raw + b"\n")[1]
    with pytest.raises(ValueError):
        read_compute_spec(raw)
    assert computer_task(spec).allowed_urls == []
    assert "<script" in computer_task(spec).html


def test_observed_artifacts_and_independent_arithmetic():
    spec = specification()
    report = expected_report(spec)
    assert [q["totalCents"] for q in report["quotes"]] == [53000, 46000, 49000]
    assert report["recommendedSupplier"] == "Stellar"
    result = extract_artifacts(spec, visible(report))
    assert result["acceptance"]["accepted"] and not result["acceptance"]["settlementApproved"]
    assert [a["name"] for a in result["artifacts"]] == ["comparison.json", "recommendation.md"]
    report["recommendedSupplier"] = "Boreal"
    with pytest.raises(ValueError):
        extract_artifacts(spec, visible(report))


@pytest.mark.parametrize("mutation", ["bool", "quantity", "duplicate", "html", "rights", "executor"])
def test_invalid_authority_or_incomparable_quotes_refused(mutation):
    value = specification().model_dump(by_alias=True)
    if mutation == "bool":
        value["quotes"][0]["unitCents"] = True
    if mutation == "quantity":
        value["quotes"][0]["quantity"] = 41
    if mutation == "duplicate":
        value["quotes"][0]["supplier"] = "Stellar"
    if mutation == "html":
        value["quotes"][0]["supplier"] = "</script>"
    if mutation == "rights":
        value["input_rights"] = "private"
    if mutation == "executor":
        value["executor"] = "fleet-linux-v1"
    with pytest.raises(ValueError):
        SupplierSpec.model_validate(value)


@pytest.mark.parametrize("text", ["not computed", BEGIN + END, BEGIN + "{}" + END + BEGIN, "x" * 64001])
def test_missing_ambiguous_or_oversized_observation_refused(text):
    with pytest.raises(ValueError):
        extract_artifacts(specification(), text)


def test_ties_no_eligible_and_large_exact_integer_totals():
    value = specification().model_dump(by_alias=True)
    for quote in value["quotes"]:
        quote.update(quantity=1000000, unitCents=1000000000, shippingCents=1000000000, deliveryDays=7)
    report = expected_report(SupplierSpec.model_validate(value))
    assert report["recommendedSupplier"] == "Boreal"
    assert report["quotes"][0]["totalCents"] == 1000001000000000
    value["maxDeliveryDays"] = 1
    report = expected_report(SupplierSpec.model_validate(value))
    assert report["recommendedSupplier"] is None


def test_real_chromium_observation_matches_independent_reviewer():
    playwright = pytest.importorskip("playwright.sync_api")
    spec = specification()
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(computer_task(spec).html)
        with pytest.raises(ValueError):
            extract_artifacts(spec, page.locator("body").inner_text())
        page.locator("#delivery").select_option("7")
        page.locator("#compare").click()
        result = extract_artifacts(spec, page.locator("body").inner_text())
        assert result["acceptance"]["accepted"]
        page.locator("#delivery").select_option("1")
        page.locator("#compare").click()
        with pytest.raises(ValueError):
            extract_artifacts(spec, page.locator("body").inner_text())
        browser.close()
