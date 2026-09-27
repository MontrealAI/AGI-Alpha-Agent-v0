# SPDX-License-Identifier: Apache-2.0
"""Publish practical cases, distinct previews and bridges from every original demo."""
from __future__ import annotations

import html
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def cases(root: Path = ROOT) -> list[dict[str, Any]]:
    """Read the canonical case definitions, or an empty list in isolated tests."""
    path = root / "docs/assets/studio/cases.json"
    return json.loads(path.read_text()) if path.is_file() else []


def lookup(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Map all preserved demo IDs to their practical workspace."""
    return {legacy: case for case in cases(root) for legacy in case["legacy"]}


def cards(root: Path = ROOT, prefix: str = "") -> str:
    """Render scenario cards with task, deliverable and distinct visual context."""
    out = ['<div class="decision-grid">']
    for i, case in enumerate(cases(root)):
        e = {key: html.escape(case[key], quote=True) for key in ("id", "title", "category", "question", "deliverable")}
        out.append(
            f'<a class="decision-card" href="{prefix}studio/?case={e["id"]}" '
            f'data-summary="{e["category"]} {e["question"]}">'
            f'<img src="{prefix}assets/studio/previews/{e["id"]}.svg" alt="" loading="lazy" width="600" height="360">'
            f'<div class="decision-card-copy"><p class="decision-kicker">{i + 1:02} / {e["category"]}</p>'
            f'<h3>{e["title"]}</h3><p>{e["question"]}</p><small>{e["deliverable"]}</small>'
            '<span class="decision-launch">Open workspace <b aria-hidden="true">↗</b></span></div></a>'
        )
    out.append("</div>")
    return "\n".join(out)


def preview(case: dict[str, Any], index: int) -> str:
    """Draw a domain-specific schematic; these are labeled inputs, never fake results."""
    kind = case["kind"]
    palette = ["#d9ed9c", "#daba7b", "#a7d0bd", "#d7c9a4"]
    accent = palette[index % len(palette)]
    shapes: list[str] = []
    label = ""
    if kind == "portfolio":
        items = case["input"]["datasets"]["projects"]
        label = "CAPITAL REQUIREMENTS / INPUT USD"
        maximum = max(r["cost"] for r in items)
        for i, item in enumerate(items[:12]):
            x = 38 + i * 44
            height = item["cost"] / maximum * 185
            shapes.append(
                f'<rect x="{x}" y="{270 - height:.1f}" width="28" height="{height:.1f}" '
                f'rx="2" fill="{accent}" opacity="{.55 + i * .035:.2f}"/>'
            )
            shapes.append(f'<text x="{x}" y="289" class="tiny">{i+1:02}</text>')
    elif kind == "schedule":
        label = "SHARED RESOURCES / WORK SEQUENCE"
        resources = list(dict.fromkeys(r["resource"] for r in case["input"]["datasets"]["operations"]))
        for i, resource in enumerate(resources):
            y = 95 + i * 48
            shapes.append(f'<text x="30" y="{y+18}" class="tiny">{html.escape(resource.upper())}</text>')
            for j in range(4):
                shapes.append(
                    f'<rect x="{155 + j * 94 + (i % 2) * 16}" y="{y}" width="{60 + (i + j) % 3 * 10}" '
                    f'height="28" rx="2" fill="{accent}" opacity="{.4 + j * .15}"/>'
                )
    elif kind == "inventory":
        label = "DEMAND HISTORY / INPUT OBSERVATIONS"
        values = [r["units"] for r in case["input"]["datasets"]["demand"]]
        maximum = max(values)
        points = " ".join(f"{30+i/(len(values)-1)*540:.1f},{275-v/maximum*170:.1f}" for i, v in enumerate(values))
        shapes.append(f'<polyline points="{points}" fill="none" stroke="{accent}" stroke-width="2.5"/>')
        x = 30 + (len(values) - case["input"]["parameters"]["holdout"]) / len(values) * 540
        shapes.append(
            f'<rect x="{x}" y="80" width="{570 - x}" height="205" fill="{accent}" opacity=".08"/>'
            f'<text x="{x}" y="304" class="tiny">HOLDOUT</text>'
        )
    elif kind == "energy":
        label = "FACILITY LOAD / SOLAR INPUTS"
        hours = case["input"]["datasets"]["hours"]
        for key, color in [("load_kwh", accent), ("solar_kwh", "#83b89d")]:
            points = " ".join(f"{30+i/23*540:.1f},{275-r[key]/60*180:.1f}" for i, r in enumerate(hours))
            shapes.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        shapes.append('<text x="30" y="304" class="tiny">00:00</text><text x="526" y="304" class="tiny">23:00</text>')
    elif kind == "procurement":
        label = "SUPPLIER CAPACITY / INPUT BATCHES"
        for i, item in enumerate(case["input"]["datasets"]["suppliers"]):
            y = 82 + i * 34
            shapes.append(
                f'<text x="30" y="{y + 14}" class="tiny">{html.escape(item["id"].upper())}</text>'
                f'<rect x="125" y="{y}" width="{item["capacity"] * 9}" height="20" rx="2" '
                f'fill="{accent}" opacity="{.45 + i * .1}"/>'
                f'<text x="{135 + item["capacity"] * 9}" y="{y + 15}" class="tiny">{item["capacity"]}</text>'
            )
    elif kind == "benchmark":
        label = "CALIBRATION / TEST PARTITIONS"
        for i in range(100):
            shapes.append(
                f'<rect x="{40 + (i % 20) * 26}" y="{108 + (i // 20) * 30}" width="18" height="18" '
                f'rx="2" fill="{accent if i < 40 else "#91c4ae"}" opacity=".85"/>'
            )
        shapes.append(
            '<text x="40" y="294" class="tiny">40 CALIBRATION</text>'
            '<text x="345" y="294" class="tiny">60 TEST CASES</text>'
        )
    else:
        label = "CLAIM → EVIDENCE → SCOPED WORK"
        for i, name in enumerate(["CLAIM", "SOURCE", "CRITERION", "PROOF JOB"]):
            x = 35 + i * 142
            if i < 3:
                shapes.append(f'<path d="M {x+92} 177 H {x+135}" stroke="{accent}" stroke-opacity=".5"/>')
            shapes.append(
                f'<rect x="{x}" y="127" width="92" height="98" rx="4" fill="none" '
                f'stroke="{accent}" stroke-opacity=".6"/>'
                f'<text x="{x + 13}" y="158" fill="{accent}" font-size="26" font-family="Georgia">{i + 1:02}</text>'
                f'<text x="{x + 9}" y="200" class="tiny">{name}</text>'
            )
        shapes.append('<text x="35" y="285" class="tiny">PROMOTION REQUIRES INDEPENDENT REVIEW</text>')
    return (
        "<!-- SPDX-License-Identifier: Apache-2.0 -->\n"
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 360">'
        f'<title>{html.escape(case["title"])} — {label.lower()}</title>'
        "<style>.tiny{font:9px Arial,sans-serif;fill:#d3dfce;letter-spacing:.5px}</style>"
        '<rect width="600" height="360" fill="#0a3029"/>'
        '<circle cx="560" cy="-40" r="200" fill="none" stroke="#527361" stroke-opacity=".2"/>'
        '<circle cx="560" cy="-40" r="260" fill="none" stroke="#527361" stroke-opacity=".15"/>'
        f'<text x="30" y="35" class="tiny">{index+1:02} / DECISION STUDIO</text>'
        '<path d="M30 54 H570" stroke="#436251" stroke-opacity=".6"/>'
        + "".join(shapes)
        + f'<text x="30" y="338" class="tiny">{label}</text>'
        + f'<text x="544" y="339" font-family="Georgia" font-size="24" fill="{accent}">α</text></svg>\n'
    )


def build(root: Path = ROOT) -> None:
    """Generate deterministic assets and add an actionable bridge to original pages."""
    entries = cases(root)
    target = root / "docs/assets/studio/previews"
    target.mkdir(parents=True, exist_ok=True)
    for i, case in enumerate(entries):
        (target / f'{case["id"]}.svg').write_text(preview(case, i))
    version = json.loads((root / "alpha_factory_v1/demos/catalog.json").read_text())["release"]
    studio = root / "docs/studio/index.html"
    studio.parent.mkdir(parents=True, exist_ok=True)
    studio.write_text((root / "scripts/templates/studio.html").read_text().replace("{{VERSION}}", version))
    for legacy, case in lookup(root).items():
        page = root / "docs" / legacy / "index.html"
        if not page.is_file():
            continue
        content = page.read_text()
        banner = (
            "<!-- decision-studio-bridge:start -->\n"
            '<section class="decision-bridge" aria-label="Practical decision workspace" '
            'style="max-width:1100px;margin:20px auto;padding:24px;background:#0a3029;color:#f5f5e7;'
            'border-radius:8px;font-family:Arial,sans-serif;box-sizing:border-box">'
            '<p style="font-size:11px;letter-spacing:2px;color:#d9ed9c">PUT THIS IDEA TO WORK</p>'
            f'<h2 style="font-family:Georgia,serif;font-weight:400">{html.escape(case["title"])}</h2>'
            f'<p>{html.escape(case["question"])}</p><p style="font-size:12px">{html.escape(case["deliverable"])}</p>'
            f'<a href="../studio/?case={case["id"]}" style="display:inline-block;padding:12px 18px;'
            'background:#d9ed9c;color:#173b2d;border-radius:4px;font-weight:bold">Open editable workspace ↗</a>'
            '<p style="font-size:11px">The original research presentation is preserved below.</p></section>\n'
            "<!-- decision-studio-bridge:end -->"
        )
        content = re.sub(
            r"<!-- decision-studio-bridge:start -->.*?<!-- decision-studio-bridge:end -->", "", content, flags=re.S
        )
        content = re.sub(r"(<body[^>]*>)\s*", lambda m: m.group(1) + "\n" + banner + "\n", content, count=1)
        page.write_text(content)


if __name__ == "__main__":
    build()
