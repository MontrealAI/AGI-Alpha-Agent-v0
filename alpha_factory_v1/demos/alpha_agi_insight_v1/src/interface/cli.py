# SPDX-License-Identifier: Apache-2.0
"""Command line utilities wrapping the Insight components.

Provides commands to run forecast simulations, inspect ledger entries and
launch the orchestrator. ``click`` is used for argument parsing and the
console output optionally leverages ``rich`` for nicer tables.
"""
# mypy: ignore-errors

from __future__ import annotations

import asyncio
import contextlib
import csv
import sys
import json
import os
import random
import time
from importlib import resources
from pathlib import Path
from typing import Any, Iterable, List, cast

import click
import af_requests as requests

try:
    from rich.console import Console
    from rich.table import Table
except Exception:  # pragma: no cover - optional
    Console = None
    Table = None

from alpha_factory_v1.core import orchestrator
from alpha_factory_v1.core.self_evolution import self_improver
from alpha_factory_v1.core.archive.hash_archive import HashArchive
from alpha_factory_v1.core.simulation import forecast, sector, mats
from alpha_factory_v1.core.utils.visual import plot_pareto
from alpha_factory_v1.common.utils import config, logging
from alpha_factory_v1.core.eval.foresight import evaluate as foresight_evaluate

from alpha_factory_v1.utils.disclaimer import DISCLAIMER

__all__ = [
    "DISCLAIMER",
    "DisclaimerGroup",
    "asyncio",
    "orchestrator",
    "self_improver",
]


class DisclaimerGroup(click.Group):
    """Group that prints a short disclaimer before any output."""

    def get_help(self, ctx: click.Context) -> str:  # pragma: no cover - CLI
        help_text = super().get_help(ctx)
        return f"{DISCLAIMER}\n\n{help_text}"

    def invoke(self, ctx: click.Context) -> Any:  # pragma: no cover - CLI
        click.echo(DISCLAIMER)
        return super().invoke(ctx)


console = Console() if Console else None


