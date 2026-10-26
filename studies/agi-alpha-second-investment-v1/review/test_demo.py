#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independently check the saved demo against frozen evidence; no campaigns run.

The JavaScript harness executes the actual inline script with a deliberately small
DOM. It checks application behavior, not browser rendering or layout.
"""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import resource
import subprocess
import tempfile
import time
from urllib.parse import unquote, urlsplit


class Document(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes = [{"tag": "document", "attrs": {}, "children": [], "parent": None}]
        self.stack = [0]

    def handle_starttag(self, tag, attrs):
        index = len(self.nodes)
        self.nodes.append({"tag": tag, "attrs": dict(attrs), "children": [], "parent": self.stack[-1]})
        self.nodes[self.stack[-1]]["children"].append(index)
        if tag not in self.VOID:
            self.stack.append(index)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.nodes[self.stack[index]]["tag"] == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        self.nodes[self.stack[-1]]["children"].append(data)

    def text(self, index):
        return "".join(self.text(x) if isinstance(x, int) else x for x in self.nodes[index]["children"])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=Path("publication/AGI_ALPHA_Second_Investment_Demo.html"))
    parser.add_argument("--out", type=Path, default=Path("review/demo-functional-results.json"))
    args = parser.parse_args()
    started = time.monotonic()
    cpu_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    root = Path(__file__).resolve().parents[1]
    html = (root / args.html).resolve()
    doc = Document()
    doc.feed(html.read_text())
    checks = []

    def check(name, passed, details=None):
        checks.append({"name": name, "passed": bool(passed), "details": details})

    ids = [node["attrs"]["id"] for node in doc.nodes if "id" in node["attrs"]]
    by_id = {node["attrs"]["id"]: i for i, node in enumerate(doc.nodes) if "id" in node["attrs"]}
    check("HTML IDs are unique", len(ids) == len(set(ids)), {"count": len(ids)})
    scripts = {key: doc.text(value) for key, value in by_id.items() if doc.nodes[value]["tag"] == "script"}
    data = json.loads(scripts["app-data"])
    files = json.loads(scripts["embedded-files"])
    summary_path = root / "market/results/primary-01/summary.json"
    representatives_path = root / "market/results/primary-01/predeclared-representatives.json"
    publication_path = root / "publication/publication-data.json"
    summary = json.loads(summary_path.read_text())
    frozen_representatives = json.loads(representatives_path.read_text())["worlds"]
    expected_representatives = []
    for world in frozen_representatives:
        paired = world["paired"]
        expected = {
            "cost_profile": world["costProfileId"], "policy": world["policyId"], "seed": world["seed"],
            "A": paired["arms"]["A"]["summary"], "B": paired["arms"]["B"]["summary"],
            "B_second": paired["arms"]["B"]["secondInvestment"], "causal": paired["causal"],
            "qualification": paired["qualification"],
        }
        for arm in ["A", "B"]:
            for history in ["balances", "cash", "bills", "invoices"]:
                expected[f"{arm}_{history}"] = paired["arms"][arm]["histories"][history]
        expected_representatives.append(expected)
    check("Embedded publication-data identity", data["publicationDataSHA256"] == sha(publication_path))
    check("Frozen grid has 80 groups and no actual receipts", len(summary["groups"]) == 80
          and summary["actualCustomerCollectionsCents"] == 0)

    # Check actual link destinations, not a hard-coded list of expected links.
    missing_links, external_links = [], []
    link_count = 0
    for node in doc.nodes:
        for attribute in ["href", "src"]:
            value = node["attrs"].get(attribute)
            if not value:
                continue
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc:
                external_links.append(value)
                continue
            link_count += 1
            if not parsed.path:
                if parsed.fragment and parsed.fragment not in by_id:
                    missing_links.append(value)
            elif not (html.parent / unquote(parsed.path)).resolve().exists():
                missing_links.append(value)
    check("Local HTML links and fragments resolve", not missing_links,
          {"checked": link_count, "missing": missing_links, "external_links": external_links})
    external_assets = [node["attrs"].get("src") for node in doc.nodes
                       if node["tag"] in ["script", "img", "iframe"] and node["attrs"].get("src")]
    check("No network-loaded scripts or media", not external_assets, external_assets)
    label_targets = {node["attrs"].get("for") for node in doc.nodes if node["tag"] == "label"}
    controls = [node for node in doc.nodes if node["tag"] in ["input", "select"]]
    check("All inputs and selectors have explicit labels", all(n["attrs"].get("id") in label_targets
          or n["attrs"].get("aria-label") for n in controls), {"controls": len(controls)})
    no_js = " ".join(doc.text(i) for i, n in enumerate(doc.nodes) if n["tag"] == "noscript")
    check("No-JS limitation is explicitly bilingual", "without JavaScript" in no_js and "sans JavaScript" in no_js)
    # Static fallback must itself give the actual negative result before any script runs.
    check("No-JS reference financial result is present", "Not financed" in doc.text(by_id["ledger-status"])
          and "103.85" in doc.text(by_id["ledger-delta"]) and doc.text(by_id["ledger-uses"]).strip() == "0")
    check("No-JS production outcomes remain present", all(package in html.read_text().split('<script')[0]
          for package in ["cryptography", "eth-account", "prometheus-client", "pydantic-settings", "pyyaml", "uvicorn"]))
    css = "\n".join(doc.text(i) for i, n in enumerate(doc.nodes) if n["tag"] == "style")
    check("Static 360px safeguards exist (not rendered layout)", all(term in css for term in [
        "@media(max-width:620px)", ".controls,.controls.two{grid-template-columns:1fr", ".calc-grid{grid-template-columns:",
        ".delivery-grid{grid-template-columns:1fr", ".table-scroll{overflow-x:auto", "min-width:0", "overflow-wrap:anywhere"
    ]), {"browser_rendered": False, "viewport_considered_px": 360})
    check("Keyboard focus and reduced-motion safeguards exist", ":focus-visible" in css
          and ".sr-only:focus" in css and "prefers-reduced-motion:reduce" in css)
    check("Both language visibility rules are explicit", "html[data-language=en] [lang=fr]" in css
          and "html[data-language=fr] [lang=en]" in css)

    fixture = {"root": str(root), "htmlSHA256": sha(html), "nodes": doc.nodes,
               "expectedGroups": summary["groups"], "expectedRepresentatives": expected_representatives,
               "expectedFileSources": {path: {"sha256": sha(root / path), "bytes": (root / path).stat().st_size}
                                       for path in files}}
    with tempfile.TemporaryDirectory(prefix="agi-alpha-demo-qa-") as temp:
        fixture_path = Path(temp) / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))
        command = ["node", str(root / "review/test_demo.cjs"), str(fixture_path)]
        ran = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        javascript = json.loads(ran.stdout)
    except json.JSONDecodeError:
        javascript = {"passed": False, "stdout": ran.stdout, "stderr": ran.stderr}
    cpu_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {
        "schema": "agi-alpha-demo-functional-qa/v1", "basis": "POST-EVALUATION PRESENTATION QA; no research reruns",
        "html": str(html.relative_to(root)), "html_sha256": sha(html), "html_bytes": html.stat().st_size,
        "test_sources": {"review/test_demo.py": sha(Path(__file__)), "review/test_demo.cjs": sha(root / "review/test_demo.cjs")},
        "frozen_reference_sources": {str(path.relative_to(root)): sha(path)
                                     for path in [summary_path, representatives_path, publication_path]},
        "static_checks": checks, "javascript": javascript, "javascript_exit_code": ran.returncode,
        "passed": all(item["passed"] for item in checks) and ran.returncode == 0 and javascript.get("passed", False),
        "elapsed_wall_seconds": time.monotonic() - started,
        "child_cpu_seconds": cpu_end.ru_utime + cpu_end.ru_stime - cpu_start.ru_utime - cpu_start.ru_stime,
        "actual_model_fees": None, "human_minutes": None,
        "limitations": ["Minimal DOM is not a browser; layout, painting, focus movement and screen-reader behavior were not rendered.",
                        "360px review is a static CSS inspection only.",
                        "No primary production campaign, market campaign or relocated reproduction was executed."]
    }
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"passed": report["passed"], "report": str(out.relative_to(root)),
                      "html_sha256": report["html_sha256"], "static_failures": [x for x in checks if not x["passed"]],
                      "javascript": javascript}, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
