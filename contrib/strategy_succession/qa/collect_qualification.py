# SPDX-License-Identifier: Apache-2.0
"""Collect exact installed acceptance into the existing release artifact handoff."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import subprocess
import tomllib
import zipfile

from defusedxml import ElementTree as SafeET

MAX_JUNIT_BYTES = 8 * 1024 * 1024


def _junit_bytes(path: Path) -> bytes:
    """Read one bounded regular report without traversing any symbolic link."""
    if ".." in path.parts or os.open not in os.supports_dir_fd or not getattr(os, "O_NOFOLLOW", 0):
        raise ValueError("Safe regular-file JUnit inspection is unavailable")
    absolute = path.absolute()
    directories = absolute.parts[1:-1]
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(absolute.anchor, directory_flags)
    try:
        for name in directories:
            child = os.open(name, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
        report_fd = os.open(absolute.name, flags, dir_fd=descriptor)
        with os.fdopen(report_fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_JUNIT_BYTES:
                raise ValueError("JUnit input must be a bounded nonempty regular file")
            raw = stream.read(MAX_JUNIT_BYTES + 1)
            after = os.fstat(stream.fileno())
            named = os.stat(absolute.name, dir_fd=descriptor, follow_symlinks=False)

            def identity(info: os.stat_result) -> tuple[int, int, int, int]:
                return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns

            if (
                len(raw) > MAX_JUNIT_BYTES
                or len(raw) != before.st_size
                or not stat.S_ISREG(named.st_mode)
                or identity(before) != identity(after)
                or identity(after) != identity(named)
            ):
                raise ValueError("JUnit input changed during bounded inspection")
            return raw
    except OSError:
        raise ValueError("JUnit input must have ordinary regular-file ancestry") from None
    finally:
        os.close(descriptor)


def verify_junit(path: Path) -> None:
    """Require actual passing cases and reject DTDs, entities and external references."""
    document = SafeET.fromstring(_junit_bytes(path), forbid_dtd=True, forbid_entities=True, forbid_external=True)
    if (
        document.tag not in {"testsuite", "testsuites"}
        or not list(document.iter("testcase"))
        or any(list(document.iter(tag)) for tag in ("failure", "error", "skipped"))
    ):
        raise ValueError("JUnit qualification requires nonempty cases with no failure, error or skip")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--first-wheel", type=Path, required=True)
    parser.add_argument("--second-wheel", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.absolute()
    project = root / "contrib/strategy_succession"
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    candidate = tomllib.loads((project / "pyproject.toml").read_text())["project"]["version"]
    assert args.first_wheel.read_bytes() == args.second_wheel.read_bytes(), "Two independently built wheels differ"
    from strategy_succession_engineering.serve import ROOT as installed
    import alpha_factory_v1

    assert not installed.resolve().is_relative_to(root)
    assert not Path(alpha_factory_v1.__file__).resolve().is_relative_to(root)
    assert importlib.metadata.version("agi-alpha-strategy-succession-engineering") == candidate
    assert importlib.metadata.version("alpha-factory-v1") == "1.42.0"
    # Bind the actual tested installed bodies to the built distribution.
    with zipfile.ZipFile(args.first_wheel) as wheel:
        payload = [n for n in wheel.namelist() if n.startswith("strategy_succession_engineering/")]
        assert payload
        for name in payload:
            relative = name.removeprefix("strategy_succession_engineering/")
            current = installed / relative
            assert not current.is_symlink() and current.read_bytes() == wheel.read(name), name
    # These are execution outputs, not substituted preexisting checked booleans.
    browser = json.loads((output / "acceptance-public/browser-acceptance.json").read_text())
    crash = json.loads((output / "acceptance-public/crash-recovery.json").read_text())
    integrated = json.loads((output / "acceptance-public/integrated-journey.json").read_text())
    assert browser["passed"] is True and crash["passed"] is True
    assert browser["source_hash"] == crash["source_hash"] == integrated["source_hash"]
    assert integrated["state"] == "completed" and integrated["outcome"]["verified"] is True
    dependency_audit = json.loads((output / "dependency-audit.json").read_text())
    assert (
        dependency_audit["passed"] is True
        and dependency_audit["packages"] == 25
        and dependency_audit["commit"] == commit
    )
    checks = {"dependency_audit": True}
    for name in ("transport", "worker", "environment", "integration", "browser", "crash_recovery"):
        verify_junit(output / (name + ".xml"))
        checks[name] = True
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    names = set(metadata["tool"]["setuptools"]["package-data"]["strategy_succession_engineering"]) | {
        "serve.py",
        "__init__.py",
        "setup.py",
        "pyproject.toml",
    }
    files = ["contrib/strategy_succession/" + name for name in sorted(names)]
    inventory = {
        "schema": "strategy-engineering-source-inventory/v1",
        "commit": commit,
        "version": version,
        "files": {name: {"sha256": sha(root / name), "bytes": (root / name).stat().st_size} for name in files if name},
    }
    inventory_path = output / "source-inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2) + "\n")
    copied = output / args.first_wheel.name
    copied.write_bytes(args.first_wheel.read_bytes())
    reproduced = output / "reproduced-wheel" / args.second_wheel.name
    reproduced.parent.mkdir(exist_ok=True)
    reproduced.write_bytes(args.second_wheel.read_bytes())
    profile = json.loads((installed / "ENGINEERING_MANIFEST.json").read_text())
    installed_summary = json.loads((output / "acceptance-public/integrated-summary.json").read_text())
    child_environment = installed_summary["child_environment"]
    assert child_environment["observation"]["dependencies"] == profile["qualified_environment"]["dependencies"]
    assert child_environment["observation"]["invocation_context_matches"] is True
    assert child_environment["observation"]["prefix_context_matches"] is True
    report = {
        "schema": "strategy-engineering-release-qualification/v1",
        "commit": commit,
        "version": version,
        "companion_version": candidate,
        "wheel": {"name": copied.name, "sha256": sha(copied), "bytes": copied.stat().st_size},
        "installed_outside_checkout": True,
        "source_inventory_sha256": sha(inventory_path),
        "runtime_version": "1.42.0",
        "runtime_wheel_sha256": profile["public_runtime_wheel_sha256"],
        "reproducible": True,
        "checks": checks,
        "source_hash": browser["source_hash"],
        "qualified_environment": profile["qualified_environment"],
        "child_environment": child_environment,
        "dependency_installation": "clean dedicated CI venv from exact qualification pins plus verified public Alpha wheel",
        "scope": "Automated browser/operator acceptance of bounded fixed planning methods; no production grant, held bridge, desktop or general computer-use qualification.",
        "costs_scope": "API journey only; browser and interruption exercise are separate attempts, not aggregate QA or lifecycle cost.",
        "costs": integrated["outcome"]["costs"],
        "separate_attempt_costs": {
            "api_journey": integrated["outcome"]["costs"],
            "browser_journey": json.loads((output / "acceptance-public/browser-mission-export.json").read_text())[
                "body"
            ]["plan"]["outcome"]["costs"],
            "crash_observed": crash["export"]["body"]["plan"]["observed"],
            "crash_reserved_unknown": crash["reserved_after"],
        },
        "total_qa_and_development_cost": "UNKNOWN; test execution and authoring are not represented as mission work units.",
        "human_and_monetary_cost": None,
        "operator_interventions": [
            "configure ephemeral test home",
            "configure exact finite profile",
            "browser exact approval",
            "close browser tab",
            "reconnect",
            "inspect/download",
            "Pause/Resume",
            "Stop",
            "separate SIGKILL/restart recovery exercise",
        ],
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
