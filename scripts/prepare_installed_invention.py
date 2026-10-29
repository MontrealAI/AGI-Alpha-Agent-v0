#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze reviewed source inputs, or bind a fresh installed layout to that freeze.

Neither mode constructs or executes an AST. Historical committed freezes remain
unchanged; --prepare-source writes a new exact-checkout freeze for qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

BACKEND = "alpha_factory_v1/core/runtime/invention_verification/"
GATE = "alpha_factory_v1/core/runtime/invention_automation/qualification.py"
BACKEND_FILES = {
    BACKEND + name
    for name in ("__init__.py", "critic_verify.py", "qualify_verify.py", "readonly.py", "dynamic_oracle.py")
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def selected_inputs(source: Path, args: argparse.Namespace, *, include_freeze: bool = True) -> dict[str, Path]:
    """Keep explicit source/installed input identities aligned; never silently default."""
    fixture = source / "evidence/invention-qualification-20261029"
    inputs = {}
    names = ("request", "program", "context", "freeze") if include_freeze else ("request", "program", "context")
    for name in names:
        path = getattr(args, name) or fixture / (name + ".json")
        if (
            any(parent.is_symlink() for parent in (path, *path.parents))
            or not path.is_file()
            or not path.resolve().is_relative_to(source)
        ):
            raise ValueError("qualification input must be a regular file inside the source checkout")
        if path.stat().st_size > 1_048_576:
            raise ValueError("qualification input exceeds byte bound")
        inputs[name] = path
    return inputs


def prepare_source(source: Path, output: Path, inputs: dict[str, Path]) -> None:
    """Register exact retained inputs and actual source bytes; never synthesize a candidate."""
    from alpha_factory_v1.core.runtime.invention_automation import critic_loop, evidence_critic
    from contrib.invention_automation.run_critic_pilot import PINNED_FILES, PROTOCOL

    if critic_loop.ROOT.resolve() != source:
        raise ValueError("source preparation imported a different checkout")
    values = {name: json.loads(path.read_bytes()) for name, path in inputs.items()}
    if digest(values["program"]) != digest(values["request"]["proposal"]):
        raise ValueError("program is not the retained proposal")
    evidence_critic.validate_context(values["request"], values["context"])
    names = (
        set(PINNED_FILES)
        | BACKEND_FILES
        | {
            GATE,
            "alpha_factory_v1/core/runtime/cli.py",
            "alpha_factory_v1/core/runtime/invention_automation/__init__.py",
            "alpha_factory_v1/core/runtime/invention_automation/operator.py",
            "alpha_factory_v1/core/runtime/structural_transfer/__init__.py",
            "scripts/prepare_installed_invention.py",
            "scripts/validate_invention_sandbox.py",
            "tests/test_invention_sandbox_qualification.py",
            "tests/test_invention_install_qualification.py",
            ".github/workflows/invention-dynamic.yml",
            ".github/workflows/invention-qualification.yml",
        }
    )
    pins = {}
    for name in sorted(names):
        path = source / name
        if (
            not path.is_file()
            or any(parent.is_symlink() for parent in (path, *path.parents))
            or not path.resolve().is_relative_to(source)
        ):
            raise ValueError("required regular source asset absent: " + name)
        pins[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if PROTOCOL not in pins:
        raise ValueError("actual protocol must be frozen")
    freeze = {
        "schema": "agialpha/critic-verifier-freeze/v1",
        "files": pins,
        "protocol_path": PROTOCOL,
        "protocol_sha256": pins[PROTOCOL],
        "request_hashes": [digest(values["request"])],
        "context_hashes": [digest(values["context"])],
    }
    output.mkdir(parents=False, exist_ok=False)
    for name, path in inputs.items():
        shutil.copyfile(path, output / (name + ".json"))
    (output / "freeze.json").write_text(json.dumps(freeze, sort_keys=True, indent=2) + "\n")
    report = {
        "schema": "agialpha/retained-source-layout/v2",
        "input_file_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in inputs.items()},
        "registered_input_hashes": {name: digest(value) for name, value in values.items()},
        "freeze_file_sha256": hashlib.sha256((output / "freeze.json").read_bytes()).hexdigest(),
        "source_files": pins,
        "generated_program_executed": False,
        "new_candidate_constructed": False,
        "scope": "new exact-source freeze for retained software qualification; historical freezes unchanged",
    }
    (output / "source-layout.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")


def prepare_installed(source: Path, output: Path, inputs: dict[str, Path]) -> None:
    """Match actual installed modules and derive a distinct installed-layout freeze."""
    from alpha_factory_v1.core.runtime.invention_automation import critic_loop, qualification
    from alpha_factory_v1.core.runtime.invention_verification import (
        critic_verify,
        dynamic_oracle,
        qualify_verify,
        readonly,
    )

    root = critic_loop.ROOT.resolve()
    if root.is_relative_to(source) or not root.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("runtime did not resolve inside the selected fresh installation")
    modules = {
        critic_loop: "alpha_factory_v1/core/runtime/invention_automation/critic_loop.py",
        qualification: GATE,
        critic_verify: BACKEND + "critic_verify.py",
        qualify_verify: BACKEND + "qualify_verify.py",
        readonly: BACKEND + "readonly.py",
        dynamic_oracle: BACKEND + "dynamic_oracle.py",
    }
    for module, name in modules.items():
        module_path = module.__file__
        expected = root / name
        if (
            module_path is None
            or expected.is_symlink()
            or not expected.is_file()
            or Path(module_path).resolve() != expected.resolve()
        ):
            raise ValueError("mixed source and installed module origins")
    freeze = json.loads(inputs["freeze"].read_bytes())
    if freeze.get("schema") != "agialpha/critic-verifier-freeze/v1":
        raise ValueError("source freeze schema")
    required = BACKEND_FILES | {GATE, *modules.values()}
    if not required <= set(freeze["files"]):
        raise ValueError("actual installed gate and canonical verifier assets must be source-frozen")
    pins, omitted = {}, {}
    for name, expected in freeze["files"].items():
        if name.startswith(("alpha_factory_v1/", "contrib/invention_automation/")):
            path = root / name
            if (
                not path.is_file()
                or any(parent.is_symlink() for parent in (path, *path.parents))
                or not path.resolve().is_relative_to(root)
            ):
                raise ValueError("installed source path escaped its package root")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("installed bytes differ from reviewed source: " + name)
            pins[name] = expected
        else:
            omitted[name] = expected
    output.mkdir(parents=False, exist_ok=False)
    for name in ("request", "program", "context"):
        shutil.copyfile(inputs[name], output / (name + ".json"))
    installed = {**freeze, "files": pins}
    (output / "freeze.json").write_text(json.dumps(installed, sort_keys=True, indent=2) + "\n")
    report = {
        "schema": "agialpha/installed-invention-layout/v2",
        "installed_root": str(root),
        "python": sys.executable,
        "source_freeze_sha256": hashlib.sha256(inputs["freeze"].read_bytes()).hexdigest(),
        "installed_freeze_sha256": hashlib.sha256((output / "freeze.json").read_bytes()).hexdigest(),
        "matched_installed_files": pins,
        "omitted_repository_only_pins": omitted,
        "generated_program_executed": False,
        "scope": "installed byte/layout verification only; dynamic qualification remains separate",
    }
    (output / "installation.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-source", action="store_true")
    for name in ("request", "program", "context", "freeze"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    source = args.source_root.resolve()
    if args.prepare_source:
        if args.freeze is not None:
            raise ValueError("source preparation writes a new freeze; historical freeze input is not accepted")
        inputs = selected_inputs(source, args, include_freeze=False)
        prepare_source(source, args.output, inputs)
    else:
        if Path.cwd().resolve().is_relative_to(source):
            raise ValueError("installed qualification must run outside the source checkout")
        inputs = selected_inputs(source, args)
        prepare_installed(source, args.output, inputs)
    print(json.dumps({"output": str(args.output), "generated_program_executed": False}))


if __name__ == "__main__":
    main()
