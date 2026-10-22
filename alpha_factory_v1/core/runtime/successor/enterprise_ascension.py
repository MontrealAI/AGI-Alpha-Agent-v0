# SPDX-License-Identifier: Apache-2.0
"""Connect retained enterprises to the existing authorized Ascension Studio journey.

This is a facade, not another executor, journal, wallet or admission mechanism.
All chain observations and phase authorization remain in studio_operator.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

from ..store import Conflict, Journal
from . import enterprise, studio_operator
from .protocol import canonical, digest
from .transport import read_document

# Deliberately exclude installation, pairing and local role signing. A journey
# never provisions trust or turns an enterprise configuration into authority.
ACTIONS = ("seal", "bind", "run", "recover", "accept", "settle")


def _request(home: Path, enterprise_id: str, plan: dict[str, Any], index: int) -> dict[str, Any]:
    return cast(dict[str, Any], enterprise.handoff(home, enterprise_id, plan, index))


def prepare(home: Path, enterprise_id: str, plan: dict[str, Any], index: int) -> dict[str, Any]:
    """Prepare exact enterprise work using an already installed Studio profile."""
    request = _request(home, enterprise_id, plan, index)
    journal = enterprise._journal(home)
    studio_operator.operate(journal, "prepare", {"request": request})
    return show(home, enterprise_id, plan, index)


def _bound_record(journal: Journal, request: dict[str, Any]) -> dict[str, Any]:
    identity = digest("ascension-studio-request", request)
    record = studio_operator.show(journal, identity)
    if canonical(record["request"]) != canonical(request) or record["request_digest"] != identity:
        raise Conflict("Studio work differs from this exact enterprise and FusionPlan")
    return cast(dict[str, Any], record)


def show(home: Path, enterprise_id: str, plan: dict[str, Any], index: int) -> dict[str, Any]:
    """Read authoritative work and settlement separately; never infer payment."""
    request = _request(home, enterprise_id, plan, index)
    journal = enterprise._journal(home)
    record = _bound_record(journal, request)
    local = enterprise.show(home, enterprise_id)
    return {
        "schema": "successor-enterprise-ascension/v1",
        "enterprise_id": enterprise_id,
        "configuration_digest": local["configuration_digest"],
        "request_digest": record["request_digest"],
        "revision": record["revision"],
        "state": record["state"],
        "local_work_state": local["state"],
        "local_work_is_market_delivery": False,
        "chain_scope": record["market_context"]["scope"],
        "chain_id": record["market_context"]["chain_id"],
        "settlement": record.get("settlement"),
        "acceptance": record.get("local_acceptance"),
        "record": Journal.document(record),
        "authority_created": False,
        "transactions_sent": False,
    }


def advance(
    home: Path,
    enterprise_id: str,
    plan: dict[str, Any],
    index: int,
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Perform one explicit existing phase, retaining its revision and authority checks.

    The caller supplies the revision they reviewed, never an automatically refreshed
    revision. Signed grants/acceptance and actual receipt hashes are passed unchanged
    to the existing verifier. No on-chain transaction is broadcast by this facade.
    """
    if action not in ACTIONS:
        raise ValueError("Unsupported enterprise Ascension phase")
    if not isinstance(payload, dict) or "request_digest" in payload:
        raise ValueError("Supply phase fields, not a caller-selected request identity")
    request = _request(home, enterprise_id, plan, index)
    journal = enterprise._journal(home)
    record = _bound_record(journal, request)
    studio_operator.operate(journal, action, {**payload, "request_digest": record["request_digest"]})
    return show(home, enterprise_id, plan, index)


def main(argv: list[str] | None = None) -> int:
    """Provide an additive CLI without replacing the existing harness commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--enterprise-id", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--index", type=int, default=0)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("show")
    phase = sub.add_parser("advance")
    phase.add_argument("action", choices=ACTIONS)
    phase.add_argument("--payload", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = read_document(args.plan)
    if args.command == "advance":
        result = advance(args.home, args.enterprise_id, plan, args.index, args.action, read_document(args.payload))
    else:
        result = (prepare if args.command == "prepare" else show)(args.home, args.enterprise_id, plan, args.index)
    print(canonical(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
