#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# References to "AGI" and "superintelligence" describe aspirational goals
# and do not indicate the presence of a real general intelligence.
# Use at your own risk. Nothing herein constitutes financial advice.
# MontrealAI and the maintainers accept no liability for losses incurred.
"""Bounded UCB tree-search illustration over a numeric target, not a sector forecast."""

from __future__ import annotations

import argparse
import csv
import io
from contextlib import redirect_stdout
from dataclasses import dataclass, field
import math
import sys
import json
import os
import random
from pathlib import Path
from typing import List, Optional

from ... import get_version


def verify_environment() -> None:
    """Best-effort runtime dependency check."""
    try:
        import check_env  # type: ignore

        check_env.main([])
    except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover
        print(f"Environment verification failed: {exc}")
    except Exception as exc:
        print(f"Unexpected error during environment verification: {exc}")
        raise


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Configuration file not found: {path}")
    if path.stat().st_size > 64_000:
        raise ValueError("Configuration exceeds 64 KB")
    try:
        import yaml
    except ImportError as exc:
        raise ValueError("YAML configuration requires PyYAML; install the project dependencies") from exc
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeError) as exc:
        raise ValueError("Configuration must be valid UTF-8 YAML") from exc
    allowed = {"episodes", "exploration", "rewriter", "target", "seed", "model", "sectors"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("Configuration must be a mapping of documented settings")
    for field in ("episodes", "target", "seed"):
        if field in value and value[field] is not None and type(value[field]) is not int:
            raise ValueError(f"Configuration {field} must be an integer")
    if "exploration" in value and type(value["exploration"]) not in (int, float):
        raise ValueError("Configuration exploration must be numeric")
    return value


def save_ranking_plot(ranking: List[tuple[str, float]], path: Path) -> None:
    """Write a bar chart visualizing the ranking.

    Parameters
    ----------
    ranking:
        List of ``(sector, score)`` tuples sorted by descending score.
    path:
        Target image file path. ``.png`` extension is recommended.
    """

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    if not ranking:
        return

    sectors, scores = zip(*ranking)
    fig, ax = plt.subplots()
    ax.barh(sectors, scores, color="#1e3a8a")
    ax.invert_yaxis()
    ax.set_xlabel("Mean simulated numeric-target reward")
    ax.set_title("Search illustration — not a forecast")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


DEFAULT_SECTORS = [
    "Finance",
    "Healthcare",
    "Education",
    "Manufacturing",
    "Transportation",
    "Energy",
    "Retail",
    "Agriculture",
    "Defense",
    "Real Estate",
]


def offline_requested() -> bool:
    return any(
        os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
        for name in ("ALPHA_AGI_OFFLINE", "ALPHA_TEST_OFFLINE", "NO_LLM")
    )


def parse_sectors(
    cfg_val: object | None, cli_val: str | None, *, allow_files: bool = True, use_env: bool = True
) -> List[str]:
    source: object | None
    if cli_val is not None:
        source = cli_val
    elif use_env and os.getenv("ALPHA_AGI_SECTORS") is not None:
        source = os.getenv("ALPHA_AGI_SECTORS")
    else:
        source = cfg_val
    if source is None:
        source = list(DEFAULT_SECTORS)
    if isinstance(source, str):
        if len(source.encode("utf-8")) > 16_000:
            raise ValueError("Sector input exceeds 16 KB")
        candidate = Path(source)
        if allow_files and "\n" not in source and "," not in source and len(source) < 240 and candidate.is_file():
            with candidate.open("rb") as stream:
                data = stream.read(16_001)
            if len(data) > 16_000:
                raise ValueError("Sector file exceeds 16 KB")
            source = data.decode("utf-8")
        source = source.replace("\n", ",").split(",")
    if not isinstance(source, list) or not source or any(not isinstance(item, str) for item in source):
        raise ValueError("Sectors must be a nonempty list of names")
    result = [item.strip() for item in source if item.strip()]
    if not 1 <= len(result) <= 64 or len(set(result)) != len(result):
        raise ValueError("Use 1–64 unique sector names")
    if any(
        len(item.encode("utf-8")) > 120 or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in item)
        for item in result
    ):
        raise ValueError("Sector names must fit 120 UTF-8 bytes without control characters")
    return result


@dataclass
class SearchNode:
    value: int
    parent: Optional["SearchNode"] = None
    total: float = 0.0
    visits: int = 0
    children: List["SearchNode"] = field(default_factory=list)


