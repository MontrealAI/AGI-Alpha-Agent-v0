# SPDX-License-Identifier: Apache-2.0
"""Post-confirmation delivery selector using the unchanged conventional evaluator."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, cast

SOURCE_ROOT = Path(__file__).resolve().parent
FROZEN_HASHES = {
    "verifier": "5392b40020f0482b50dc0a48ea4e6cfbc42ee7e9a6c252a74015c6464935a5a5",
    "expert": "fd4390b85ff38359c6a8915b982a951aaaac383d2c1c2560146552ec9a8645cf",
    "ordinary": "4ba3b068d77892dcd54b07fa045e4b31510ddf806aaa53cdf9dcf15b23674fc1",
}
PROTOCOL_SHA256 = "d05af0f04ea55b1bcc5cf5303e0862dacd509d8cfabd9d216f68689a8467c72a"
NUMERIC_FIELDS = ("cash_margin", "accounting_margin", "npv", "simple_payback")


def _refusal(reason: str) -> dict[str, Any]:
    return {
        "decision": "INVALID_INPUT",
        "reasons": [reason],
        "cash_margin": None,
        "accounting_margin": None,
        "npv": None,
        "simple_payback": None,
        "next_measurements": [],
        "evidence_level": "INPUT_NOT_EVALUATED",
        "operational_authorization": False,
    }


def _evaluator(name: str) -> Callable[[Any], dict[str, Any]]:
    path = SOURCE_ROOT / f"{name}.py"
    if hashlib.sha256(path.read_bytes()).hexdigest() != FROZEN_HASHES[name]:
        raise RuntimeError(f"frozen_source_integrity_mismatch:{name}")
    spec = importlib.util.spec_from_file_location(f"_reuse_delivery_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unavailable_evaluator:{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Callable[[Any], dict[str, Any]], module.evaluate)


def _numeric_agreement(left: dict[str, Any], right: dict[str, Any]) -> bool:
    for field in NUMERIC_FIELDS:
        first, second = left.get(field), right.get(field)
        if first is None or second is None:
            if first != second:
                return False
            continue
        if not isinstance(first, (list, tuple)) or not isinstance(second, (list, tuple)) or len(first) != len(second):
            return False
        for a, b in zip(first, second):
            if a is None or b is None:
                if a != b:
                    return False
            elif not math.isclose(float(a), float(b), rel_tol=1e-8, abs_tol=1e-6):
                return False
    return True


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return f"NONFINITE_DIAGNOSTIC:{value}"
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _metadata(result: dict[str, Any], input_mode: str) -> dict[str, Any]:
    result["delivery_revision"] = "post_confirmation_conventional_selector.v1"
    result["selected_evaluator"] = "unchanged_frozen_conventional_decimal_reference"
    result["input_number_policy"] = input_mode
    result["confirmation_status"] = (
        "Post-confirmation recovery; original confirmation scores and failures are unchanged."
    )
    result["alpha_claim"] = "No Operational Alpha or improved fresh-confirmation rate is claimed."
    result["operational_authorization"] = False
    return result


def deliver(case: Any, compare_originals: bool = True) -> dict[str, Any]:
    """Select the frozen Decimal result and expose original-arm decision disagreements."""
    input_mode = "Python numeric inputs are interpreted by their shortest decimal spelling; booleans are not numbers."
    protocol = SOURCE_ROOT.parent / "protocol" / "acceptance.json"
    if hashlib.sha256(protocol.read_bytes()).hexdigest() != PROTOCOL_SHA256:
        result = _refusal("frozen_protocol_integrity_mismatch")
        result["delivery_blocked"] = True
        return _metadata(result, input_mode)
    try:
        selected = _evaluator("verifier")(copy.deepcopy(case))
    except (OSError, RuntimeError, ValueError, OverflowError, ArithmeticError) as error:
        result = _refusal(f"reference_evaluation_unavailable:{type(error).__name__}")
        result["delivery_blocked"] = True
        return _metadata(result, input_mode)
    selected = copy.deepcopy(selected)
    comparisons: dict[str, Any] = {}
    if compare_originals:
        for name in ("ordinary", "expert"):
            try:
                original = _evaluator(name)(copy.deepcopy(case))
                snapshot = {field: original.get(field) for field in (*NUMERIC_FIELDS, "decision", "reasons")}
                comparisons[name] = {
                    "evaluation_status": "executed_unchanged_frozen_arm",
                    "original_result": _json_safe(snapshot),
                    "decision_disagrees": original.get("decision") != selected.get("decision"),
                    "numbers_within_original_protocol_tolerance": _numeric_agreement(original, selected),
                }
            except (OSError, RuntimeError, ValueError, OverflowError, ArithmeticError, TypeError, KeyError) as error:
                comparisons[name] = {"evaluation_status": "diagnostic_unavailable", "error_type": type(error).__name__}
    selected["original_arm_comparison"] = comparisons
    selected["decision_disagreement_count"] = sum(
        value.get("decision_disagrees", False) for value in comparisons.values()
    )
    selected["reference_source_sha256"] = FROZEN_HASHES["verifier"]
    return _metadata(selected, input_mode)


def _decimal_tokens_to_frozen_inputs(value: Any) -> Any:
    if isinstance(value, Decimal):
        number = float(value)
        if not value.is_finite() or not math.isfinite(number) or Decimal(str(number)) != value:
            raise ValueError("decimal_literal_cannot_round_trip_losslessly_to_frozen_input")
        return number
    if isinstance(value, list):
        return [_decimal_tokens_to_frozen_inputs(item) for item in value]
    if isinstance(value, dict):
        return {key: _decimal_tokens_to_frozen_inputs(item) for key, item in value.items()}
    return value


def _reject_nonfinite_literal(value: str) -> Any:
    raise ValueError(f"nonstandard_nonfinite_json_literal:{value}")


def deliver_json(text: str, compare_originals: bool = True) -> dict[str, Any]:
    """Read JSON number tokens as decimal values and refuse silent precision loss."""
    mode = (
        "JSON numeric literals are parsed as exact decimal tokens, then admitted only if their shortest decimal "
        "round trip into the unchanged frozen evaluator is lossless. Long or out-of-range literals are refused."
    )
    try:
        parsed = json.loads(text, parse_float=Decimal, parse_constant=_reject_nonfinite_literal)
        case = _decimal_tokens_to_frozen_inputs(parsed)
    except (ValueError, OverflowError, ArithmeticError) as error:
        return _metadata(_refusal(f"invalid_json_or_unsupported_decimal_precision:{type(error).__name__}"), mode)
    result = deliver(case, compare_originals=compare_originals)
    result["input_number_policy"] = mode
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Produce a conditional reuse investment screen using the frozen Decimal evaluator."
    )
    parser.add_argument("input", type=Path, help="JSON input record; no plant or payment operations are performed.")
    parser.add_argument("--output", type=Path, help="Optional result path; otherwise writes JSON to standard output.")
    parser.add_argument(
        "--no-comparison", action="store_true", help="Skip diagnostic execution of the original two arms."
    )
    args = parser.parse_args()
    result = deliver_json(args.input.read_text(encoding="utf-8"), compare_originals=not args.no_comparison)
    rendered = json.dumps(_json_safe(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
