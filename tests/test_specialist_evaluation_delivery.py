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
    workflow = yaml.safe_load((ROOT / ".github/workflows/specialist-evaluation.yml").read_text())
    job = workflow["jobs"]["evaluation"]
    assert "if" not in job and not job.get("continue-on-error")
    checks = [
        step for step in job["steps"] if step.get("run") == "python tests/browser/test_specialist_evaluation_browser.py"
    ]
    assert len(checks) == 1
    check = checks[0]
    assert "if" not in check and not check.get("continue-on-error")
    assert check["env"]["AXE_SCRIPT"] == "tests/browser/node_modules/axe-core/axe.min.js"
    assert check["env"]["EVALUATION_SCREENSHOTS"] == "evidence/specialist-evaluation"
    assert workflow["permissions"] == {"contents": "read"}
    for step in job["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