def _plain_table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    rows = list(rows)
    if not rows:
        return " | ".join(map(str, headers))

    cols = [list(map(str, col)) for col in zip(*([headers] + rows))]
    widths = [max(len(item) for item in col) for col in cols]
    line = "-+-".join("-" * w for w in widths)
    header = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    data_lines = [" | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row)) for row in rows]
    return "\n".join([header, line, *data_lines])


def _rich_table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
    if console and Table:
        table = Table(show_header=True, header_style="bold cyan")
        for h in headers:
            table.add_column(str(h))
        for row in rows:
            table.add_row(*[str(v) for v in row])
        console.print(table)
    else:
        click.echo(_plain_table(headers, rows))


def _format_results(res: List[forecast.ForecastPoint]) -> None:
    rows = [(r.year, f"{r.capability:.2f}", ",".join(s.name for s in r.affected)) for r in res]
    _rich_table(["year", "capability", "affected"], rows)


@click.group(cls=DisclaimerGroup)
def main() -> None:
    """α‑AGI Insight command line interface."""


@main.command()
@click.option(
    "--horizon",
    default=5,
    show_default=True,
    type=click.IntRange(min=1),
    help="Forecast horizon in years (>=1)",
)
@click.option("--curve", default="logistic", show_default=True, help="Capability growth curve")
@click.option("--k", type=float, help="Curve steepness parameter")
@click.option("--x0", type=float, help="Curve midpoint shift")
@click.option("--seed", type=int, help="Random seed")
@click.option("--offline", is_flag=True, help="Force offline mode")
@click.option("--no-broadcast", is_flag=True, help="Disable blockchain broadcasting")
@click.option("--llama-model-path", type=click.Path(), help="Path to local Llama model")
@click.option("--model", "model_name", help="Model name for AgentContext/local models")
@click.option("--temperature", type=float, help="Model temperature")
@click.option("--context-window", type=click.IntRange(min=1), help="Context window size (>=1)")
@click.option(
    "--import-dgm",
    "import_dgm",
    type=click.Path(exists=True),
    help="Import DGM logs before simulation",
)
@click.option("--sectors-file", type=click.Path(exists=True), help="JSON file with sector definitions")
@click.option(
    "--sectors",
    default=6,
    show_default=True,
    type=click.IntRange(min=1),
    help="Number of sectors (>=1)",
)
@click.option(
    "--energy",
    default=1.0,
    show_default=True,
    type=float,
    help="Initial sector energy (also configurable via the web UI)",
)
@click.option(
    "--entropy",
    default=1.0,
    show_default=True,
    type=float,
    help="Initial sector entropy (also configurable via the web UI)",
)
@click.option(
    "--pop-size",
    default=6,
    show_default=True,
    type=click.IntRange(min=1),
    help="MATS population size (>=1)",
)
@click.option(
    "--generations",
    default=3,
    show_default=True,
    type=click.IntRange(min=1),
    help="Evolution steps (>=1)",
)
@click.option(
    "--mut-rate",
    default=0.1,
    show_default=True,
    type=click.FloatRange(0.0, 1.0),
    help="Mutation rate during crossover (0-1)",
)
@click.option(
    "--xover-rate",
    default=0.5,
    show_default=True,
    type=click.FloatRange(0.0, 1.0),
    help="Crossover rate (0-1)",
)
@click.option(
    "--backtrack-rate",
    default=0.0,
    show_default=True,
    type=float,
    help="Probability of selecting low-scoring parents",
)
@click.option("--dry-run", is_flag=True, help="Run offline without broadcasting")
@click.option("--export", type=click.Choice(["json", "csv"]), help="Export results format")
@click.option("--save-plots", is_flag=True, help="Write pareto.png and pareto.json")
@click.option("--verbose", is_flag=True, help="Verbose output")
@click.option("--start-orchestrator", is_flag=True, help="Run orchestrator after simulation")
def simulate(
    horizon: int,
    curve: str,
    seed: int | None,
    offline: bool,
    sectors_file: str | None,
    sectors: int,
    energy: float,
    entropy: float,
    pop_size: int,
    generations: int,
    mut_rate: float,
    xover_rate: float,
    backtrack_rate: float,
    dry_run: bool,
    export: str | None,
    save_plots: bool,
    verbose: bool,
    start_orchestrator: bool,
    no_broadcast: bool,
    llama_model_path: str | None,
    model_name: str | None,
    temperature: float | None,
    context_window: int | None,
    import_dgm: str | None,
    k: float | None,
    x0: float | None,
) -> None:
    """Run a forecast simulation.

    Args:
        horizon: Forecast horizon in years.
        curve: Name of the capability growth curve.
        seed: Random seed for deterministic output.
        offline: Force offline mode.
        sectors_file: JSON file with sector definitions.
        sectors: Number of sectors to simulate.
        energy: Initial sector energy.
        entropy: Initial sector entropy.
        pop_size: MATS population size.
        generations: Number of evolution steps.
        mut_rate: Probability of mutating a gene.
        xover_rate: Probability of performing crossover.
        backtrack_rate: Probability of selecting low-scoring parents.
        dry_run: Run offline without broadcasting.
        export: Format to export results.
        save_plots: Save pareto.png and pareto.json in the working directory.
        verbose: Enable verbose output.
        start_orchestrator: Launch orchestrator after the run.
        no_broadcast: Disable ledger broadcasting.
        llama_model_path: Path to a local Llama model.
        model_name: Model identifier for LLM calls.
        temperature: Sampling temperature for completions.
        context_window: Prompt context window size.
        import_dgm: Directory with DGM logs to import.
        k: Optional growth curve steepness.
        x0: Optional growth curve midpoint shift.

    Returns:
        None
    """
    if seed is not None:
        random.seed(seed)
        with contextlib.suppress(ModuleNotFoundError):
            import numpy as np  # type: ignore

            np.random.seed(seed)
        with contextlib.suppress(ModuleNotFoundError):
            import torch  # type: ignore

            torch.manual_seed(seed)
        config.CFG.seed = seed

    if llama_model_path is not None:
        os.environ["LLAMA_MODEL_PATH"] = str(llama_model_path)

    if import_dgm is not None:
        from alpha_factory_v1.core.tools import dgm_import

        dgm_import.import_logs(import_dgm)

    settings = config.CFG.model_copy()
    if dry_run:
        offline = True
        no_broadcast = True
    if offline:
        settings.offline = True
    if model_name is not None:
        settings.model_name = model_name
    if temperature is not None:
        settings.temperature = temperature
    if context_window is not None:
        settings.context_window = context_window
    if no_broadcast:
        settings.broadcast = False

    orch = orchestrator.Orchestrator(settings)
    if sectors_file:
        secs = sector.load_sectors(sectors_file, energy=energy, entropy=entropy)
    else:
        secs = [sector.Sector(f"s{i:02d}", energy, entropy) for i in range(sectors)]
    trajectory = forecast.forecast_disruptions(
        secs,
        horizon,
        curve=curve,
        k=k,
        x0=x0,
        pop_size=pop_size,
        generations=generations,
        seed=seed,
        mut_rate=mut_rate,
        xover_rate=xover_rate,
    )
    results = [forecast.ForecastPoint(t.year, t.capability, [s for s in t.sectors if s.disrupted]) for t in trajectory]

    if export == "json":
        data = [
            {
                "year": r.year,
                "capability": r.capability,
                "affected": [s.name for s in r.affected],
            }
            for r in results
        ]
        click.echo(json.dumps(data))
    elif export == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["year", "capability", "affected"])
        for r in results:
            writer.writerow([r.year, r.capability, "|".join(s.name for s in r.affected)])
    else:
        _format_results(results)

    # evaluate forecast accuracy on the Sector-Shock-10 dataset
    try:
        repo_root = Path(str(resources.files("alpha_factory_v1")))
        if not (repo_root / "data" / "sector_shock_10").exists():
            raise FileNotFoundError
    except Exception:  # pragma: no cover - fallback for editable installs
        repo_root = Path(__file__).resolve().parents[5]

    scores = foresight_evaluate(repo_root)

    result_data = {
        "version": 1,
        "forecast": [
            {
                "year": r.year,
                "capability": r.capability,
                "affected": [s.name for s in r.affected],
            }
            for r in results
        ],
        "scores": scores,
    }

    results_dir = Path(
        os.getenv(
            "SIM_RESULTS_DIR",
            os.path.join(os.getenv("ALPHA_DATA_DIR", "/tmp/alphafactory"), "simulations"),
        )
    )
    results_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    out_file = results_dir / f"{int(time.time())}.json"
    out_file.write_text(json.dumps(result_data))

    if save_plots:

        def eval_fn(genome: list[float]) -> tuple[float, float, float]:
            x, y = genome
            return x**2, y**2, (x + y) ** 2

        pop = mats.run_evolution(
            eval_fn,
            2,
            population_size=pop_size,
            generations=generations,
        )
        elites = [ind for ind in pop if ind.rank == 0]
        plot_pareto(elites, Path("pareto.png"))

    if not start_orchestrator:
        ledger = getattr(orch, "ledger", None)
        if ledger is not None:
            task = getattr(ledger, "_task", None)
            if isinstance(getattr(asyncio, "Task", None), type) and isinstance(task, asyncio.Task):
                try:
                    asyncio.run(ledger.stop_merkle_task())
                except Exception:  # pragma: no cover - best effort cleanup
                    pass
            if hasattr(ledger, "close"):
                ledger.close()
    else:
        if start_orchestrator and verbose and console is not None:
            console.log("Starting orchestrator … press Ctrl+C to stop")
        try:
            asyncio.run(orch.run_forever())
        except KeyboardInterrupt:  # pragma: no cover - interactive
            pass


