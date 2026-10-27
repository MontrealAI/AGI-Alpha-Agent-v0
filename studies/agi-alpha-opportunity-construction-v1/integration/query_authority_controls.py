# SPDX-License-Identifier: Apache-2.0
"""Exercise real native grant boundaries on the study's public mission manifests."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from query_authority import (
    DOMAIN,
    HERE,
    MODE,
    PRINCIPAL,
    FixtureQueryAuthority,
    bind_query,
    consume_grant,
    digest,
    native_modules,
    read_json,
    verify_grant,
)


def run_authority_controls(
    origin_manifest: Path, successor_manifest: Path, worker: Path, output: Path
) -> dict[str, Any]:
    """Preserve scope/epoch/replay refusals; these controls do not execute MPC."""
    origin_manifest, successor_manifest, worker = (
        Path(item).resolve() for item in (origin_manifest, successor_manifest, worker)
    )
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing to overwrite an authority-control evidence directory")
    output.mkdir(parents=True)
    checks: list[dict[str, Any]] = []
    now = int(time.time())

    def expect(name: str, operation: Callable[[], Any], *, refused: bool) -> Any:
        try:
            value = operation()
        except (ValueError, KeyError, AssertionError) as error:
            checks.append({"name": name, "passed": refused, "observed": "refused", "reason": str(error)})
            return None
        checks.append({"name": name, "passed": not refused, "observed": "accepted"})
        return value

    def save(path: Path, value: Any) -> None:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")

    with tempfile.TemporaryDirectory(prefix="reserve-query-controls-") as directory:
        temporary = Path(directory)
        authority = FixtureQueryAuthority(temporary / "origin-journal")
        origin_binding = bind_query(origin_manifest, worker)
        successor_binding = bind_query(successor_manifest, worker)
        if origin_binding["scenario_count"] != 21 or successor_binding["scenario_count"] != 41:
            raise ValueError("Controls require the real 21-scenario origin and 41-scenario successor manifests")
        grant = authority.issue(origin_binding, now=now)
        expect(
            "Current origin grant is consumed before execution",
            lambda: authority.consume(grant, origin_manifest, worker, now=now),
            refused=False,
        )
        expect(
            "Exact grant replay is refused",
            lambda: authority.consume(grant, origin_manifest, worker, now=now),
            refused=True,
        )
        expect(
            "A second nonce cannot reopen the same scope and epoch",
            lambda: authority.consume(authority.issue(origin_binding, now=now), origin_manifest, worker, now=now),
            refused=True,
        )

        grant_path, context_path = temporary / "grant.json", temporary / "context.json"
        save(grant_path, grant)
        save(context_path, authority.context)
        process = subprocess.run(
            [
                sys.executable,
                str(HERE / "query_authority.py"),
                "--grant",
                str(grant_path),
                "--context",
                str(context_path),
                "--manifest",
                str(origin_manifest),
                "--worker",
                str(worker),
                "--journal",
                str(authority.journal_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        decoded = json.loads(process.stdout)
        checks.append(
            {
                "name": "Fresh consumer process refuses the retained replay",
                "passed": process.returncode == 1
                and decoded.get("accepted") is False
                and "already consumed" in decoded.get("error", ""),
                "observed": decoded,
            }
        )

        for field, replacement in (
            ("scope_id", origin_binding["scope_id"] + "-changed"),
            ("scenario_epoch", origin_binding["scenario_epoch"] + "-changed"),
            ("world_count", origin_binding["world_count"] + 1),
        ):
            altered = copy.deepcopy(origin_binding)
            altered[field] = replacement
            expect(
                "Old grant refuses changed " + field,
                lambda: verify_grant(grant, authority.context, altered, now),
                refused=True,
            )
        altered = copy.deepcopy(origin_binding)
        altered["input_commitments"][0] = "0" * 64 if altered["input_commitments"][0] != "0" * 64 else "1" * 64
        expect(
            "Old grant refuses changed owner input commitment",
            lambda: verify_grant(grant, authority.context, altered, now),
            refused=True,
        )
        altered_worker = temporary / "changed-worker.py"
        altered_worker.write_bytes(worker.read_bytes() + b"\n# Changed executable bytes for refusal control only.\n")
        expect(
            "Old grant refuses changed worker bytes",
            lambda: verify_grant(grant, authority.context, bind_query(origin_manifest, altered_worker), now),
            refused=True,
        )
        expect(
            "Origin grant cannot authorize the larger successor mission",
            lambda: verify_grant(grant, authority.context, successor_binding, now),
            refused=True,
        )
        expect(
            "Expired authority is refused",
            lambda: verify_grant(grant, authority.context, origin_binding, now + 3601),
            refused=True,
        )
        expect(
            "Authority is refused before its validity interval",
            lambda: verify_grant(grant, authority.context, origin_binding, now - 10),
            refused=True,
        )
        revoked_context = {**authority.context, "revoked": [PRINCIPAL]}
        expect(
            "Revoked controller is refused",
            lambda: verify_grant(grant, revoked_context, origin_binding, now),
            refused=True,
        )
        tampered = copy.deepcopy(grant)
        tampered["payload"]["nonce"] += "-altered"
        expect(
            "Changed signed payload is refused",
            lambda: verify_grant(tampered, authority.context, origin_binding, now),
            refused=True,
        )
        trust, _ = native_modules()
        validator_only = trust.TrustRegistry(
            {PRINCIPAL: trust.TrustAnchor(authority.context["public_key"], frozenset({"validator"}))}
        )
        expect(
            "Validator-only role does not become query controller",
            lambda: validator_only.verify(trust.SignedEnvelope.model_validate(grant), DOMAIN, "controller"),
            refused=True,
        )
        other = FixtureQueryAuthority(temporary / "other-journal")
        expect(
            "Grant cannot be replayed through a different fresh journal",
            lambda: consume_grant(grant, authority.context, origin_manifest, worker, other.journal_dir, now=now),
            refused=True,
        )
        replaced_key = {**authority.context, "public_key": other.context["public_key"]}
        expect(
            "Another signer is not trusted by imported evidence",
            lambda: verify_grant(grant, replaced_key, origin_binding, now),
            refused=True,
        )
        incomplete, _ = read_json(origin_manifest)
        incomplete["scenarios"] = incomplete["scenarios"][:-1]
        incomplete_path = temporary / "incomplete-manifest.json"
        save(incomplete_path, incomplete)
        expect(
            "Omitting a difficult scenario fails the authority binding",
            lambda: bind_query(incomplete_path, worker),
            refused=True,
        )

        successor_grant = authority.issue(successor_binding, now=now)
        successor_consumption = expect(
            "Fresh explicit successor grant is accepted for all 41 scenarios",
            lambda: authority.consume(successor_grant, successor_manifest, worker, now=now),
            refused=False,
        )
        expect(
            "Successor grant also remains one-use",
            lambda: authority.consume(successor_grant, successor_manifest, worker, now=now),
            refused=True,
        )
        save(output / "origin-grant.json", grant)
        save(output / "successor-grant.json", successor_grant)
        save(output / "successor-consumption.json", successor_consumption)
        save(output / "public-native-journal.json", authority.public_receipt())

        racing = FixtureQueryAuthority(temporary / "race-journal")
        racing_grant = racing.issue(origin_binding, now=now)

        def race_once(_: int) -> str:
            try:
                racing.consume(racing_grant, origin_manifest, worker, now=now)
                return "accepted"
            except ValueError as error:
                return "refused: " + str(error)

        with ThreadPoolExecutor(max_workers=2) as executor:
            race_results = list(executor.map(race_once, range(2)))
        checks.append(
            {
                "name": "Atomic Journal consumption admits exactly one concurrent caller",
                "passed": race_results.count("accepted") == 1
                and sum("already consumed" in item for item in race_results) == 1,
                "observed": race_results,
            }
        )
        save(output / "concurrent-public-journal.json", racing.public_receipt())
    result = {
        "schema": "agialpha.reserve-query.authority-controls.v1",
        "mode": MODE,
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "origin_binding": origin_binding,
        "successor_binding": successor_binding,
        "checks": checks,
        "worker_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
        "helper_sha256": hashlib.sha256((HERE / "query_authority.py").read_bytes()).hexdigest(),
        "controls_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Actual native signature, role, schema and transactional replay controls over public study manifests. No MPC work or commercial outcome is counted here.",
        "binding_sha256": {"origin": digest(origin_binding), "successor": digest(successor_binding)},
        "private_owner_files_read": 0,
        "private_keys_exported": False,
        "current_authority": "Simulated local identities; no live ENS, organizational independence or production authorization.",
        "state_limit": "The retained local journal is trusted. Host compromise or rollback of all state is outside this fixture.",
    }
    save(output / "controls.json", result)
    if result["status"] != "passed":
        raise AssertionError("An authority control failed; the preserved evidence includes its outcome")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("origin", "successor", "worker", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    arguments = parser.parse_args()
    result = run_authority_controls(arguments.origin, arguments.successor, arguments.worker, arguments.output)
    print(json.dumps({"status": result["status"], "scope": result["scope"]}))
