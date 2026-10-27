#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fixed-shape confidential reserve feasibility, MPyC 0.11, three local parties.

Launch THREE independently supervised copies with -M3 -I0/-I1/-I2 -T1.
Required application arguments: --manifest PUBLIC.json --private-dir DIRECTORY.
Optional --vendor-dir defaults to ../vendor/mpyc_0_11; -B controls local ports.

Public manifest schema (canonical JSON hashing uses sorted keys and compact
separators, UTF-8): schema="reserve-mpc-v1", parties=3, assets_per_party=2,
demands=6, max_claims=2 or 3, scope_id=str, scenario_epoch=str, world_count=N,
scenarios=[{"id": str, "demand_clients": [int,...]}],
input_commitments=[SHA256(raw party_0.json), ..., SHA256(raw party_2.json)].
Scenarios must be the complete singleton/pair family, optionally all triples.

Owner file party_PID.json: schema, party_id, nonce (64 hexadecimal characters),
worlds=[{"eligibility": 2x6 bits, "availability": 2xS bits,
         "retention": 2xS bits}, ...], S=21 or 41. Retention=1 means WITHHELD, so an asset
is usable in a scenario iff availability=1 and retention=0. Unused padded rows
must have zero eligibility/availability. A fresh secret nonce prevents simple
dictionary testing of a public commitment in a real separate-party deployment.

Each worker reads its own owner file only. The public supervisor can possess all
toy files for reproducibility; this is not independent-host isolation. Local
validation/commitment checking assumes honest protocol behavior. There is no
proof of physical inventory, truthful eligibility, or exclusive ownership.

For each public scenario and every nonempty subset of its demand clients, count
usable neighboring assets privately, test count >= subset size, and AND every
test. Hall's criterion is necessary and sufficient for an injective assignment.
No matching, edge, count, or per-scenario verdict is opened. This says forall
declared scenarios exists an assignment, not one fixed assignment for all.

Exactly one final bit per world is opened to all three parties in one batched
mpc.output call. Party 0 prints those bits and two public hashes. Stderr contains
only public execution telemetry. Loopback byte counters count application TCP
stream bytes, including MPyC framing/initial messages, excluding TCP/IP headers.

Security: established MPyC passive Shamir model, m=3, t=1 (<m/2). This local
fixture uses plaintext loopback and provides no remote authenticated channels,
malicious-party security, observer certification, or production security audit.
"""

import argparse
import asyncio
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import time
from collections.abc import Iterable
from typing import Any, cast


def canonical(value: object) -> bytes:
    """Encode public hash inputs deterministically."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""
    return hashlib.sha256(data).hexdigest()


