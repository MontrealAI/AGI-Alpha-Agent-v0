# SPDX-License-Identifier: Apache-2.0
"""Prevent publication from bypassing packaged and public flagship acceptance."""

from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_flagship_qualifies_the_packaged_site_and_public_origin() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/agent-release.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    gallery = jobs["gallery"]
    steps = gallery["steps"]
    local = next(step for step in steps if "scripts.validate_successor_alpha" in step.get("run", ""))
    assert "--site site --output evidence/successor-alpha" in local["run"]
    assert "--axe-script tests/browser/node_modules/axe-core/axe.min.js" in local["run"]
    assert "if" not in local and "continue-on-error" not in local
    archive = next(step for step in steps if step.get("name") == "Archive the exact tested full site")
    assert steps.index(local) < steps.index(archive)
    assert set(gallery["strategy"]["matrix"]["assets"]) == {"minimal", "full"}
    assert "gallery" in jobs["package"]["needs"]
    public = next(step for step in jobs["pages"]["steps"] if "scripts.validate_successor_alpha" in step.get("run", ""))
    assert "--site site --url https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/alpha/" in public["run"]
    assert "--output evidence/public-pages/successor-alpha" in public["run"]
    assert "--axe-script tests/browser/node_modules/axe-core/axe.min.js" in public["run"]
    assert "if" not in public and "continue-on-error" not in public
    assert {"pages", "package"}.issubset(jobs["publish"]["needs"])
    assert "release/successor-1.34.0-20261018" in workflow["on"]["push"]["branches"]


def test_computer_use_candidate_runs_complete_acceptance_before_merge() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/agent-release.yml").read_text(), Loader=yaml.BaseLoader)
    assert "codex/flagship-computer-strategy-loop-20261018" in workflow["on"]["push"]["branches"]
