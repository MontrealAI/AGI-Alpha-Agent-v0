# SPDX-License-Identifier: Apache-2.0
"""Installed Alpha commands for inspectable claim falsification."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .checker import check
from .contracts import TASK_SCHEMA, read, write_new
from .instrument import probe


def example() -> dict[str, Any]:
    """A finite-test-passing quadratic with a genuine continuum violation."""
    return {
        "schema": TASK_SCHEMA,
        "id": "finite-tests-do-not-prove-continuum",
        "coefficients": ["624/10000", "-1/2", "1"],
        "domain": ["0", "1"],
        "claim": "nonnegative-throughout-domain",
        "scope": "declared-mathematical-model-only",
        "sources": [
            "https://www.nist.gov/publications/abstracting-formal-specifications-generate-software-tests-model-checking"
        ],
        "limits": {"cells": 1024, "depth": 20, "seconds": 5},
    }


def add_commands(commands: Any) -> None:
    """Add a bounded native route without changing existing commands."""
    root = commands.add_parser("claim-probe", help="Find a counterexample or exact bound for a declared model claim")
    sub = root.add_subparsers(dest="probe_action", required=True)
    for action in ["run", "check", "example", "joint"]:
        parser = sub.add_parser(action)
        if action != "example":
            parser.add_argument("file", type=Path)
        if action == "check":
            parser.add_argument("--result", type=Path, required=True)
        else:
            parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--language", choices=["en", "fr"], default="en")
        if action == "run":
            parser.add_argument("--method", choices=["library", "bernstein"], default="library")


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Exercise the exact installed input, constructor and independent checker."""
    labels = {
        "en": "Exact mathematical model only; physical application is unqualified.",
        "fr": "Modèle mathématique exact seulement; application physique non qualifiée.",
    }
    if args.probe_action == "example":
        task = example()
        write_new(args.output, task)
        return {"task": str(args.output), "scope": labels[args.language]}
    if args.probe_action == "joint":
        from .joint import construct_and_check

        result = construct_and_check(read(args.file))
        write_new(args.output, result)
        return result
    task = read(args.file)
    if args.probe_action == "check":
        return {**check(task, read(args.result)), "scopeMessage": labels[args.language]}
    if args.method == "library":
        from .symbolic import ordinary_library

        result = ordinary_library(task)
    else:
        result = probe(task)
    verification = check(task, result)
    if not verification["accepted"]:
        raise ValueError("constructor output failed independent check")
    write_new(args.output, result)
    return {
        "output": str(args.output),
        "status": result["status"],
        "verification": verification,
        "scope": labels[args.language],
        "physicalQualified": False,
    }
