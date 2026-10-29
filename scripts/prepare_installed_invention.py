#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind installed bytes to a reviewed source freeze without executing any AST.

Run with the fresh installation's Python from outside the checkout and with an
empty PYTHONPATH. Repository-only pins are explicitly omitted from the new
installed-layout freeze, never rewritten in the original source freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


def selected_inputs(source: Path, args: argparse.Namespace) -> dict[str, Path]:
    """Keep explicit source/installed input identities aligned; never silently default."""
    fixture = source / "evidence/invention-qualification-20261029"
    inputs = {}
    for name in ("request", "program", "context", "freeze"):
        path = getattr(args, name) or fixture / (name + ".json")
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(source):
            raise ValueError("qualification input must be a regular file inside the source checkout")
        inputs[name] = path
    return inputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for name in ("request", "program", "context", "freeze"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    source = args.source_root.resolve()
    if Path.cwd().resolve().is_relative_to(source):
        raise ValueError("installed qualification must run outside the source checkout")
    from alpha_factory_v1.core.runtime.invention_automation import critic_loop, qualification
    from contrib.invention_automation import critic_verify

    root = critic_loop.ROOT
    if root.is_relative_to(source) or not root.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("runtime did not resolve inside the selected fresh installation")
    for module in (critic_loop, qualification, critic_verify):
        module_path = module.__file__
        if module_path is None or not Path(module_path).resolve().is_relative_to(root):
            raise ValueError("mixed source and installed module origins")
    inputs = selected_inputs(source, args)
    freeze = json.loads(inputs["freeze"].read_text())
    pins, omitted = {}, {}
    for name, expected in freeze["files"].items():
        if name.startswith(("alpha_factory_v1/", "contrib/invention_automation/")):
            path = root / name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("installed source path escaped its package root")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("installed bytes differ from reviewed source: " + name)
            pins[name] = expected
        else:
            omitted[name] = expected
    required_installed_gate = "alpha_factory_v1/core/runtime/invention_automation/qualification.py"
    if required_installed_gate not in pins:
        raise ValueError("installed qualification gate must be bound by the supplied source freeze")
    args.output.mkdir(parents=False, exist_ok=False)
    for name in ("request", "program", "context"):
        shutil.copyfile(inputs[name], args.output / (name + ".json"))
    installed = {**freeze, "files": pins}
    (args.output / "freeze.json").write_text(json.dumps(installed, sort_keys=True, indent=2) + "\n")
    report = {
        "schema": "agialpha/installed-invention-layout/v1",
        "installed_root": str(root),
        "python": sys.executable,
        "source_freeze_sha256": hashlib.sha256(inputs["freeze"].read_bytes()).hexdigest(),
        "installed_freeze_sha256": hashlib.sha256((args.output / "freeze.json").read_bytes()).hexdigest(),
        "matched_installed_files": pins,
        "omitted_repository_only_pins": omitted,
        "generated_program_executed": False,
        "scope": "installed byte/layout verification only; dynamic qualification remains separate",
    }
    (args.output / "installation.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"installed_files_matched": len(pins), "output": str(args.output)}))


if __name__ == "__main__":
    main()
