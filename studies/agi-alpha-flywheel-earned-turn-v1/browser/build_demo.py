"""Build one offline HTML from the exact local browser/scientific source closure."""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
IMPORTS = re.compile(r"^import\s+[\s\S]*?\s+from\s+(['\"])([^'\"]+)\1\s*;", re.M)
modules: dict[str, str] = {}


def include(path: Path) -> None:
    """Capture an inert, statically imported module inside the companion tree."""
    path = path.resolve()
    key = path.relative_to(BASE).as_posix()
    if key in modules:
        return
    source = path.read_text(encoding="utf-8")
    modules[key] = source
    for match in IMPORTS.finditer(source):
        target = match.group(2)
        if not target.startswith("."):
            raise ValueError(f"External import is not permitted in offline bundle: {key}: {target}")
        include(path.parent / target)


def encoded(value: object) -> str:
    """Keep source text inert inside an HTML JSON script element."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(
        "\u2028", "\\u2028"
    ).replace("\u2029", "\\u2029")


def recorded_details(record: dict | None) -> str:
    """Render recorded evidence only; numerical execution stays in the frozen modules."""
    if record is None:
        return ""
    analysis = record["analysis"]
    flywheel = analysis["arms"]["flywheel"]
    comparison = analysis["comparisons"]["native_refactor"]
    ratio = comparison["cpu_ratio"]
    lower, upper = comparison["ci95"]
    coordinate = lambda value: 20 + (value - 0.93) / 0.12 * 320
    metric = lambda value, label: f'<div><strong>{html.escape(str(value))}</strong><span>{label}</span></div>'
    metrics = metric(f'{flywheel["qualified"]} / {flywheel["offered"]}', "qualified per arm")
    metrics += metric(flywheel["successors"], "scoped successors")
    metrics += metric(flywheel["parent_using_qualified_fresh"], "fresh D parent calls")
    rows = []
    names = {
        "flywheel": "Flywheel",
        "native_refactor": "Native reuse + refactor",
        "conventional_reuse": "Conventional reuse",
        "direct_specialist": "Parent-free specialist",
        "equivalent": "Equivalent asset",
        "parent_rebuilt": "Reconstructed parent",
        "no_reinvestment": "No reinvestment",
    }
    for key, label in names.items():
        arm = analysis["arms"][key]
        rows.append(f'<tr><td>{label}</td><td>{arm["mean_cpu_ms"]:,.3f}</td><td>{arm["qualified"]}/{arm["offered"]}</td></tr>')
    example = record["example_first_registered_stream"]
    lineage = []
    labels = {
        "A": "Useful response + factor retained",
        "B08": "Changed load uses the exact parent",
        "C": "Accepted B08 flows define the successor",
        "D01": "Fresh changed-network output uses it",
    }
    for mission in example["missions"]:
        if mission["id"] not in labels:
            continue
        lineage.append(f'<li><b>{mission["id"]}</b><span>{labels[mission["id"]]}<small>Residual {mission["checker"]["relative_residual"]:.2e} · {mission["details"]["parent_calls"]} parent calls</small></span></li>')
    return f'''<div class="recorded-metrics">{metrics}</div>
<div class="recorded-comparison"><div class="recorded-comparison-title"><strong>Whole-workflow CPU ratio</strong><span class="badge hold">PRODUCT HOLD</span></div><p class="recorded-ratio">{ratio:.3f}<span>95% CI [{lower:.3f}, {upper:.3f}]</span></p>
<svg class="ratio-plot" viewBox="0 0 360 78" role="img" aria-label="CPU ratio {ratio:.6f}; 95 percent interval {lower:.6f} to {upper:.6f}. The upper interval exceeds the required 0.95 benefit threshold.">
<line x1="20" x2="340" y1="25" y2="25" stroke="#51415f"/>
<line x1="{coordinate(.95):.3f}" x2="{coordinate(.95):.3f}" y1="9" y2="39" stroke="#ecc78b" stroke-dasharray="3 3"/>
<line x1="{coordinate(1):.3f}" x2="{coordinate(1):.3f}" y1="9" y2="39" stroke="#a99cbf" stroke-dasharray="3 3"/>
<line x1="{coordinate(lower):.3f}" x2="{coordinate(upper):.3f}" y1="25" y2="25" stroke="#ad86ff" stroke-width="5" stroke-linecap="round"/>
<circle cx="{coordinate(ratio):.3f}" cy="25" r="6" fill="#65dccb" stroke="#141020" stroke-width="2"/>
<text x="{coordinate(.95):.3f}" y="57" text-anchor="middle" fill="#ecc78b" font-size="10">0.95</text><text x="{coordinate(.95):.3f}" y="72" text-anchor="middle" fill="#b8adc9" font-size="9">required bound</text>
<text x="{coordinate(1):.3f}" y="57" text-anchor="middle" fill="#b8adc9" font-size="10">1.00</text><text x="{coordinate(1):.3f}" y="72" text-anchor="middle" fill="#b8adc9" font-size="9">native comparator</text></svg>
<p class="small muted">The upper confidence bound must be below 0.95. This criterion was not met. The conventional-reuse noninferiority guard passed; superiority was not established.</p></div>
<details class="recorded-detail"><summary>Inspect all seven comparisons</summary><div class="table-scroll"><table><thead><tr><th>Native workflow</th><th>Mean CPU ms</th><th>Qualified</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="small muted">Paired, independent streams are the uncertainty unit. Every offered output qualified in each arm. Whole-workflow CPU includes checking and control overhead.</p></details>
<details class="recorded-detail"><summary>Trace one actual A → B → C → D</summary><p class="small muted">First registered recurring stream, seed {example['seed']}. These are native records, separate from the four live browser missions.</p><ol class="recorded-lineage">{''.join(lineage)}</ol><p class="small muted">The download contains full input, result, receipt and asset identities, exact edge changes, SHIFT and unsupported-case evidence.</p></details>
<p class="recorded-resource"><strong>Resource transfer:</strong> {flywheel['released_ms']:,.0f} ms of unused supplied quota released; {flywheel['construction_debits_ms']:,.3f} ms actually debited for successor construction. The source was external endowment. This does not demonstrate causal savings or cash earned.</p>
<p class="small muted">Full investment recovery unresolved · Acceleration not tested · Commercial growth not measured</p>'''


include(ROOT / "app.mjs")
manifest = {key: hashlib.sha256(value.encode()).hexdigest() for key, value in sorted(modules.items())}
source_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
execution_manifest = dict(manifest)
execution_manifest["browser/bootstrap.mjs"] = hashlib.sha256((ROOT / "bootstrap.mjs").read_bytes()).hexdigest()
execution_hash = hashlib.sha256(
    json.dumps(execution_manifest, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
recorded_path = ROOT / "recorded-summary.json"
recorded = json.loads(recorded_path.read_text()) if recorded_path.exists() else None
data = {
    "schema": "earned-turn-browser-bundle/v1",
    "source_hash": source_hash,
    "execution_source_hash": execution_hash,
    "execution_manifest": execution_manifest,
    "module_manifest": manifest,
    "upstream_commit": "c352bad0a0941fdccd490a7224e3efd1b8de45d5",
    "upstream_release": "v1.42.0",
    "upstream_description": "Released workbench c352bad0; mission-store current main, exact per-file manifest retained",
    "research": recorded,
    "scope": "Fresh finite demonstration, separate from the frozen confirmatory campaign and installed native runtime.",
}
page = (ROOT / "template.html").read_text().replace("__STYLES__", (ROOT / "styles.css").read_text())
page = page.replace("__RECORDED_DETAILS__", recorded_details(recorded))
page = page.replace("__BUNDLE_DATA__", encoded(data)).replace("__BUNDLE_MODULES__", encoded(modules))
page = page.replace("__BOOTSTRAP__", (ROOT / "bootstrap.mjs").read_text())
output = ROOT / "index.html"
output.write_text(page, encoding="utf-8")
record = {
    "schema": "earned-turn-browser-manifest/v1",
    "source_hash": source_hash,
    "execution_source_hash": execution_hash,
    "execution_manifest": execution_manifest,
    "modules": manifest,
    "presentation": {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ("template.html", "styles.css", "build_demo.py")
    },
    "output": output.name,
    "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    "bytes": output.stat().st_size,
    "research_embedded": recorded is not None,
}
(ROOT / "BUNDLE_MANIFEST.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({key: record[key] for key in ("source_hash", "output_sha256", "bytes", "research_embedded")}))
