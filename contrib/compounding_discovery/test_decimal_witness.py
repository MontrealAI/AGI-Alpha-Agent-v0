# SPDX-License-Identifier: Apache-2.0
"""Adverse training regressions for exact producer decimal serialization."""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.structural_transfer.eadarp_check import _dec


@pytest.fixture(scope="module")
def canonical_decimal() -> Any:
    from alpha_factory_v1.core.runtime.compounding_discovery.programs import canonical_decimal as installed

    return installed


def test_exact_trailing_zero_diagnostic_case_uses_existing_checker_contract(canonical_decimal: Any) -> None:
    value = Decimal("0.0003480546181440922052701225090")
    with pytest.raises(ValueError, match="precision"):
        _dec(str(value))
    serialized = canonical_decimal(value)
    assert serialized == "0.000348054618144092205270122509"
    assert Decimal(serialized) == value
    assert _dec(serialized) == value


def test_true_thirty_one_place_precision_remains_refused(canonical_decimal: Any) -> None:
    original = "0.0003480546181440922052701225091"
    assert canonical_decimal(Decimal(original)) == original
    with pytest.raises(ValueError, match="precision"):
        _dec(canonical_decimal(Decimal(original)))


@pytest.mark.parametrize(
    "original,expected",
    [("1000.000", "1000"), ("1200", "1200"), ("-0.000", "-0"), ("0E-31", "0"), ("-12.340000", "-12.34")],
)
def test_fractional_zero_trimming_preserves_integer_zeros_and_value(
    canonical_decimal: Any, original: str, expected: str
) -> None:
    serialized = canonical_decimal(Decimal(original))
    assert serialized == expected
    assert Decimal(serialized) == Decimal(original)


def test_serialization_does_not_round_under_small_decimal_context(canonical_decimal: Any) -> None:
    original = Decimal("0.0003480546181440922052701225090")
    with localcontext() as context:
        context.prec = 3
        serialized = canonical_decimal(original)
    assert Decimal(serialized) == original