@main.command("show-results")
@click.option(
    "--limit",
    default=10,
    show_default=True,
    type=click.IntRange(min=1),
    help="Entries to display (>=1)",
)
@click.option("--export", type=click.Choice(["json", "csv"]), help="Export results format")
def show_results(limit: int, export: str | None) -> None:
    """Show recent ledger entries.

    Args:
        limit: Number of entries to display.
        export: Format to export results.

    Returns:
        None
    """
    path = Path(config.CFG.ledger_path)
    if not path.exists():
        click.echo("No results found")
        return
    with logging.Ledger(str(path)) as led:
        rows = led.tail(limit)
        if not rows:
            click.echo("No results found")
            return
        data = [
            (
                f"{r['ts']:.2f}",
                r["sender"],
                r["recipient"],
                json.dumps(r["payload"]),
            )
            for r in rows
        ]
    if export == "json":
        items = [
            {
                "ts": r[0],
                "sender": r[1],
                "recipient": r[2],
                "payload": json.loads(r[3]),
            }
            for r in data
        ]
        click.echo(json.dumps(items))
    elif export == "csv":
        lines = ["ts,sender,recipient,payload"]
        for r in data:
            lines.append(f"{r[0]},{r[1]},{r[2]},{r[3].replace(',', ';')}")
        click.echo("\n".join(lines))
    else:
        _rich_table(["ts", "sender", "recipient", "payload"], data)


