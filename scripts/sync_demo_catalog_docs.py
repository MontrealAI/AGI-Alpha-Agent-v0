# SPDX-License-Identifier: Apache-2.0
"""Keep current demo indexes aligned with the catalog without rewriting research content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tomllib
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATES = {
    "aiga_meta_evolution": "Native CPU generation, checkpoint and Hebbian paths",
    "alpha_agi_business_2_v1": "Service configuration and commissioning remain separate",
    "alpha_agi_business_3_v1": "Exact Python/browser parity, notebook, container and public browser checks",
    "alpha_agi_business_v1": "Bundled opportunity ranking and offline launch",
    "alpha_agi_insight_v0": "Native/browser discovery parity, exports and review boundaries",
    "alpha_agi_insight_v1": "Scenario CLI, browser replay, actual local GPT-2 and offline recovery",
    "alpha_agi_marketplace_v1": "Bundled dry-run job; live API submission remains separate",
    "alpha_asi_world_model": "Notebook and bounded backend tests; service commissioning remains separate",
    "alpha_super_planner_v1": "Scripted progress display; no planning computation claimed",
    "cross_industry_alpha_factory": "Deterministic catalog sampling; external generation remains separate",
    "era_of_experience": "Native/browser learning parity, held-out review, exports and offline recovery",
    "finance_alpha": "Python matrix, paper accounting, replay, notebook and browser acceptance",
    "gpt2_small_cli": "Actual offline GPT-2 generation with separately downloaded weights",
    "macro_sentinel": "Lower-tail risk arithmetic, bundled data and executed notebook",
    "meta_agentic_agi": "Repeated SQLite lineage and actual Streamlit viewer",
    "meta_agentic_agi_v2": "Repeated SQLite lineage and actual Streamlit viewer",
    "meta_agentic_agi_v3": "Curriculum parity, held-out tasks, exports and retained Streamlit viewer",
    "meta_agentic_tree_search_v0": "Native/browser search parity, exhaustive benchmark and review exports",
    "muzero_planning": "MuZero Python matrix, bounded training, browser Stop and container checks",
    "muzeromctsllmagent_v0": "MuZero Python matrix, retrieval, advice boundaries and real browser acceptance",
    "omni_factory_demo": "Bounded dry-run episodes and retained local accounting",
    "presentation": "Original presentation asset preservation",
    "self_healing_repo": "Repair benchmark and Docker isolation; proposed changes require review",
    "solving_agi_governance": "Nine-gate parity, hostile inputs, exact exports and public browser checks",
    "sovereign_agentic_agialpha_agent_v0": "Python matrix, signed reviews, recovery, lock and browser checks",
    "utils": "Shared utility tests and Docker boundary; no standalone demo",
}


def replace_region(text: str, name: str, content: str) -> str:
    """Replace one explicit generated region, retaining all surrounding prose."""
    start, end = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
        raise ValueError(f"Missing or ambiguous documentation region: {name}")
    before, _, rest = text.partition(start)
    _, _, after = rest.partition(end)
    return before + start + "\n" + content.rstrip() + "\n" + end + after


def cell(value: str) -> str:
    """Keep catalog text inside one Markdown table cell."""
    return value.replace("|", "\\|").replace("\n", " ")


def expected_documents(root: Path = ROOT) -> dict[Path, str]:
    """Render only maintained version, count and inventory sections."""
    base = root / "alpha_factory_v1/demos"
    catalog: dict[str, Any] = json.loads((base / "catalog.json").read_text(encoding="utf-8"))
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if catalog["release"] != version:
        raise ValueError("Catalog release must match pyproject.toml")
    entries = catalog["entries"]
    if {entry["id"] for entry in entries} != set(GATES):
        raise ValueError("Every catalog entry needs an explicit validation boundary in GATES")
    total = len(entries)
    finite = sum(bool(entry["smoke"]) for entry in entries)
    commands = sum(bool(entry["command"]) for entry in entries)
    docs: dict[Path, str] = {}

    def region(path: Path, name: str, content: str) -> None:
        current = docs.get(path, path.read_text(encoding="utf-8"))
        docs[path] = replace_region(current, name, content)

    readme = base / "README.md"
    region(
        readme,
        "CATALOG-RELEASE",
        f"**Current package: {version}.** [Start with the factory guide](../../docs/agent/FACTORY_GUIDE.md),\n"
        "[Protocol Desk](https://montrealai.github.io/AGI-Alpha-Agent-v0/ascension-protocol/) "
        "and native FusionPlan/evidence commands.\n"
        f"All {total} entries below remain available; their individual execution modes still apply.",
    )
    region(
        readme,
        "CATALOG-FINITE",
        f"All {finite} finite catalog commands use explicit offline settings and are tested from the built wheel\n"
        "outside the source tree with Python network calls blocked. Bundled inputs are resolved from the\n"
        "installation; output-directory configuration cannot select a paid tree-search provider. Child\n"
        "OpenAI/Anthropic keys and tracing are disabled for these finite commands; your shell settings are retained.\n"
        "Advanced standalone commands keep their separately documented options. The launcher is not a sandbox.",
    )
    rows = ["| Demo | Current mode | What it does |", "|---|---|---|"]
    for entry in entries:
        rows.append(
            f"| [{cell(entry['title'])}]({entry['id']}/README.md) | "
            f"{cell(entry['mode'])} | {cell(entry['summary'])} |"
        )
    region(readme, "CATALOG-INVENTORY", "\n".join(rows))

    walkthrough = root / "docs/agent/DEMOS.md"
    region(
        walkthrough,
        "CATALOG-RELEASE",
        f"**Version {version}.** The canonical directory is\n"
        "[`alpha_factory_v1/demos`]"
        "(https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos).\n"
        f"All {total} entries, their research narratives, flowcharts and media remain available.\n"
        "Start in the browser for an interactive tour, or run a finite local example below.",
    )
    region(
        walkthrough,
        "CATALOG-COUNTS",
        f"The catalog contains **{total} entries: {commands} launch commands "
        f"and {total - commands} guide-only entries**.\n"
        f"The {finite} finite catalog examples use explicit offline defaults. "
        "Their child processes disable configured\n"
        "OpenAI/Anthropic keys, remote Neo4j/PostgreSQL storage and tracing; tree search uses its bundled\n"
        "synthetic workflow model and reproducible private random stream.\n"
        f"Your shell credentials are unchanged. The release tests run all {finite} from the wheel with Python network\n"
        "calls blocked, including Python 3.11/3.12 environments with the full backend dependencies "
        "and inherited\n"
        "database settings. This verifies those launch contracts; "
        "the launcher is not a network or code sandbox.\n"
        "Advanced standalone commands and optional services retain their separately documented behavior.",
    )
    validation = root / "docs/agent/DEMO_VALIDATION.md"
    region(
        validation,
        "CATALOG-RELEASE",
        f"# Demo validation and execution modes — {version}\n\n"
        "Start with the [demo walkthrough](DEMOS.md) for installation, prerequisite checks, browser experiences\n"
        f"and the complete Ascension lifecycle. The release retains all {total} entries "
        f"and tests the {finite} finite offline\n"
        "commands from the actual wheel outside the repository. All six CSV samples and 11 Insight scenario\n"
        "fixtures are checked byte-for-byte against their source data.",
    )
    count_rows = (
        f"| Catalog | Exact {total}-directory coverage; {finite} finite commands, "
        "with repeat runs preserving v1/v2 SQLite "
        "history | `demo-catalog.json` in regression artifacts |\n"
        f"| Installed demos | All {finite} finite commands from the wheel with Python network calls blocked, inherited "
        "provider keys disabled and sample bytes preserved | `test_demo_distribution.py` in regression JUnit |\n"
        f"| Full backend wheel | All {finite} finite wheel commands with backend extras installed, inherited database "
        "settings disabled and test-only environment shortcuts removed | "
        "`demo-distribution-3.11` / `demo-distribution-3.12` JUnit |"
    )
    checks = docs[validation].partition("<!-- CATALOG-REQUIRED-COUNTS:START -->")[2]
    checks = checks.partition("<!-- CATALOG-REQUIRED-COUNTS:END -->")[0].strip()
    for row in count_rows.splitlines():
        label = row.split("|")[1].strip()
        checks, replacements = re.subn(rf"^\| {re.escape(label)} \|.*$", lambda _: row, checks, flags=re.M)
        if replacements != 1:
            raise ValueError(f"Expected one validation row: {label}")
    region(validation, "CATALOG-REQUIRED-COUNTS", checks)
    rows = [
        "| Directory | Current mode | Finite catalog gate | Additional evidence or boundary |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        gate = "Required" if entry["smoke"] else "Separate validation" if entry["command"] else "Guide only"
        rows.append(
            f"| [{entry['id']}](../demos/{entry['id']}.md) | {cell(entry['mode'])} | "
            f"{gate} | {GATES[entry['id']]} |"
        )
    region(validation, "CATALOG-INVENTORY", "\n".join(rows))
    for entry in entries:
        path = base / entry["id"] / "README.md"
        text = path.read_text(encoding="utf-8")
        start, end = "<!-- CURRENT-DEMO:START -->", "<!-- CURRENT-DEMO:END -->"
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
            raise ValueError(f"Missing or ambiguous current guide: {entry['id']}")
        before, _, rest = text.partition(start)
        section, _, after = rest.partition(end)
        section, headings = re.subn(
            r"^(## (?:Current runnable path|Start locally|Start in two minutes|Start here|Start in three steps) — )"
            r"\d+\.\d+\.\d+[ \t]*$",
            lambda match: match[1] + version,
            section,
            flags=re.M,
        )
        if headings != 1:
            raise ValueError(f"Expected one versioned current heading: {entry['id']}")
        docs[path] = before + start + section + end + after
    return docs


def synchronize(root: Path = ROOT, *, check: bool = False) -> list[Path]:
    """Write generated regions, or report stale documents without writing."""
    changed = []
    for path, expected in expected_documents(root).items():
        if path.read_text(encoding="utf-8") != expected:
            changed.append(path)
            if not check:
                path.write_text(expected, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on drift without changing files")
    args = parser.parse_args()
    changed = synchronize(check=args.check)
    for path in changed:
        print(f"{'STALE' if args.check else 'UPDATED'} {path.relative_to(ROOT)}")
    if args.check and changed:
        print("Run: python -m scripts.sync_demo_catalog_docs")
        return 1
    print("Catalog guides match the runnable inventory and release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
