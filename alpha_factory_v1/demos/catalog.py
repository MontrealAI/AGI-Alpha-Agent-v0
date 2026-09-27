# SPDX-License-Identifier: Apache-2.0
"""One catalog for demo launch instructions, gallery descriptions and validation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any

from alpha_factory_v1.utils.disclaimer import print_disclaimer

CATALOG = Path(__file__).with_name("catalog.json")
REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
DEMOS_ROOT = CATALOG.parent


def resolve_setting(value: str, entry: dict[str, Any], output: Path) -> str:
    """Resolve catalog-owned paths for source checkouts and installed wheels."""
    return (
        value.replace("{output}", str(output.resolve()))
        .replace("{demo}", str(DEMOS_ROOT / entry["id"]))
        .replace("{demos}", str(DEMOS_ROOT))
    )


def entries() -> list[dict[str, Any]]:
    """Load the reviewed demo inventory without importing optional backends."""
    return json.loads(CATALOG.read_text(encoding="utf-8"))["entries"]  # type: ignore[no-any-return]


def command_for(entry: dict[str, Any], output: Path) -> list[str]:
    """Resolve a fixed argument vector; no shell or user-supplied code is used."""
    return [
        sys.executable if arg == "python" and i == 0 else resolve_setting(arg, entry, output)
        for i, arg in enumerate(entry["command"])
    ]


def environment_for(entry: dict[str, Any], output: Path) -> dict[str, str]:
    """Resolve explicitly declared demo settings and keep output outside the source."""
    env = os.environ.copy()
    if entry.get("offline"):
        env.update(
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
            NO_LLM="1",
            AF_TRACING="false",
            OPENAI_AGENTS_DISABLE_TRACING="true",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            NEO4J_URI="",
            PGHOST="",
        )
    env.update({key: resolve_setting(value, entry, output) for key, value in entry["environment"].items()})
    paths = [str(REPO_ROOT)]
    for path in env.get("PYTHONPATH", "").split(os.pathsep):
        if path and (resolved := Path(path).resolve()) != output.resolve():
            paths.append(str(resolved))
    env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(paths))
    env["PYTHONSAFEPATH"] = "1"
    env.setdefault("AF_MEMORY_DIR", str(output.resolve() / "memory"))
    env.setdefault("AF_TRACING", "false")
    return env


def prerequisites_for(entry: dict[str, Any]) -> dict[str, Any]:
    """Check module and bundled-file presence without importing optional backends."""
    missing_modules = []
    for name in entry.get("required_modules", []):
        try:
            available = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            available = False
        if not available:
            missing_modules.append(name)
    missing_assets = [name for name in entry.get("assets", []) if not (DEMOS_ROOT / name).is_file()]
    runnable = bool(entry["command"])
    return {
        "schema": "agialpha.demo.prerequisites.v1",
        "demo": entry["id"],
        "runnable": runnable,
        "passed": runnable and not missing_modules and not missing_assets,
        "missing_modules": missing_modules,
        "missing_assets": missing_assets,
        "offline_defaults": entry.get("offline", False),
        "prerequisites": entry["prerequisites"],
        "guide": f"{GALLERY}demos/{entry['id']}/",
        "scope": (
            "Module and bundled-file presence only; "
            "model weights, service configuration and providers are not exercised."
        ),
    }


def print_prerequisites(report: dict[str, Any]) -> None:
    """Explain missing prerequisites without starting or installing anything."""
    if not report["runnable"]:
        print("This entry has no supported standalone CLI. Use its browser illustration and guide.")
    if report["missing_modules"]:
        print("Missing Python modules: " + ", ".join(report["missing_modules"]))
    if report["missing_assets"]:
        print("Missing bundled files: " + ", ".join(report["missing_assets"]))
        print("Reinstall the matching release; sample data is included in the wheel.")
    if report["passed"]:
        print("Declared modules and bundled files are present.")
    print(f"Prerequisites: {report['prerequisites']}\nGuide: {report['guide']}\nScope: {report['scope']}")


def main(argv: list[str] | None = None) -> int:
    """List, inspect or launch a documented demo with explicit expectations."""
    parser = argparse.ArgumentParser(description="Explore the AGIALPHA demo catalog")
    sub = parser.add_subparsers(dest="action")
    listing = sub.add_parser("list", help="List every demo and its execution mode")
    listing.add_argument("--json", action="store_true")
    for name, help_text in (
        ("show", "Show a guide without starting anything"),
        ("check", "Check declared prerequisites without imports, downloads or writes"),
        ("run", "Run the documented local command"),
    ):
        child = sub.add_parser(name, help=help_text)
        child.add_argument("demo", choices=[entry["id"] for entry in entries()])
        if name == "check":
            child.add_argument("--json", action="store_true", help="Print machine-readable prerequisite results")
        else:
            child.add_argument("--output-dir", type=Path, help="Directory for this demo's local state")
    args = parser.parse_args(argv)
    if args.action is None:
        parser.print_help()
        return 0
    if args.action == "list":
        if args.json:
            print(json.dumps(entries(), indent=2, ensure_ascii=False))
        else:
            for entry in entries():
                print(f"{entry['id']:<38} {entry['mode']}")
            print("\nStart: python -m alpha_factory_v1.demos show DEMO_NAME")
        return 0
    entry = next(item for item in entries() if item["id"] == args.demo)
    if args.action == "check":
        report = prerequisites_for(entry)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print_prerequisites(report)
        return 0 if report["passed"] else 2
    output = args.output_dir or Path.cwd() / "demo-runs" / entry["id"]
    print(f"\n{entry['title']} — {entry['mode']}\n{entry['summary']}")
    print(f"\nPrerequisites: {entry['prerequisites']}\nExpected: {entry['expected']}")
    print(f"Scope: {entry['limitations']}\nBrowser/guide: {GALLERY}demos/{entry['id']}/")
    command = command_for(entry, output)
    if not command:
        print("This entry has no supported standalone CLI. Use its browser illustration and guide.")
        return 0 if args.action == "show" else 2
    print(f"\nCommand: {shlex.join(command)}\nOutput directory: {output.resolve()}", flush=True)
    if entry["environment"]:
        print("Demo settings: " + ", ".join(entry["environment"]), flush=True)
    if args.action == "show":
        return 0
    report = prerequisites_for(entry)
    if not report["passed"]:
        print_prerequisites(report)
        return 2
    print_disclaimer()
    try:
        output.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(command, cwd=output, env=environment_for(entry, output), check=False)
        if result.returncode:
            print(
                f"Demo exited with status {result.returncode}. Output retained at {output.resolve()}.", file=sys.stderr
            )
            print(f"See {GALLERY}demos/{entry['id']}/ for this demo's setup and limits.", file=sys.stderr)
        return result.returncode
    except KeyboardInterrupt:
        print("\nStopped. Local output is retained.", file=sys.stderr)
        return 130
    except OSError as exc:
        print(f"Could not launch: {exc}. Check the prerequisites above.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