@main.command("show-memory")
@click.option(
    "--limit",
    default=10,
    show_default=True,
    type=click.IntRange(min=1),
    help="Entries to display (>=1)",
)
@click.option("--export", type=click.Choice(["json", "csv"]), help="Export results format")
def show_memory(limit: int, export: str | None) -> None:
    """Display stored memory entries."""
    path = config.CFG.memory_path
    if not path:
        click.echo("Memory persistence not enabled")
        return
    mem_file = Path(path)
    if not mem_file.exists():
        click.echo("No memory entries")
        return
    entries = []
    for line in mem_file.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:  # noqa: BLE001 - ignore bad records
            entries.append({"raw": line})
    if not entries:
        click.echo("No memory entries")
        return
    entries = entries[-limit:]
    if export == "json":
        click.echo(json.dumps(entries))
    elif export == "csv":
        lines = ["payload"]
        for e in entries:
            lines.append(json.dumps(e).replace(",", ";"))
        click.echo("\n".join(lines))
    else:
        _rich_table(["payload"], [(json.dumps(e),) for e in entries])


@main.command("agents-status")
@click.option("--watch", is_flag=True, help="Continuously monitor agents")
def agents_status(watch: bool) -> None:
    """Display registered agents.

    Args:
        watch: Continuously monitor agent status changes.

    Returns:
        None
    """

    base = os.getenv("BUSINESS_HOST", "http://localhost:8000").rstrip("/")
    token = os.getenv("API_TOKEN", "")

    if not token:
        click.echo("API_TOKEN not configured")
        raise SystemExit(1)

    def _fetch() -> list[dict[str, object]]:
        resp = requests.get(
            f"{base}/status",
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=5,
        )
        if resp.status_code != 200:
            raise click.ClickException(f"HTTP {resp.status_code}")
        data = cast(dict[str, Any], resp.json())
        agents = cast(dict[str, Any], data.get("agents", {}))
        if isinstance(agents, dict):
            return [
                {
                    "name": name,
                    "last_beat": info.get("last_beat", 0),
                    "restarts": info.get("restarts", 0),
                }
                for name, info in agents.items()
            ]
        return cast(list[dict[str, object]], agents)

    def render() -> None:
        rows = [(a.get("name"), f"{a.get('last_beat', 0):.0f}", a.get("restarts", 0)) for a in _fetch()]
        _rich_table(["agent", "last_beat", "restarts"], rows)

    try:
        while True:
            render()
            if not watch:
                break
            time.sleep(2)
    except KeyboardInterrupt:  # pragma: no cover - interactive
        pass


@main.command(name="orchestrator")
@click.option("--verbose", is_flag=True, help="Verbose output")
@click.option("--model", "model_name", help="Model name for AgentContext/local models")
@click.option("--temperature", type=float, help="Model temperature")
@click.option("--context-window", type=click.IntRange(min=1), help="Context window size (>=1)")
def run_orchestrator(
    verbose: bool, model_name: str | None, temperature: float | None, context_window: int | None
) -> None:
    """Run the orchestrator until interrupted."""
    settings = config.CFG
    if model_name is not None:
        settings.model_name = model_name
    if temperature is not None:
        settings.temperature = temperature
    if context_window is not None:
        settings.context_window = context_window
    orch = orchestrator.Orchestrator(settings)
    if verbose and console is not None:
        console.log("Starting orchestrator … press Ctrl+C to stop")
    try:
        asyncio.run(orch.run_forever())
    except KeyboardInterrupt:  # pragma: no cover - interactive
        pass


@main.command(name="api-server")
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind host")
@click.option(
    "--port",
    type=click.IntRange(min=1, max=65535),
    default=8000,
    show_default=True,
    help="Bind port (1-65535)",
)
def api_server_cmd(host: str, port: int) -> None:
    """Launch the FastAPI backend server."""

    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover - optional
        raise click.ClickException("uvicorn is required to run the API server") from exc

    uvicorn.run(
        "alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server:app",
        host=host,
        port=port,
    )


@main.command(name="self-improver")
@click.option("--repo", "repo_url", required=True, help="Repository URL or path")
@click.option("--patch", "patch_file", type=click.Path(exists=True), required=True, help="Unified diff file")
@click.option("--metric-file", default="metric.txt", show_default=True, help="Metric file inside repo")
@click.option("--log", "log_file", default="improver_log.json", show_default=True, help="JSON file to append results")
def self_improver_cmd(repo_url: str, patch_file: str, metric_file: str, log_file: str) -> None:
    """Clone repo, apply patch, evaluate score delta and log it."""

    delta, _ = self_improver.improve_repo(repo_url, patch_file, metric_file, log_file)
    click.echo(f"score delta: {delta}")


