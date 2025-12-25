"""Validate $AGIALPHA token configuration consistency.

This helper compares the canonical token config, Solidity constants, and
any workflow-provided environment variables so CI fails fast if values drift.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TOKEN_CONFIG = ROOT / "token.config.js"
CONTRACT_CONSTANTS = ROOT / "contracts/v2/Constants.sol"
TEST_CONSTANTS = ROOT / "tests/contracts/contracts/v2/Constants.sol"
TRUFFLE_MIGRATION = ROOT / "truffle/migrations/2_deploy_agijobs_v2.js"
PY_TOKEN_UTILS = ROOT / "alpha_factory_v1/utils/token_utils.py"
JS_TOKEN_UTILS = ROOT / "tests/contracts/test/utils/token.js"
WORKFLOWS = (
    ROOT / ".github/workflows/ci.yml",
    ROOT / ".github/workflows/pr-ci.yml",
    ROOT / ".github/workflows/ci-health.yml",
    ROOT / ".github/workflows/smoke.yml",
)


@dataclass(frozen=True)
class TokenConfig:
    address: str
    decimals: int

    @property
    def normalized_address(self) -> str:
        return self.address.lower()


CANONICAL_TOKEN = TokenConfig(
    address="0xa61a3b3a130a9c20768eebf97e21515a6046a1fa",
    decimals=18,
)


def _extract_pattern(path: Path, pattern: str, label: str) -> str:
    match = re.search(pattern, path.read_text())
    if not match:
        raise ValueError(f"Could not find {label} in {path}")
    return match.group(1)


def load_token_config() -> TokenConfig:
    address = _extract_pattern(
        TOKEN_CONFIG,
        r"AGIALPHA_ADDRESS:\s*['\"]([^'\"]+)['\"]",
        "AGIALPHA address",
    )
    decimals = int(
        _extract_pattern(
            TOKEN_CONFIG,
            r"AGIALPHA_DECIMALS:\s*([0-9]+)",
            "AGIALPHA decimals",
        )
    )
    return TokenConfig(address=address, decimals=decimals)


def load_contract_constants(path: Path) -> TokenConfig:
    address = _extract_pattern(
        path,
        r"AGIALPHA\s*=\s*(0x[0-9a-fA-F]+)",
        "contract AGIALPHA address",
    )
    decimals = int(
        _extract_pattern(
            path,
            r"AGIALPHA_DECIMALS\s*=\s*([0-9]+)",
            "contract AGIALPHA decimals",
        )
    )
    return TokenConfig(address=address, decimals=decimals)


def load_truffle_migration(expected: TokenConfig) -> TokenConfig:
    text = TRUFFLE_MIGRATION.read_text()
    if not re.search(r"process\.env\.AGIALPHA_ADDRESS\s*\|\|\s*AGIALPHA_ADDRESS", text):
        raise ValueError("truffle migration must default to AGIALPHA_ADDRESS when env var is unset")
    if not re.search(r"Number\(process\.env\.AGIALPHA_DECIMALS\s*\|\|\s*AGIALPHA_DECIMALS\)", text):
        raise ValueError("truffle migration must default to AGIALPHA_DECIMALS when env var is unset")
    if not re.search(r"agiDecimals\s*!==\s*18", text):
        raise ValueError("truffle migration AGIALPHA decimal guard must enforce 18 decimals")
    return TokenConfig(address=expected.address, decimals=expected.decimals)


def load_workflow_config(path: Path) -> TokenConfig:
    address = _extract_pattern(
        path,
        r"AGIALPHA_ADDRESS:\s*\"?([^\"\n]+)\"?",
        f"workflow {path.name} AGIALPHA address",
    )
    decimals = int(
        _extract_pattern(
            path,
            r"AGIALPHA_DECIMALS:\s*([0-9]+)",
            f"workflow {path.name} AGIALPHA decimals",
        )
    )
    return TokenConfig(address=address, decimals=decimals)


def load_python_token_utils(path: Path) -> TokenConfig:
    decimals = int(
        _extract_pattern(
            path,
            r"AGIALPHA_DECIMALS\s*=\s*([0-9]+)",
            "Python token utils decimals",
        )
    )
    # Default to the canonical address because the Python helper only tracks decimals.
    return TokenConfig(address=CANONICAL_TOKEN.address, decimals=decimals)


def verify_js_token_utils(path: Path, expected: TokenConfig) -> None:
    text = path.read_text()
    if "token.config" not in text:
        raise ValueError("JavaScript token utils must import token.config.js for canonical values")
    if "AGIALPHA_ADDRESS" not in text or "AGIALPHA_DECIMALS" not in text:
        raise ValueError("JavaScript token utils must surface AGIALPHA constants from token.config.js")
    if re.search(r"AGIALPHA_ADDRESS\s*=\s*['\"]", text):
        raise ValueError("JavaScript token utils must not hardcode AGIALPHA; import token.config.js instead")


def _env_config() -> TokenConfig | None:
    address = os.getenv("AGIALPHA_ADDRESS")
    decimals = os.getenv("AGIALPHA_DECIMALS")
    if not address and not decimals:
        return None
    if not address or not decimals:
        raise ValueError("Both AGIALPHA_ADDRESS and AGIALPHA_DECIMALS must be set together")
    return TokenConfig(address=address, decimals=int(decimals))


def compare_configs(reference: TokenConfig, other: TokenConfig, labels: Iterable[str]) -> None:
    label = "/".join(labels)
    if reference.normalized_address != other.normalized_address:
        raise ValueError(f"{label} address mismatch: {other.address} (got) != {reference.address} (expected)")
    if reference.decimals != other.decimals:
        raise ValueError(f"{label} decimals mismatch: {other.decimals} (got) != {reference.decimals} (expected)")


def main() -> int:
    token = load_token_config()
    compare_configs(CANONICAL_TOKEN, token, labels=["expected", "token.config.js"])
    contract = load_contract_constants(CONTRACT_CONSTANTS)
    compare_configs(CANONICAL_TOKEN, contract, labels=["expected", "contracts/Constants.sol"])
    test_contract = load_contract_constants(TEST_CONSTANTS)
    compare_configs(
        CANONICAL_TOKEN,
        test_contract,
        labels=["expected", "tests/contracts/Constants.sol"],
    )
    truffle = load_truffle_migration(token)
    compare_configs(CANONICAL_TOKEN, truffle, labels=["expected", TRUFFLE_MIGRATION.name])
    compare_configs(token, contract, labels=["token.config.js", "contracts/Constants.sol"])
    compare_configs(
        token,
        test_contract,
        labels=["token.config.js", "tests/contracts/Constants.sol"],
    )
    compare_configs(token, truffle, labels=["token.config.js", TRUFFLE_MIGRATION.name])

    for workflow in WORKFLOWS:
        if workflow.exists():
            workflow_config = load_workflow_config(workflow)
            compare_configs(token, workflow_config, labels=["token.config.js", workflow.name])

    python_utils = load_python_token_utils(PY_TOKEN_UTILS)
    compare_configs(token, python_utils, labels=["token.config.js", PY_TOKEN_UTILS.name])

    verify_js_token_utils(JS_TOKEN_UTILS, token)

    env_cfg = _env_config()
    if env_cfg:
        compare_configs(token, env_cfg, labels=["token.config.js", "env"])

    print("AGIALPHA configuration is consistent:\n" f"  address: {token.address}\n" f"  decimals: {token.decimals}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"::error::{exc}")
        raise