def parse_application_args() -> argparse.Namespace:
    """Parse worker paths while preserving MPyC's runtime arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--vendor-dir", type=Path, default=Path(__file__).resolve().parents[1] / "vendor/mpyc_0_11")
    args, runtime_args = parser.parse_known_args()
    # Prevent MPyC's implicit child spawning: the supervisor must start each PID.
    if not any(a == "-I" or a.startswith("-I") or a == "--index" or a.startswith("--index=") for a in runtime_args):
        parser.error("Start each worker explicitly with -I0, -I1, or -I2")
    for flag in ("--no-log", "--no-numpy", "--no-gmpy2", "--no-uvloop"):
        if flag not in runtime_args:
            runtime_args.append(flag)
    sys.argv = [sys.argv[0]] + runtime_args
    return args


ARGS = parse_application_args()
sys.path.insert(0, str(ARGS.vendor_dir.resolve()))
import mpyc  # noqa: E402
from mpyc.runtime import mpc  # noqa: E402
from mpyc import asyncoro  # noqa: E402

if mpyc.__version__ != "0.11":
    raise RuntimeError("This staged probe pins MPyC 0.11")
if len(mpc.parties) != 3 or mpc.threshold != 1:
    raise RuntimeError("Exactly three parties and passive threshold one are required")
if mpc.options.ssl:
    raise RuntimeError("This fixture uses loopback only; SSL deployment is not configured")

TELEMETRY: dict[str, Any] = {
    "bytes_sent": 0,
    "bytes_received": 0,
    "connections": 0,
    "peer_addresses": set(),
    "private_files_opened": [],
}


class CountingTransport:
    """Count byte lengths without retaining or disclosing message contents."""

    def __init__(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def write(self, data: bytes) -> None:
        TELEMETRY["bytes_sent"] += len(data)
        self.transport.write(data)

    def writelines(self, lines: Iterable[bytes]) -> None:
        lines = tuple(lines)
        TELEMETRY["bytes_sent"] += sum(map(len, lines))
        self.transport.writelines(lines)

    def __getattr__(self, key: str) -> Any:
        return getattr(self.transport, key)


_connection_made = asyncoro.MessageExchanger.connection_made
_data_received = asyncoro.MessageExchanger.data_received


def counted_connection(self: Any, transport: asyncio.Transport) -> None:
    """Count a connection and enforce its loopback peer address."""
    address = transport.get_extra_info("peername")
    if not address or address[0] != "127.0.0.1":
        transport.close()
        raise RuntimeError("Only IPv4 loopback peers are permitted")
    TELEMETRY["connections"] += 1
    TELEMETRY["peer_addresses"].add(address[0])
    _connection_made(self, CountingTransport(transport))


def counted_received(self: Any, data: bytes) -> None:
    """Count received bytes without retaining their contents."""
    TELEMETRY["bytes_received"] += len(data)
    _data_received(self, data)


asyncoro.MessageExchanger.connection_made = counted_connection
asyncoro.MessageExchanger.data_received = counted_received
for party in mpc.parties:
    if party.host not in ("localhost", "127.0.0.1", "::1"):
        raise RuntimeError("Remote parties are not permitted in this fixture")
    party.host = "127.0.0.1"
_create_server = mpc._loop.create_server


async def loopback_server(*args: Any, **kwargs: Any) -> asyncio.AbstractServer:
    """Restrict MPyC's default listener to the IPv4 loopback interface."""
    if kwargs.get("host") not in (None, "localhost", "127.0.0.1"):
        raise RuntimeError("Non-loopback listening is forbidden")
    kwargs["host"] = "127.0.0.1"
    return cast(asyncio.AbstractServer, await _create_server(*args, **kwargs))


mpc._loop.create_server = loopback_server


def require(condition: bool, message: str) -> None:
    """Reject invalid input with a value-free diagnostic."""
    if not condition:
        raise ValueError(message)


def bits_matrix(value: Any, rows: int, columns: int) -> None:
    """Require an exact matrix shape containing integer zero/one values."""
    require(isinstance(value, list) and len(value) == rows, "Invalid padded row count")
    for row in value:
        require(isinstance(row, list) and len(row) == columns, "Invalid padded column count")
        require(all(type(bit) is int and bit in (0, 1) for bit in row), "Inputs must be bits")