def _provider_rewrite(value: int, rewriter: str, model: str | None) -> int:
    if not model:
        raise ValueError("A provider rewriter requires an explicit --model")
    prompt = f"Return only a JSON integer, one step larger or smaller than {value}."
    try:
        if rewriter == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY is required for the explicitly requested rewriter")
            from openai import OpenAI

            with OpenAI(timeout=15.0, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}], max_tokens=32
                )
                raw = response.choices[0].message.content or ""
        else:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise ValueError("ANTHROPIC_API_KEY is required for the explicitly requested rewriter")
            from anthropic import Anthropic

            with Anthropic(timeout=15.0, max_retries=0) as client:
                reply = client.messages.create(
                    model=model, messages=[{"role": "user", "content": prompt}], max_tokens=32
                )
                raw = getattr(reply.content[0], "text", "") if reply.content else ""
        result = json.loads(raw)
        if type(result) is not int or abs(result - value) != 1:
            raise ValueError("Provider must return one integer exactly one step from its input")
        return result
    except Exception as exc:
        # Never silently describe a random fallback as a successful model call.
        raise ValueError(
            "Provider rewrite failed; check credentials, model availability and the one-step response contract"
        ) from exc


def run(
    episodes: int = 5,
    exploration: float = 1.4,
    rewriter: str | None = None,
    log_dir: Path | None = None,
    *,
    target: int = 3,
    seed: Optional[int] = None,
    model: str | None = None,
    sectors: Optional[List[str]] = None,
    json_output: bool = False,
    offline: bool | None = None,
) -> str:
    if type(episodes) is not int or not 1 <= episodes <= 500:
        raise ValueError("Episodes must be an integer from 1 through 500")
    if type(exploration) not in (int, float) or not math.isfinite(exploration) or not 0 <= exploration <= 10:
        raise ValueError("Exploration must be finite, from 0 through 10")
    if type(target) is not int or not -10_000 <= target <= 10_000:
        raise ValueError("Numeric target must be an integer from -10000 through 10000")
    if seed is not None and (type(seed) is not int or not 0 <= seed <= 2**32 - 1):
        raise ValueError("Seed must be an integer from 0 through 4294967295")
    rewriter = rewriter or "random"
    if rewriter not in {"random", "openai", "anthropic"}:
        raise ValueError("Unknown rewriter")
    if rewriter != "random" and (offline is True or offline_requested()):
        raise ValueError("Offline mode forbids provider rewriters; choose random")
    if rewriter != "random" and episodes > 20:
        raise ValueError("Provider searches are limited to 20 calls")
    sectors = parse_sectors(sectors, None, allow_files=False, use_env=False)
    rng = random.Random(0 if seed is None else seed)
    root = SearchNode(0)
    observations: dict[int, list[float]] = {}
    trace = []
    for episode in range(1, episodes + 1):
        node = root
        while len(node.children) == 2:
            node = max(
                node.children,
                key=lambda n: n.total / n.visits + exploration * math.sqrt(math.log(node.visits + 1) / n.visits),
            )
        available = [
            node.value + step for step in (-1, 1) if node.value + step not in [child.value for child in node.children]
        ]
        proposed = rng.choice(available) if rewriter == "random" else _provider_rewrite(node.value, rewriter, model)
        if proposed not in available:
            proposed = available[0]
        child = SearchNode(proposed, node)
        node.children.append(child)
        reward = -abs(proposed - target) + rng.random() * 0.1
        current: SearchNode | None = child
        while current is not None:
            current.visits += 1
            current.total += reward
            current = current.parent
        index = proposed % len(sectors)
        observations.setdefault(index, []).append(reward)
        trace.append({"episode": episode, "candidate": sectors[index], "policy": proposed, "reward": reward})
        if not json_output:
            print(f"Episode {episode:>3}: candidate {sectors[index]} → reward {reward:.3f}")
    ranking = sorted(
        ((sectors[index], math.fsum(values) / len(values)) for index, values in observations.items()),
        key=lambda item: (-item[1], item[0]),
    )
    sector, score = ranking[0]
    result_data = {
        "best": sector,
        "score": score,
        "ranking": ranking,
        "seed": 0 if seed is None else seed,
        "episodes": episodes,
        "target": target,
        "rewriter": rewriter,
        "model": model if rewriter != "random" else None,
        "exploration": exploration,
        "sectors": sectors,
        "trace": trace,
        "scope": "Numeric-target search illustration; sector labels are mapped modulo list length. Scores are not forecasts.",
        "observations": {sectors[index]: len(values) for index, values in observations.items()},
    }
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        # Exclusive per-run directory prevents accidental overwrite and mixed concurrent results.
        import hashlib

        key = hashlib.sha256(json.dumps(result_data, sort_keys=True).encode()).hexdigest()
        destination = log_dir / key
        csv_buffer = io.StringIO(newline="")
        writer = csv.writer(csv_buffer)
        writer.writerow(["episode", "candidate", "policy", "reward"])
        for row in trace:
            label = row["candidate"]
            writer.writerow(
                [
                    row["episode"],
                    "'" + label if label.startswith(("=", "+", "-", "@")) else label,
                    row["policy"],
                    row["reward"],
                ]
            )
        expected = {
            "scores.csv": csv_buffer.getvalue().encode("utf-8"),
            "summary.json": (json.dumps(result_data, indent=2) + "\n").encode("utf-8"),
        }
        if destination.exists() or destination.is_symlink():
            if (
                destination.is_symlink()
                or not destination.is_dir()
                or any(
                    (destination / name).is_symlink()
                    or not (destination / name).is_file()
                    or (destination / name).read_bytes() != data
                    for name, data in expected.items()
                )
            ):
                raise ValueError("Existing search output differs; choose a new log directory")
        else:
            destination.mkdir()
            for name, data in expected.items():
                with (destination / name).open("xb") as stream:
                    stream.write(data)
            try:
                save_ranking_plot(ranking, destination / "ranking.png")
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                print(f"Search saved; optional plot unavailable: {exc}", file=sys.stderr)
        print(f"Search artifacts: {destination.resolve()}", file=sys.stderr)
    summary = f"Best sector: {sector} score: {score:.3f} (simulated numeric-target reward)"
    if json_output:
        return json.dumps(result_data, ensure_ascii=False, allow_nan=False)
    print(summary)
    print("Top sectors:")
    for position, (name, mean) in enumerate(ranking[:3], 1):
        print(f" {position}. {name} → {mean:.3f}")
    return summary


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the α‑AGI Insight demo")
    parser.add_argument("--episodes", type=int, help="Search iterations (1–500)")
    parser.add_argument("--offline", action="store_true", help="Forbid provider calls")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "configs" / "default.yaml",
        help="YAML configuration",
    )
    parser.add_argument(
        "--rewriter",
        choices=["random", "openai", "anthropic"],
        help="Rewrite strategy",
    )
    parser.add_argument("--target", type=int, help="Toy numeric target; sector names do not provide evidence")
    parser.add_argument("--seed", type=int, help="Optional RNG seed")
    parser.add_argument("--exploration", type=float, help="Exploration constant for UCB1")
    parser.add_argument("--model", type=str, help="Model for the rewriter")
    parser.add_argument("--log-dir", type=Path, help="Optional directory to store episode logs")
    parser.add_argument(
        "--sectors",
        type=str,
        help="Comma-separated sector names or path to a text file",
    )
    parser.add_argument(
        "--list-sectors",
        action="store_true",
        help="Print the resolved sector list and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Return JSON summary instead of plain text",
    )
    parser.add_argument(
        "--verify-env",
        action="store_true",
        help="Check runtime dependencies before running",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show program version and exit",
    )
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)

        if args.verify_env:
            with redirect_stdout(sys.stderr):
                verify_environment()
        episodes = int(
            args.episodes if args.episodes is not None else os.getenv("ALPHA_AGI_EPISODES", cfg.get("episodes", 5))
        )
        exploration = float(
            args.exploration
            if args.exploration is not None
            else os.getenv("ALPHA_AGI_EXPLORATION", cfg.get("exploration", 1.4))
        )
        rewriter = args.rewriter or os.getenv("MATS_REWRITER") or cfg.get("rewriter", "random")
        target = int(args.target if args.target is not None else os.getenv("ALPHA_AGI_TARGET", cfg.get("target", 3)))
        seed_val = args.seed if args.seed is not None else os.getenv("ALPHA_AGI_SEED") or cfg.get("seed")
        seed = int(seed_val) if seed_val is not None else None
        model = args.model or cfg.get("model")
        sectors = parse_sectors(cfg.get("sectors"), args.sectors)

        if args.list_sectors:
            print("Sectors:")
            for name in sectors:
                print(f"- {name}")
            return

        summary = run(
            episodes,
            exploration,
            rewriter,
            args.log_dir,
            target=target,
            seed=seed,
            model=model,
            sectors=sectors,
            json_output=args.json,
            offline=args.offline,
        )
        if args.json:
            print(summary)
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
