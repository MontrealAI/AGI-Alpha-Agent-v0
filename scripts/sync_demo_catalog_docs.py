# SPDX-License-Identifier: Apache-2.0
"""Keep demo inventories and current launch headings aligned with the executable catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- DEMO-INVENTORY:START -->"
END = "<!-- DEMO-INVENTORY:END -->"


def render_inventory(root: Path, *, validation: bool = False) -> str:
    """Render execution modes, descriptions and finite-gate coverage from one source."""
    catalog = json.loads((root / "alpha_factory_v1/demos/catalog.json").read_text(encoding="utf-8"))
    entries = catalog["entries"]
    finite = sum(entry["smoke"] for entry in entries)
    lines = [
        START,
        f"**Catalog {catalog['release']}: {len(entries)} entries; {finite} finite offline launch checks.**",
        "",
        "| Demo | Current mode | What it does | Finite catalog check |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        link = f"../demos/{entry['id']}.md" if validation else f"{entry['id']}/README.md"
        gate = "Required" if entry["smoke"] else "Separate acceptance / prerequisites"
        title, mode, summary = (str(entry[key]).replace("|", "&#124;") for key in ("title", "mode", "summary"))
        lines.append(f"| [{title}]({link}) | {mode} | {summary} | {gate} |")
    return "\n".join([*lines, END])


def synchronize(root: Path = ROOT, *, check: bool = False) -> list[str]:
    """Refresh marked inventories and launch versions; preserve historical prose and diagrams."""
    updates: dict[Path, str] = {}
    for relative, validation in (
        ("alpha_factory_v1/demos/README.md", False),
        ("docs/agent/DEMO_VALIDATION.md", True),
    ):
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(START) != 1 or original.count(END) != 1 or original.index(START) > original.index(END):
            raise ValueError(f"Expected one ordered inventory marker pair: {relative}")
        updated = re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            lambda _: render_inventory(root, validation=validation),
            original,
            flags=re.DOTALL,
        )
        if updated != original:
            updates[path] = updated
    catalog = json.loads((root / "alpha_factory_v1/demos/catalog.json").read_text(encoding="utf-8"))
    for entry in catalog["entries"]:
        path = root / "alpha_factory_v1/demos" / entry["id"] / "README.md"
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")

        def update_heading(match: re.Match[str]) -> str:
            section = re.sub(
                r"\A(\s*## (?:Current runnable path|Start locally) — )\d+\.\d+\.\d+",
                lambda heading: heading[1] + catalog["release"],
                match[2],
            )
            return match[1] + section + match[3]

        updated = re.sub(
            r"(<!-- CURRENT-DEMO:START -->)(.*?)(<!-- CURRENT-DEMO:END -->)",
            update_heading,
            original,
            flags=re.DOTALL,
        )
        if updated != original:
            updates[path] = updated
    if not check:
        for path, updated in updates.items():
            path.write_text(updated, encoding="utf-8")
    return [str(path.relative_to(root)) for path in updates]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on stale inventories without writing")
    args = parser.parse_args()
    stale = synchronize(check=args.check)
    if stale:
        print(("Stale" if args.check else "Updated") + " demo inventories: " + ", ".join(stale))
    else:
        print("Demo inventories match the executable catalog")
    return int(args.check and bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
