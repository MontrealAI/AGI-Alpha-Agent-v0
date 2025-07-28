# SPDX-License-Identifier: Apache-2.0
"""Minimal CLI exposing orchestrator utilities."""
from __future__ import annotations

from pathlib import Path
import click

from alpha_factory_v1.core.self_evolution import harness
from alpha_factory_v1.core.governance.stake_registry import StakeRegistry

try:
    from alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface import cli as _insight_cli
except Exception:  # pragma: no cover - optional
    _insight_cli = None


@click.group()
def orch() -> None:
    """Orchestrator commands."""


@orch.command("self-test")
@click.argument("patch", type=click.Path(exists=True))
def self_test(patch: str) -> None:
    """Apply PATCH and run sandboxed tests."""
    registry = StakeRegistry()
    registry.set_stake("orch", 1.0)
    diff = Path(patch).read_text(encoding="utf-8")
    accepted = harness.vote_and_merge(Path.cwd(), diff, registry)
    click.echo("accepted" if accepted else "rejected")


if _insight_cli is not None:
    # Re-export the full Insight demo CLI when available
    main = _insight_cli.main  # type: ignore[attr-defined]
    for _name in (
        "agents_status",
        "run_orchestrator",
        "api_server_cmd",
        "self_improver_cmd",
        "simulate",
        "show_results",
        "show_memory",
        "explore",
        "replay",
        "archive",
        "archive_ls",
        "evolve_cmd",
        "transfer_test_cmd",
    ):
        if hasattr(_insight_cli, _name):
            globals()[_name] = getattr(_insight_cli, _name)
else:

    @click.group()
    def main() -> None:
        """α‑Factory command line interface."""

    main.add_command(orch)

    def agents_status(*_a: object, **_kw: object) -> None:
        raise click.ClickException("Insight demo not installed")


__all__ = ["main", "orch"]
for _x in (
    "agents_status",
    "run_orchestrator",
    "api_server_cmd",
    "self_improver_cmd",
    "simulate",
    "show_results",
    "show_memory",
    "explore",
    "replay",
    "archive",
    "archive_ls",
    "evolve_cmd",
    "transfer_test_cmd",
):
    if _x in globals():
        __all__.append(_x)


if __name__ == "__main__":  # pragma: no cover
    main()