@main.command()
@click.option("--jobs", "jobs_file", type=click.Path(exists=True), required=True, help="JSON file with jobs")
@click.option("--token-quota", type=click.IntRange(min=1), help="Maximum tokens to consume (>=1)")
@click.option("--time-quota", type=click.IntRange(min=1), help="Maximum runtime in seconds (>=1)")
def explore(jobs_file: str, token_quota: int | None, time_quota: int | None) -> None:
    """Run self-improvement jobs under quota limits."""

    from alpha_factory_v1.core import scheduler

    data = json.loads(Path(jobs_file).read_text())
    jobs = [scheduler.Job(**item) for item in data]
    sched = scheduler.SelfImprovementScheduler(jobs, tokens_quota=token_quota, time_quota=time_quota)
    asyncio.run(sched.serve())


@main.command()
@click.option("--since", type=float, help="Replay events newer than timestamp")
@click.option("--count", type=click.IntRange(min=1), help="Number of events to replay (>=1)")
def replay(since: float | None, count: int | None) -> None:
    """Replay ledger events with a short delay.

    Returns:
        None
    """
    path = Path(config.CFG.ledger_path)
    if not path.exists():
        click.echo("No ledger to replay")
        return
    with logging.Ledger(str(path)) as led:
        limit = count or 1000
        rows = led.tail(limit)
        if since is not None:
            since_val = since
            rows = [r for r in rows if r["ts"] >= since_val]
        for row in rows:
            msg = f"{row['ts']:.2f} {row['sender']} -> {row['recipient']} {json.dumps(row['payload'])}"
            click.echo(msg)
            time.sleep(0.1)


@main.group()
def archive() -> None:
    """Manage archived agent tarballs."""


@archive.command("ls")
@click.option("--proof", is_flag=True, help="Show Merkle proof stubs")
@click.option("--db", "db_path", default="hash_archive.db", show_default=True, help="Archive database path")
def archive_ls(proof: bool, db_path: str) -> None:
    """List pinned CIDs."""

    arch = HashArchive(db_path)
    entries = arch.list_entries()
    if not entries:
        click.echo("No archive entries")
        return
    headers = ["id", "cid"]
    rows: list[tuple[str, str]] = [(e[0], e[2]) for e in entries]
    if proof:
        root = arch.merkle_root()
        headers.append("proof")
        rows_with_proof: list[tuple[str, str, str]] = [(r[0], r[1], root[:16]) for r in rows]
        _rich_table(headers, rows_with_proof)
    else:
        _rich_table(headers, rows)


@main.command(name="evolve")
@click.option("--max-cost", default=1.0, show_default=True, type=float, help="Cost budget")
@click.option("--wallclock", type=float, help="Wallclock limit in seconds")
@click.option(
    "--backtrack-rate",
    default=0.0,
    show_default=True,
    type=float,
    help="Probability of selecting low-scoring parents",
)
@click.option("--beta", default=1.0, show_default=True, type=float, help="Score weight")
@click.option(
    "--gamma",
    default=0.0,
    show_default=True,
    type=float,
    help="Edit children count weight",
)
@click.option(
    "--max-cost-per-gain",
    type=float,
    help="Stop if GPU seconds per fitness gain exceed this value",
)
def evolve_cmd(
    max_cost: float,
    wallclock: float | None,
    backtrack_rate: float,
    beta: float,
    gamma: float,
    max_cost_per_gain: float | None,
) -> None:
    """Run the minimal asynchronous evolution demo."""
    from alpha_factory_v1.core import evolve as _evolve

    async def _eval(genome: float) -> tuple[float, float]:
        await asyncio.sleep(0)
        return random.random(), 0.01

    archive = _evolve.InMemoryArchive()
    asyncio.run(
        _evolve.evolve(
            lambda g: g,
            _eval,
            archive,
            max_cost=max_cost,
            wallclock=wallclock,
            backtrack_rate=backtrack_rate,
            beta=beta,
            gamma=gamma,
            cost_threshold=max_cost_per_gain,
        )
    )


@main.command(name="transfer-test")
@click.option(
    "--models",
    default="claude-3.7,gpt-4o",
    show_default=True,
    help="Comma-separated list of models",
)
@click.option(
    "--top-n",
    default=3,
    show_default=True,
    type=click.IntRange(min=1),
    help="Number of top agents (>=1)",
)
def transfer_test_cmd(models: str, top_n: int) -> None:
    """Replay top agents on alternate models and store results."""
    model_list = [m.strip() for m in models.split(",") if m.strip()]
    from alpha_factory_v1.core.tools import transfer_test as _tt

    _tt.run_transfer_test(model_list, top_n)


if __name__ == "__main__":  # pragma: no cover
    main()
