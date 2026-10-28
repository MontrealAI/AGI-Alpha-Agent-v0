# SPDX-License-Identifier: Apache-2.0
"""Build one source-bound reading edition; require completed evidence inputs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise SystemExit(f"Required evidence file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
                     + ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--regressions", type=Path, required=True)
    parser.add_argument("--quickstart", type=Path, required=True)
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    evidence = args.evidence.resolve()
    results_path = evidence / "evaluation/results.json"
    result = read_json(results_path)
    facts = read_json(args.facts)
    matrix = read_json(args.regressions)
    regression_rows = matrix.get("entries", matrix.get("regressions")) if isinstance(matrix, dict) else matrix
    gates = read_json(evidence / "downstream_gates.json")
    costs = read_json(evidence / "costs.json")
    manifest_path = evidence / "evaluation/task_manifest.json"
    manifest = read_json(manifest_path)
    for field in ("implementation", "validation", "comparators", "chain", "source_status", "evidence_index"):
        if not facts.get(field):
            raise SystemExit(f"Required publication fact missing: {field}")
    if not args.quickstart.is_file():
        raise SystemExit("Tested quickstart must be supplied as a real file")
    expected = [f"R{i:02}" for i in range(1, 38)]
    if [r["id"] for r in regression_rows] != expected:
        raise SystemExit("Regression matrix must contain R01 through R37 exactly once in order")
    for row in regression_rows:
        if row["status"] not in {"PASS", "FAIL", "NOT RUN", "BLOCKED", "NOT APPLICABLE"}:
            raise SystemExit(f"Invalid regression status: {row['id']}")
        if not row.get("status_reason") or "Extraction only" in row["status_reason"]:
            raise SystemExit(f"Regression applicability not assessed: {row['id']}")
    if result["task_manifest_sha256"] != sha(manifest_path):
        raise SystemExit("Results do not bind the supplied task manifest")
    rows = result["rows"]
    summary = result["summary"]
    if len(rows) != summary["case_count"] or sum(r["correct"] for r in rows) != summary["correct"]:
        raise SystemExit("Result counters disagree")
    if len(rows) != 24 or len(result["validation"]) != 6:
        raise SystemExit("Unexpected frozen confirmation denominator")
    financial = costs["financial"]
    for field in ("real_revenue_usd", "real_collections_usd", "simulated_revenue_usd", "simulated_collections_usd", "earned_profit_investment_usd"):
        if financial[field] != 0:
            raise SystemExit("Narrative's zero-commerce scope no longer matches its evidence")
    if any(c["decision"] != "HOLD" for c in gates["candidates"] if "decision" in c):
        raise SystemExit("Downstream status changed; revise narrative before rebuilding")
    family_rows = []
    for family in sorted({r["family"] for r in rows}):
        group = [r for r in rows if r["family"] == family]
        family_rows.append([family.replace("_", " "), len(group), sum(r["correct"] for r in group),
                            sum(r["instrument"]["status"] == "optimal" for r in group),
                            sum(r["oracle"]["status"] == "optimal" for r in group),
                            sum(r["static"]["status"] == "optimal" for r in group)])
    exact = f"{summary['correct']}/{summary['case_count']}"
    abstract = (f"The instrument agrees with an independent exact adaptive control on {exact} frozen cases; "
                f"{summary['instrument_solved']} cases admit verified policies and the remaining cases are correctly classified within the finite model. "
                f"The static control solves {summary['static_solved']}/{summary['case_count']}, while all six malformed-input probes are refused.")
    measurements = table(["Designed family", "Cases", "Correct", "Instrument feasible", "Adaptive control feasible", "Static feasible"], family_rows)
    elapsed = {key: sum(r["seconds"][key] for r in rows) for key in ("instrument_wall", "instrument_cpu", "oracle_wall", "oracle_cpu")}
    measurement_text = (f"The frozen pass yields **{exact} correct finite decisions**, with **{summary['instrument_solved']}/{summary['case_count']} verified feasible policies** "
                        f"and **{summary['case_count']-summary['instrument_solved']}/{summary['case_count']} infeasible cases**. "
                        f"The exact adaptive control ties all {summary['case_count']} decisions and optimal costs. "
                        f"The static control is feasible in {summary['static_solved']}/{summary['case_count']} cases.\n\n" + measurements + "\n\n" +
                        f"Across the 24 sequential calls, instrument wall time totals {elapsed['instrument_wall']:.6f} s and CPU time {elapsed['instrument_cpu']:.6f} s; "
                        f"the independent adaptive control totals {elapsed['oracle_wall']:.6f} s wall and {elapsed['oracle_cpu']:.6f} s CPU. "
                        "These descriptive local measurements are not complete construction costs or a normalized model-efficiency benchmark. "
                        "The four cases where contingent feasibility exceeds static feasibility are designed mechanism tests, not four independent scientific discoveries.\n\n" +
                        f"All {summary['validation_rejected']}/6 invalid-input probes are refused under the declared validation check. "
                        "The complete case-by-case policies, rejected inputs and counterfactual ablation audits remain in `evidence/evaluation/results.json`. "
                        "A failed altered-model policy is evaluated against the original case, not accepted under its relaxed assumptions.")
    comparison_text = table(["Comparison", "Observed status", "Scope and evidence"], [[r["name"], r["status"], r["evidence"]] for r in facts["comparators"]])
    downstream = table(["Possibility", "Proposed missing means", "Decision / missing evidence"],
                       [[c["domain"], c["missing_means"], c["status"]] for c in gates["candidates"]])
    counts = Counter(r["status"] for r in regression_rows)
    regression_text = "Status totals: " + "; ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + ".\n\n"
    regression_text += ("Common source for all entries: the pinned base repository and additive `contrib/discovery_means_v1` source identified above. "
                        "Each entry retains its own applicability reason, including partial instrument/governance evidence. "
                        "The machine-readable matrix additionally retains complete target, procedure and receipt fields. "
                        "NOT RUN does not convert any requirement to NOT APPLICABLE.\n\n")
    for r in regression_rows:
        regression_text += (f"## {r['id']} · {r['title'].title()}\n\n"
                            f"**Intent.** {r['requirement_exact']} **Expected.** {r['expected_exact']}\n\n"
                            f"**Status: {r['status']}.** {r['status_reason']}\n\n")
        if r['id'] in {'R34', 'R35'}:
            regression_text += "**Partial evidence.** " + str(r.get("actual_result", "")) + "\n\n"
    identity = (f"Base repository commit: `{manifest.get('base_commit', '12770c22b4a9f90f2013bbfb64242f912ba5071e')}`. "
                f"Instrument SHA-256: `{result['instrument_sha256']}`. "
                f"Frozen task manifest SHA-256: `{result['task_manifest_sha256']}`. "
                f"Evaluation result SHA-256: `{sha(results_path)}`.\n\n" + facts["source_status"])
    example_source = here.parents[2] / "contrib/discovery_means_v1/examples/adaptive.json"
    from example_figure import build as build_example
    build_example(example_source, here / "adaptive-example.svg")
    replacements = {
        "ABSTRACT_RESULT": abstract,
        "IMPLEMENTATION": facts["implementation"],
        "RESULTS": measurement_text,
        "COMPARATORS": comparison_text,
        "VALIDATION": facts["validation"],
        "DOWNSTREAM": downstream,
        "QUICKSTART": args.quickstart.read_text(encoding="utf-8"),
        "SOURCE_IDENTITY": identity,
        "CHAIN_STATUS": table(["Link", "Status and scope"], [[r["link"], r["status"]] for r in facts["chain"]]),
        "REGRESSIONS": regression_text,
        "EVIDENCE_INDEX": facts["evidence_index"],
    }
    source = (here / "narrative.md.in").read_text(encoding="utf-8")
    for key, value in replacements.items():
        source = source.replace(f"@@{key}@@", value)
    if re.findall(r"@@(?!(?:ARCHITECTURE|EXAMPLE))[A-Z_]+@@", source):
        raise SystemExit("Unresolved publication placeholders")
    caption = "The installed add-on produces checked policies and records source-bound evidence through native signed research custody. The bundle remains paused-uncertain; production authority and the general native executor are not qualified."
    example_caption = "Authored executed example from adaptive.json. The first screen selects a branch-specific test; every possible observation is represented. Worst path cost is 3 query units, versus 4 for the static left-plus-right portfolio. Query units are declared resources, not currency or billed research cost."
    markdown = source.replace("@@ARCHITECTURE@@", f"![{caption}](architecture.svg)").replace("@@EXAMPLE@@", f"![{example_caption}](adaptive-example.svg)")
    (here / "AGI_ALPHA_Discovery_Means_v1.md").write_text(markdown, encoding="utf-8")
    latex_md = source.replace("@@ARCHITECTURE@@", f"![{caption}](architecture.pdf){{width=90%}}").replace("@@EXAMPLE@@", f"![{example_caption}](adaptive-example.pdf){{width=90%}}")
    (here / "_latex.md").write_text(latex_md, encoding="utf-8")
    subprocess.run(["pandoc", "_latex.md", "--from=markdown", "--to=latex", "--standalone", "--citeproc", "--bibliography=references.bib", "--template=template.tex", "--no-highlight", "-o", "AGI_ALPHA_Discovery_Means_v1.tex"], cwd=here, check=True)
    tex_path = here / "AGI_ALPHA_Discovery_Means_v1.tex"
    tex_source = tex_path.read_text(encoding="utf-8")
    tex_source = re.sub(r"\\texttt\{([0-9a-f]{40,64})\}", lambda m: "\\nolinkurl{" + m.group(1) + "}", tex_source)
    frontier_start = tex_source.index("\\hypertarget{the-frontier-left-by-this-construction}")
    table_start = tex_source.index("\\begin{longtable}", frontier_start)
    table_body = tex_source.index("\\toprule", table_start)
    table_spec = r"\begin{longtable}{>{\raggedright\arraybackslash}p{.29\linewidth}@{\hspace{16pt}}>{\raggedright\arraybackslash}p{.64\linewidth}}" + "\n"
    tex_source = tex_source[:table_start] + table_spec + tex_source[table_body:]
    tex_path.write_text(tex_source, encoding="utf-8")
    body = subprocess.run(["pandoc", "AGI_ALPHA_Discovery_Means_v1.md", "--from=markdown", "--to=html5", "--citeproc", "--bibliography=references.bib", "--mathml", "--no-highlight"], cwd=here, check=True, capture_output=True, text=True).stdout
    body = re.sub(r'<p>(<math display="block".*?</math>)</p>', r'<div class="math-scroll" tabindex="0" aria-label="Scrollable displayed equation">\1</div>', body, flags=re.S)
    svg = (here / "architecture.svg").read_text(encoding="utf-8")
    body = re.sub(r'<img src="architecture\.svg"[^>]*>', svg, body)
    example_svg = (here / "adaptive-example.svg").read_text(encoding="utf-8")
    body = re.sub(r'<img src="adaptive-example\.svg"[^>]*>', example_svg, body)
    headings = re.findall(r'<h1 id="([^"]+)">(.*?)</h1>', body)
    nav = " ".join(f'<a href="#{html.escape(key)}">{re.sub("<[^>]+>", "", name)}</a>' for key, name in headings)
    css = (here / "reader.css").read_text(encoding="utf-8")
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>AGI ALPHA FLYWHEEL · Discovery Means v1</title><style>' + css + '</style></head><body>'
            '<header><p>TRANSFORMATIONAL INTELLIGENCE / RESEARCH EDITION v1</p><h1>AGI ALPHA FLYWHEEL</h1>'
            '<p class="subtitle">THE ENTERPRISE THAT INVENTS THE MEANS OF DISCOVERING ITS NEXT ECONOMY</p>'
            '<p class="byline">Vincent Boucher<br>President of MONTREAL.AI<br>28 October 2026</p></header>'
            '<nav aria-label="Reading navigation"><a href="AGI_ALPHA_Discovery_Means_v1.pdf">Read the PDF</a>'
            '<a href="AGI_ALPHA_Discovery_Means_v1.tex">LaTeX source</a>' + nav + '</nav><main id="reading-edition">' + body + '</main>'
            '<footer>Source-bound local research edition. No canonical release or public deployment is asserted. '
            'All experimental, financial and authority limits are part of the result.</footer></body></html>')
    (here / "Browser_Edition.html").write_text(page, encoding="utf-8")
    if args.pdf:
        subprocess.run(["inkscape", str(here / "architecture.svg"), "--export-type=pdf", "--export-filename=" + str(here / "architecture.pdf")], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["inkscape", str(here / "adaptive-example.svg"), "--export-type=pdf", "--export-filename=" + str(here / "adaptive-example.pdf")], check=True, stdout=subprocess.DEVNULL)
        with (here / "xelatex-build.log").open("w", encoding="utf-8") as log:
            for _ in range(2):
                subprocess.run(["xelatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "AGI_ALPHA_Discovery_Means_v1.tex"], cwd=here, stdout=log, stderr=subprocess.STDOUT, check=True)
    inputs = [example_source, results_path, args.facts, args.regressions, args.quickstart, manifest_path, evidence / "costs.json", evidence / "downstream_gates.json"]
    outputs = [here / "AGI_ALPHA_Discovery_Means_v1.md", here / "AGI_ALPHA_Discovery_Means_v1.tex", here / "Browser_Edition.html"]
    if args.pdf:
        outputs.append(here / "AGI_ALPHA_Discovery_Means_v1.pdf")
    receipt = {"scope": "Publication rendering and evidence identity; visual inspection is a separate receipt", "inputs": {str(p): sha(p) for p in inputs}, "outputs": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in outputs}}
    (here / "build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt["outputs"], indent=2))


if __name__ == "__main__":
    main()