def load_inputs() -> tuple[dict[str, Any], list[tuple[int, ...]], list[int], str, str]:
    """Read public metadata and only this process's committed private file."""
    public_path = ARGS.manifest.resolve()
    private_root = ARGS.private_dir.resolve()
    owner_path = private_root / f"party_{mpc.pid}.json"

    def owner_file_guard(event: str, audit_args: tuple[Any, ...]) -> None:
        if event != "open" or not isinstance(audit_args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(audit_args[0])).resolve()
        if path.parent == private_root and path.name.startswith("party_"):
            require(path == owner_path, "Worker attempted to open another owner's input")
            TELEMETRY["private_files_opened"].append(path.name)

    sys.addaudithook(owner_file_guard)
    manifest: dict[str, Any] = json.loads(public_path.read_bytes())
    require(
        isinstance(manifest, dict)
        and set(manifest)
        == {
            "schema",
            "parties",
            "assets_per_party",
            "demands",
            "max_claims",
            "scope_id",
            "scenario_epoch",
            "world_count",
            "scenarios",
            "input_commitments",
        },
        "Wrong manifest fields",
    )
    require(manifest.get("schema") == "reserve-mpc-v1", "Wrong manifest schema")
    for key, expected in (("parties", 3), ("assets_per_party", 2), ("demands", 6)):
        require(type(manifest.get(key)) is int and manifest[key] == expected, "Wrong public padded dimensions")
    n = manifest["world_count"]
    require(type(n) is int and 1 <= n <= 1000, "Invalid public world count")
    max_claims = manifest["max_claims"]
    require(type(max_claims) is int and max_claims in (2, 3), "max_claims must be 2 or 3")
    scenario_count = 21 if max_claims == 2 else 41
    for key in ("scope_id", "scenario_epoch"):
        require(
            isinstance(manifest.get(key), str) and 1 <= len(manifest[key]) <= 128,
            "Missing or invalid public scope/epoch",
        )
    scenarios = manifest["scenarios"]
    require(isinstance(scenarios, list) and len(scenarios) == scenario_count, "Wrong public scenario count")
    groups: list[tuple[int, ...]] = []
    ids: list[str] = []
    for scenario in scenarios:
        require(
            isinstance(scenario, dict) and set(scenario) == {"id", "demand_clients"}, "Wrong public scenario fields"
        )
        group = scenario.get("demand_clients")
        require(isinstance(group, list) and 1 <= len(group) <= max_claims, "Wrong public claim count")
        require(all(type(d) is int and 0 <= d < 6 for d in group), "Invalid public demand")
        require(group == sorted(set(group)), "Demand clients must be sorted and unique")
        require(isinstance(scenario.get("id"), str), "Scenario needs public ID")
        groups.append(tuple(group))
        ids.append(scenario["id"])
    expected_groups = {group for size in range(1, max_claims + 1) for group in itertools.combinations(range(6), size)}
    require(set(groups) == expected_groups and len(set(ids)) == scenario_count, "Scenario family incomplete")
    commitments = manifest["input_commitments"]
    require(isinstance(commitments, list) and len(commitments) == 3, "Three commitments required")
    require(
        all(isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h) for h in commitments),
        "Commitments must be lowercase SHA-256 hex",
    )
    raw = owner_path.read_bytes()
    require(sha256(raw) == commitments[mpc.pid], "Owner-file commitment mismatch")
    owner = json.loads(raw)
    require(isinstance(owner, dict) and set(owner) == {"schema", "party_id", "nonce", "worlds"}, "Wrong owner fields")
    require(
        owner.get("schema") == "reserve-mpc-v1" and type(owner.get("party_id")) is int and owner["party_id"] == mpc.pid,
        "Wrong owner schema or party ID",
    )
    nonce = owner.get("nonce")
    require(
        isinstance(nonce, str) and len(nonce) == 64 and all(c in "0123456789abcdef" for c in nonce),
        "A 256-bit nonce is required",
    )
    worlds = owner.get("worlds")
    require(isinstance(worlds, list) and len(worlds) == n, "World count mismatch")
    flat: list[int] = []
    for world in worlds:
        require(
            isinstance(world, dict) and set(world) == {"eligibility", "availability", "retention"},
            "Wrong private world fields",
        )
        for key, width in (("eligibility", 6), ("availability", scenario_count), ("retention", scenario_count)):
            bits_matrix(world.get(key), 2, width)
        # World, then row, then eligibility/availability/retention.
        for row in range(2):
            flat.extend(world["eligibility"][row])
            flat.extend(world["availability"][row])
            flat.extend(world["retention"][row])
    public_contract = {
        key: manifest[key]
        for key in (
            "schema",
            "parties",
            "assets_per_party",
            "demands",
            "max_claims",
            "scope_id",
            "scenario_epoch",
            "scenarios",
        )
    }
    scenario_hash = sha256(canonical(public_contract))
    commitment_hash = sha256(
        canonical({"public_scenario_sha256": scenario_hash, "world_count": n, "input_commitments": commitments})
    )
    return manifest, groups, flat, scenario_hash, commitment_hash


