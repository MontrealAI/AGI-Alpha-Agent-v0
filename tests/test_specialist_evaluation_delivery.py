# SPDX-License-Identifier: Apache-2.0
"""Guard exact source bindings and mandatory Specialist browser acceptance."""
from pathlib import Path
import base64
import hashlib
import json
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_generated_source_and_csp_bind_exact_bytes() -> None:
    manifest = json.loads((ROOT / "docs/successor/evaluate/sources.json").read_text())
    for name, value in manifest["sources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value, name
    assert (
        hashlib.sha256(json.dumps(manifest["sources"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        == manifest["sourceHash"]
    )
    page = (ROOT / "docs/successor/evaluate/index.html").read_text()
    assert "connect-src 'none'" in page
    for tag in ("script", "style"):
        match = re.search(rf"<{tag}>(.*?)</{tag}>", page, re.S)
        assert match is not None
        value = match.group(1)
        assert "sha256-" + base64.b64encode(hashlib.sha256(value.encode()).digest()).decode() in page
    assert manifest["sourceHash"] in page


def test_browser_gate_is_mandatory_and_has_pinned_tooling() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/successor-mission.yml").read_text())
    job = workflow["jobs"]["mission"]
    assert "if" not in job and not job.get("continue-on-error")
    checks = [
        step
        for step in job["steps"]
        if "python tests/browser/test_specialist_evaluation_browser.py" in step.get("run", "").splitlines()
    ]
    assert len(checks) == 1
    check = checks[0]
    assert "if" not in check and not check.get("continue-on-error")
    assert check["env"]["AXE_SCRIPT"] == "${{ github.workspace }}/tests/browser/node_modules/axe-core/axe.min.js"
    assert check["env"]["EVALUATION_SCREENSHOTS"] == "${{ github.workspace }}/discovery-screenshots/evaluation"
    assert workflow["permissions"] == {"contents": "read"}
    for step in job["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])


def test_evaluation_navigation_and_gallery_generation_are_additive() -> None:
    for relative in (
        "scripts/templates/alpha-discovery/index.html",
        "docs/successor/discover/index.html",
        "scripts/templates/successor-workbench/index.html",
        "docs/successor/work/index.html",
    ):
        page = (ROOT / relative).read_text()
        assert 'href="../evaluate/"' in page
        assert 'href="../mission/"' in page
    for relative in ("scripts/templates/portal.html", "docs/index.html"):
        page = (ROOT / relative).read_text()
        assert 'href="successor/evaluate/"' in page
        assert 'href="successor/work/"' in page
        assert 'href="successor/play/"' in page
    generator = (ROOT / "scripts/generate_gallery_html.py").read_text()
    assert '("generate_successor_mission", "generate_alpha_discovery", "generate_specialist_evaluation")' in generator
    assert '("successor", "evaluate", "index.html")' in generator
    assert not (ROOT / ".github/workflows/specialist-evaluation.yml").exists()
    for relative, prefix in (
        ("docs/service-worker.js", "./"),
        ("docs/assets/service-worker.js", "../"),
        ("docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js", "../../../"),
    ):
        script = (ROOT / relative).read_text()
        assert json.dumps(prefix + "successor/evaluate/index.html") in script
        assert json.dumps(prefix + "successor/discover/index.html") in script