async def main() -> None:
    """Evaluate all public Hall conditions and open only each world's conjunction."""
    started = time.perf_counter()
    manifest, scenarios, local_bits, scenario_hash, commitment_hash = load_inputs()
    await mpc.start()
    connected = time.perf_counter()
    public_agreement = await mpc.transfer((scenario_hash, commitment_hash, manifest["world_count"]))
    require(len(set(public_agreement)) == 1, "Parties disagree on public manifest")
    secint = mpc.SecInt(8)  # Counts range 0..6, thresholds 1..3.
    shared = mpc.input([secint(bit) for bit in local_bits])
    verdicts = []
    scenario_count = len(scenarios)
    max_claims = manifest["max_claims"]
    condition_count = sum(2 ** len(group) - 1 for group in scenarios)
    row_width = 6 + 2 * scenario_count
    world_width = 2 * row_width
    for world_index in range(manifest["world_count"]):
        assets = []
        for party in range(3):
            for row in range(2):
                start = world_index * world_width + row * row_width
                values = shared[party][start : start + row_width]
                assets.append((values[:6], values[6 : 6 + scenario_count], values[6 + scenario_count : row_width]))
        # Precompute eligibility unions; all loops depend only on public shape.
        unions = {}
        for size in range(1, max_claims + 1):
            for subset in itertools.combinations(range(6), size):
                unions[subset] = [1 - mpc.prod([1 - eligibility[d] for d in subset]) for eligibility, _, _ in assets]
        conditions = []
        for scenario_index, demand_group in enumerate(scenarios):
            usable = [
                availability[scenario_index] * (1 - retention[scenario_index]) for _, availability, retention in assets
            ]
            for size in range(1, len(demand_group) + 1):
                for subset in itertools.combinations(demand_group, size):
                    count = mpc.in_prod(usable, unions[subset])
                    conditions.append(count >= size)
        require(len(conditions) == condition_count, "Unexpected public Hall circuit shape")
        verdict = mpc.all(conditions)
        verdicts.append(verdict)
        # Resolve pending work without opening a value. Bounds batch memory.
        await mpc.gather(verdict)
    bits = await mpc.output(verdicts)
    computed = time.perf_counter()
    require(all(bit in (0, 1) for bit in bits), "Non-bit aggregate output")
    if mpc.pid == 0:
        print(
            json.dumps(
                {
                    "all_scenarios_sufficient": bits,
                    "public_scenario_sha256": scenario_hash,
                    "input_commitment_sha256": commitment_hash,
                },
                sort_keys=True,
            ),
            flush=True,
        )
    await mpc.shutdown()
    finished = time.perf_counter()
    telemetry = {
        "event": "mpc_worker_telemetry",
        "party_id": mpc.pid,
        "process_id": os.getpid(),
        "mpyc_version": mpyc.__version__,
        "threshold": mpc.threshold,
        "parties": len(mpc.parties),
        "sec_param": mpc.options.sec_param,
        "secure_integer_bits": 8,
        "world_count": manifest["world_count"],
        "private_input_bits_per_party": len(local_bits),
        "hall_conditions_per_world": condition_count,
        "elapsed_seconds": finished - started,
        "startup_seconds": connected - started,
        "compute_seconds": computed - connected,
        "bytes_sent": TELEMETRY["bytes_sent"],
        "bytes_received": TELEMETRY["bytes_received"],
        "connections": TELEMETRY["connections"],
        "peer_addresses": sorted(TELEMETRY["peer_addresses"]),
        "private_files_opened": TELEMETRY["private_files_opened"],
        "output_bits_opened": len(bits),
        "status": "ok",
    }
    print(json.dumps(telemetry, sort_keys=True), file=sys.stderr, flush=True)


if __name__ == "__main__":
    try:
        mpc.run(main())
    except Exception as exc:
        # Do not echo secret values or offending private-file contents.
        print(
            json.dumps(
                {
                    "event": "mpc_worker_error",
                    "party_id": mpc.pid,
                    "process_id": os.getpid(),
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            ),
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
