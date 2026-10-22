# SPDX-License-Identifier: Apache-2.0
"""Reproduce the exact portable bundle and protect its separate acceptance lane."""

from __future__ import annotations

import ast
import importlib.util
import hashlib
import json
import re
import stat
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def capability_checkout_paths() -> list[str]:
    """All raw-hashed inputs and retained generated identities need LF checkouts."""
    manifest = json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text())
    return sorted(
        set(manifest["sources"])
        | {
            "examples/successor-capability/discovery-lab-reproduce.mjs",
            "docs/successor/capabilities/index.html",
            "docs/successor/capabilities/sources.json",
            "docs/alpha_factory_v1/demos/successor/capabilities/index.html",
            "docs/alpha_factory_v1/demos/successor/capabilities/sources.json",
            "docs/service-worker.js",
            "docs/assets/service-worker.js",
            "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
        }
    )


def test_every_capability_byte_hashed_input_has_explicit_lf_checkout_attributes(tmp_path: Path) -> None:
    paths = capability_checkout_paths()
    shutil.copyfile(ROOT / ".gitattributes", tmp_path / ".gitattributes")
    subprocess.run(["git", "-C", str(tmp_path), "init", "--quiet"], capture_output=True, check=True)
    result = subprocess.run(
        ["git", "-C", str(tmp_path), "check-attr", "--stdin", "text", "eol"],
        input="\n".join(paths) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout.splitlines() == [line for name in paths for line in (f"{name}: text: set", f"{name}: eol: lf")]


def test_actual_crlf_checkout_preserves_capability_raw_bytes_and_catalog_hashes(tmp_path: Path) -> None:
    """A real Git checkout must retain raw bytes even with autocrlf enabled."""
    source, checkout = tmp_path / "source", tmp_path / "checkout"
    source.mkdir()
    checkout.mkdir()
    paths = capability_checkout_paths()
    for name in [".gitattributes", *paths]:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (source / "checkout-control.txt").write_bytes(b"ordinary unpinned control\n")
    for arguments in (
        ("init", "--quiet"),
        ("config", "core.autocrlf", "true"),
        ("config", "core.eol", "crlf"),
        ("add", ".gitattributes", *paths, "checkout-control.txt"),
        ("checkout-index", "--all", "--force", "--prefix=" + str(checkout) + "/"),
    ):
        subprocess.run(["git", "-C", str(source), *arguments], capture_output=True, check=True)
    assert (checkout / "checkout-control.txt").read_bytes() == b"ordinary unpinned control\r\n"
    for name in paths:
        assert (checkout / name).read_bytes() == (ROOT / name).read_bytes(), name
    catalog = json.loads((checkout / "docs/successor/capabilities/sources.json").read_bytes())
    for name, expected in catalog["sources"].items():
        assert hashlib.sha256((checkout / name).read_bytes()).hexdigest() == expected, name
    encoded = json.dumps(catalog["sources"], sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == catalog["sourceHash"]


def test_native_fleet_return_cannot_be_skipped_by_the_required_hosted_journey() -> None:
    """An actual immutable public checkout and mandatory mode guard the extra acceptance."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/successor-capability.yml").read_text())
    steps = workflow["jobs"]["capability"]["steps"]
    checkouts = [step for step in steps if step.get("with", {}).get("repository") == "MontrealAI/AGI-Fleet-Linux"]
    assert len(checkouts) == 1
    checkout = checkouts[0]
    assert checkout["uses"] == "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd"
    assert checkout["with"]["ref"] == "0dd352fdd2b1af00bc8358e0ac7f96682fd6f796"
    assert checkout["with"]["persist-credentials"] is False
    assert "if" not in checkout and not checkout.get("continue-on-error")
    journey = next(
        step for step in steps if "python tests/browser/test_discovery_lab_continuation.py" in step.get("run", "")
    )
    assert journey["env"]["DISCOVERY_FLEET_ROOT"].endswith("/" + checkout["with"]["path"])
    assert journey["env"]["DISCOVERY_FLEET_REQUIRED"] == "1"
    assert "if" not in journey and not journey.get("continue-on-error")
    events = workflow.get("on", workflow.get(True))
    for name in (
        "fleet_receipt_native.mjs",
        "fleet_module_boundary.mjs",
        "fleet_module_boundary.test.mjs",
        "fleet_git_metadata.mjs",
        "fleet_git_metadata.test.mjs",
    ):
        assert "tests/browser/" + name in events["pull_request"]["paths"]
    node_step = next(step["run"] for step in steps if "node --test" in step.get("run", ""))
    assert "tests/browser/fleet_module_boundary.test.mjs" in node_step
    assert "tests/browser/fleet_git_metadata.test.mjs" in node_step


def test_native_source_helper_refuses_unsafe_metadata_without_installing_or_running_commands(tmp_path: Path) -> None:
    """Inert configuration values exercise refusal before Git or source import."""
    node = shutil.which("node")
    assert node is not None
    request, mission = tmp_path / "request.json", tmp_path / "mission.json"
    request.write_text("{}")
    mission.write_text("{}")
    for name, config, expected in [
        (
            "filter",
            '[core]\n bare = false\n[filter "unavailable"]\n smudge = unavailable-value\n',
            "configuration section",
        ),
        ("include", "[core]\n bare = false\n[include]\n path = unsafe.cfg\n", "configuration section"),
        ("fsmonitor", "[core]\n bare = false\n fsmonitor = unavailable-value\n", "Git configuration is refused"),
        ("promisor", '[core]\n bare = false\n[remote "origin"]\n promisor = true\n', "Git configuration is refused"),
        ("partial", "[core]\n bare = false\n[extensions]\n partialClone = origin\n", "Git configuration is refused"),
        (
            "uploadpack",
            '[core]\n bare = false\n[remote "origin"]\n uploadpack = unavailable-value\n',
            "Git configuration is refused",
        ),
    ]:
        root = tmp_path / name
        (root / ".git").mkdir(parents=True)
        (root / ".git/config").write_text(config)
        result = subprocess.run(
            [
                node,
                str(ROOT / "tests/browser/fleet_receipt_native.mjs"),
                str(root),
                str(mission),
                str(request),
                str(tmp_path / (name + "-output")),
            ],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        assert result.returncode != 0 and expected in result.stderr


def test_native_source_helper_refuses_non_admitted_worktree_metadata(tmp_path: Path) -> None:
    """Only inert local metadata is supplied; refusal precedes any Git object read."""
    node = shutil.which("node")
    assert node is not None
    for kind, expected in [
        ("active-worktree", "worktree configuration is refused"),
        ("bare-worktree-key", "worktree configuration is refused"),
        ("commondir", "common Git directory"),
        ("worktree-directory", "metadata must be regular"),
        ("oversize-worktree", "Bounded regular file"),
    ]:
        root = tmp_path / kind
        directory = root / ".git"
        directory.mkdir(parents=True)
        config = "[core]\n bare = false\n"
        if kind == "active-worktree":
            config += "[extensions]\n worktreeConfig = false\n worktreeConfig = true\n"
        elif kind == "bare-worktree-key":
            config += "[extensions]\n worktreeConfig\n"
        (directory / "config").write_text(config)
        if kind == "commondir":
            (directory / "commondir").write_text("../unavailable\n")
        elif kind == "worktree-directory":
            (directory / "config.worktree").mkdir()
        else:
            (directory / "config.worktree").write_text(
                "#" + "x" * 128000 if kind == "oversize-worktree" else "[core]\n sparseCheckout = false\n"
            )
        mission, request = tmp_path / "mission.json", tmp_path / "request.json"
        mission.write_text("{}")
        request.write_text("{}")
        result = subprocess.run(
            [
                node,
                str(ROOT / "tests/browser/fleet_receipt_native.mjs"),
                str(root),
                str(mission),
                str(request),
                str(root / "absent-output"),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode != 0 and expected in result.stderr, kind


def test_native_browser_attack_bank_is_predeclared_and_not_selected_by_the_producer() -> None:
    """Inspect the fixed acceptance inventory as inert syntax, without loading browser code."""
    tree = ast.parse((ROOT / "tests/browser/test_discovery_lab_continuation.py").read_text())
    declaration = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "FLEET_VARIANTS" for target in node.targets)
    )
    assert ast.literal_eval(declaration.value) == (
        "executor",
        "runtime",
        "elapsed",
        "memory",
        "outcome",
        "raw-framing",
        "receipt-framing",
        "request-framing",
        "source-repository",
        "forged-authority",
        "swapped-mission",
    )
    acceptance = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "fleet_return")
    loops = [node for node in ast.walk(acceptance) if isinstance(node, ast.For)]
    assert any(isinstance(node.iter, ast.Name) and node.iter.id == "FLEET_VARIANTS" for node in loops)


def test_both_native_requests_are_actual_ui_downloads_with_one_pre_fleet_history() -> None:
    """Protect the two alternatives consumed from one authenticated browser artifact."""
    source = (ROOT / "tests/browser/test_discovery_lab_continuation.py").read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "fleet_return")
    downloads = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "download_request"
    ]
    assert [ast.literal_eval(node.args[2]) for node in downloads] == ["USDC", "AGIALPHA"]
    journal = next(
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "request_exports" for target in node.targets)
    )

    def fields(node: ast.expr) -> dict[str, ast.expr]:
        assert isinstance(node, ast.Dict)
        result = {}
        for key, value in zip(node.keys, node.values):
            assert key is not None
            name = ast.literal_eval(key)
            assert isinstance(name, str) and name not in result
            result[name] = value
        return result

    entries = fields(journal)
    assert {"missionId", "campaignDigest", "sourceHash", "pageSha256", "workspace", "requests"} <= entries.keys()
    assert fields(entries["requests"]).keys() == {"manager-usdc", "jobs-agialpha"}
    assert {"file", "sha256", "jobsFile", "jobsSha256", "revision", "eventPrefix", "head"} <= fields(
        entries["workspace"]
    ).keys()
    assert "jobs_workspace_path.read_bytes() == workspace_path.read_bytes()" in source
    assert '"browser-native-requests.json"' in source and '"jobs-browser-request.json"' in source


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_portable_bundle_reproduces_and_gallery_preserves_exact_bytes() -> None:
    manifest = json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text())
    with tempfile.TemporaryDirectory(prefix="capability-delivery-") as directory:
        isolated = Path(directory)
        for name in manifest["sources"]:
            target = isolated / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        load_script("generate_successor_capability").build(isolated)
        for name in ("index.html", "sources.json"):
            assert (isolated / "docs/successor/capabilities" / name).read_bytes() == (
                ROOT / "docs/successor/capabilities" / name
            ).read_bytes(), name
        page = isolated / "docs/successor/capabilities/index.html"
        original = page.read_bytes()
        load_script("generate_gallery_html").insert_back_link([page])
        assert page.read_bytes() == original


def test_acceptance_is_mandatory_read_only_and_retains_evidence() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/successor-capability.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["group"].startswith("capability-")
    # Standalone and reusable release invocations must not cancel one another.
    assert "${{ github.workflow }}" in workflow["concurrency"]["group"]
    job = workflow["jobs"]["capability"]
    assert job["if"] == "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"
    assert job["needs"] == "paper-scope"
    assert workflow["jobs"]["paper-scope"]["uses"] == "./.github/workflows/paper-scope.yml"
    assert not job.get("continue-on-error")
    steps = job["steps"]
    for step in steps:
        if "uses" in step:
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
    commands = [
        "node --test examples/successor-capability/*.test.mjs",
        "python scripts/generate_successor_capability.py",
        "git diff --exit-code -- docs/successor/capabilities",
        "python tests/browser/test_successor_capability_browser.py",
    ]
    for command in commands:
        matches = [step for step in steps if command in step.get("run", "")]
        assert len(matches) == 1
        assert "if" not in matches[0] and not matches[0].get("continue-on-error")
    browser = next(step for step in steps if commands[-1] in step.get("run", ""))
    assert browser["env"]["AXE_SCRIPT"].endswith("/tests/browser/node_modules/axe-core/axe.min.js")
    retained = {
        commands[0]: "node.log",
        "tests/test_successor_capability_delivery.py -q": "delivery.log",
        "python -m mypy --strict": "typing.log",
        commands[-1]: "v1-browser.log",
        "python tests/browser/test_out_evolve_browser.py": "out-evolve-browser.log",
        "python tests/browser/test_out_execute_browser.py": "out-execute-browser.log",
        "node examples/successor-capability/out-execute/reproduce.mjs": "out-execute-study.log",
        "python tests/browser/test_successor_capability_accessibility.py": "accessibility-review.log",
    }
    for command, log in retained.items():
        step = next(step for step in steps if command in step.get("run", ""))
        assert "set -o pipefail" in step["run"]
        assert f"tee capability-evidence/logs/{log}" in step["run"]
        assert "if" not in step and not step.get("continue-on-error")
    typing = next(step["run"] for step in steps if "python -m mypy --strict" in step.get("run", ""))
    assert "tests/browser/out_evolve_recovery.py" in typing
    assert "tests/browser/test_out_execute_browser.py" in typing
    events = workflow.get("on", workflow.get(True))
    assert "tests/browser/out_evolve_recovery.py" in events["pull_request"]["paths"]
    assert "tests/browser/test_out_execute_browser.py" in events["pull_request"]["paths"]
    # This data file is consumed executable input in the generated browser bundle.
    assert "docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json" in events["pull_request"]["paths"]
    assert "workflow_call" in events
    node_step = next(step["run"] for step in steps if "node --test" in step.get("run", ""))
    assert "examples/successor-capability/out-execute/*.test.mjs" in node_step
    uploader = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert uploader["if"] == "always()"
    assert uploader["with"]["if-no-files-found"] == "error"


def test_release_packaging_requires_the_same_complete_capability_gate() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["successor-capability"]
    assert job == {
        "if": "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}",
        "needs": ["paper-scope", "publication-preflight"],
        "uses": "./.github/workflows/successor-capability.yml",
    }
    package = workflow["jobs"]["package"]
    assert "successor-capability" in package["needs"]
    assert "style-advisory" not in package["needs"]
    assert package["if"] == "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"
    assert not package.get("continue-on-error")
    download = next(step for step in package["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
    # Keep advisory formatting out without excluding substantive acceptance evidence.
    assert (
        download["with"]["pattern"] == "!{historical-ci,release-package,public-pages,github-pages,advisory-formatting}*"
    )
    assert download["with"]["digest-mismatch"] == "error"


@pytest.mark.parametrize(
    "mutation", ["advisory-evidence", "capability-evidence", "capability-gate", "digest", "advisory-gate"]
)
def test_release_evidence_contract_rejects_policy_regressions(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())
    package = workflow["jobs"]["package"]
    download = next(step for step in package["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
    if mutation == "advisory-evidence":
        download["with"]["pattern"] = download["with"]["pattern"].replace(",advisory-formatting", "")
    elif mutation == "capability-evidence":
        download["with"]["pattern"] = download["with"]["pattern"].replace("}*", ",successor-capability}*")
    elif mutation == "capability-gate":
        package["needs"].remove("successor-capability")
    elif mutation == "digest":
        download["with"]["digest-mismatch"] = "warn"
    else:
        package["needs"].append("style-advisory")
    monkeypatch.setattr(yaml, "safe_load", lambda _source: workflow)
    with pytest.raises(AssertionError):
        test_release_packaging_requires_the_same_complete_capability_gate()


def test_retained_authored_study_is_bound_to_installed_source_and_keeps_counterbaselines() -> None:
    record = json.loads((ROOT / "docs/agent/release-evidence/out-execute-authored-study-20261021.json").read_text())
    summary = record["summary"]
    assert record["scope"] == "local-authored-finite-study-not-release-acceptance"
    assert summary["manuscriptCompanionReproduced"] is False
    for group in ("compilerSources", "checkerSources"):
        for path, expected in summary["source"][group].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    for path, expected in record["studyHarnessSources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    assert summary["snapshots"] == summary["matches"] == 576
    assert summary["semanticStops"] == 160 != summary["manuscriptClaimCounts"]["semanticStops"]
    assert summary["executionWork"] == summary["matchedIncrementalWork"]
    assert summary["identicalInputControl"]["fixedSecond"] < summary["identicalInputControl"]["boundarySecond"]
    assert summary["localArchiveReopenAudit"]["profileComparisons"] > 0
    assert len(record["retainedFixtureSha256"]) == summary["fixtures"] == 64


# These fixtures use only ordinary owned Git checkouts and data-only old bodies.
# The retained parent reproducer is never executed.
def _refresh_copy(tmp_path: Path) -> Path:
    root = tmp_path / "checkout"
    for name in capability_checkout_paths():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes().replace(b"\n", b"\r\n"))
    return root


def _git(root: Path, *arguments: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, check=True).stdout


def test_existing_parent_to_lf_attributes_checkout_has_explicit_backed_up_repair(tmp_path: Path) -> None:
    """A normal upgrade leaves stale raw CRLF despite clean Git status and LF attributes."""
    helper = load_script("refresh_capability_checkout")
    paths = capability_checkout_paths()
    fixture = json.loads((ROOT / "tests/fixtures/capability-checkout-parent.json").read_bytes())
    assert fixture["sourceCommit"] == "87a003d23d3093edac3747ee1f9da292c6159515"
    assert fixture["sourceTree"] == "ffa3d663519e713eca31a9840b8bf6816e53e12a"
    source, checkout = tmp_path / "source", tmp_path / "checkout"
    source.mkdir()
    controls = ["docs/Out_Execute.tex", "docs/Out_Execute.pdf"]
    for name in [*paths, *controls]:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    (source / "unpinned-control.txt").write_bytes(b"ordinary control\n")
    for name, entry in fixture["files"].items():
        raw = entry["text"].encode()
        assert len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"]
        (source / name).write_bytes(raw)
    for arguments in (
        ("init", "--quiet"),
        ("config", "user.name", "Owned test"),
        ("config", "user.email", "owned-test@example.invalid"),
        ("config", "commit.gpgsign", "false"),
        ("add", "."),
        ("commit", "--quiet", "-m", "Exact old attribute and reproducer bodies"),
    ):
        _git(source, *arguments)
    parent = _git(source, "rev-parse", "HEAD").decode().strip()
    for name in fixture["files"]:
        (source / name).write_bytes((ROOT / name).read_bytes())
    _git(source, "add", ".")
    _git(source, "commit", "--quiet", "-m", "Reviewed LF attribute transition")
    target = _git(source, "rev-parse", "HEAD").decode().strip()
    subprocess.run(
        ["git", "clone", "--quiet", "--local", "--no-checkout", str(source), str(checkout)],
        capture_output=True,
        check=True,
    )
    _git(checkout, "config", "core.autocrlf", "true")
    _git(checkout, "config", "core.eol", "crlf")
    _git(checkout, "checkout", "--quiet", "--detach", parent)
    _git(checkout, "checkout", "--quiet", "--detach", target)
    assert _git(checkout, "status", "--porcelain") == b""
    (checkout / "private-staged.txt").write_bytes(b"private staged content\n")
    _git(checkout, "add", "private-staged.txt")
    originals = {name: (checkout / name).read_bytes() for name in paths}
    modes = {name: stat.S_IMODE((checkout / name).stat().st_mode) for name in paths}
    unchanged = {
        name: (checkout / name).read_bytes()
        for name in [*controls, "unpinned-control.txt", "private-staged.txt", ".git/index", ".git/config"]
    }
    assert unchanged["unpinned-control.txt"] == b"ordinary control\r\n"
    assert sum(b"\r\n" in raw for raw in originals.values()) == 47
    catalog = json.loads(originals[helper.CATALOG])
    assert (
        sum(hashlib.sha256(originals[name]).hexdigest() != digest for name, digest in catalog["sources"].items()) == 40
    )
    dry_run = helper.refresh(checkout)
    assert dry_run["checked"] == 49 and len(dry_run["needsRefresh"]) == 47
    assert not dry_run["applied"] and dry_run["backupDirectory"] is None
    assert originals == {name: (checkout / name).read_bytes() for name in paths}
    backup_parent = tmp_path / "backups"
    backup_parent.mkdir()
    applied = helper.refresh(checkout, apply=True, backup_parent=backup_parent)
    backup = Path(applied["backupDirectory"])
    assert applied["applied"] and stat.S_IMODE(backup.stat().st_mode) == 0o700
    manifest = json.loads((backup / "manifest.json").read_bytes())
    assert len(manifest["files"]) == 49
    for entry in manifest["files"]:
        name = entry["path"]
        assert (backup / "files" / name).read_bytes() == originals[name]
        assert entry["bytes"] == len(originals[name])
        assert entry["sha256"] == hashlib.sha256(originals[name]).hexdigest()
        assert entry["mode"] == modes[name] == stat.S_IMODE((checkout / name).stat().st_mode)
        assert (checkout / name).read_bytes() == (ROOT / name).read_bytes()
    assert unchanged == {name: (checkout / name).read_bytes() for name in unchanged}
    # Index bytes/stat metadata stay untouched; raw working bytes are the repair contract.
    assert _git(checkout, "diff", "--exit-code") == b""
    assert helper.refresh(checkout, apply=True, backup_parent=backup_parent)["backupDirectory"] is None
    assert list(backup_parent.iterdir()) == [backup]


@pytest.mark.parametrize("edit", ["private", "mixed", "catalog", "oversize"])
def test_checkout_refresh_refuses_the_whole_plan_for_unexpected_bytes(tmp_path: Path, edit: str) -> None:
    helper = load_script("refresh_capability_checkout")
    root = _refresh_copy(tmp_path)
    path = root / (helper.CATALOG if edit == "catalog" else "scripts/generate_successor_capability.py")
    raw = path.read_bytes()
    if edit == "mixed":
        path.write_bytes(raw.replace(b"\r\n", b"\n", 1))
    elif edit == "oversize":
        with path.open("wb") as stream:
            stream.truncate(helper.MAX_FILE_BYTES + 1)
    else:
        path.write_bytes(raw + b"private edit\r\n")
    originals = {name: (root / name).read_bytes() for name in capability_checkout_paths()}
    backups = tmp_path / "backups"
    backups.mkdir()
    with pytest.raises(ValueError):
        helper.refresh(root, apply=True, backup_parent=backups)
    assert originals == {name: (root / name).read_bytes() for name in originals}
    assert list(backups.iterdir()) == []


def test_checkout_refresh_refuses_aliases_and_inside_backup_before_changes(tmp_path: Path) -> None:
    helper = load_script("refresh_capability_checkout")
    root = _refresh_copy(tmp_path)
    with pytest.raises(ValueError, match="outside"):
        helper.refresh(root, apply=True, backup_parent=root)
    catalog = root / helper.CATALOG
    saved = catalog.read_bytes()
    outside = tmp_path / "original-catalog.json"
    outside.write_bytes(saved)
    catalog.unlink()
    catalog.symlink_to(outside)
    with pytest.raises(ValueError, match="regular"):
        helper.refresh(root, apply=True, backup_parent=tmp_path)
    assert outside.read_bytes() == saved
    assert not list(tmp_path.glob("capability-lf-backup-*"))


def test_checkout_refresh_retains_all_originals_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_script("refresh_capability_checkout")
    root = _refresh_copy(tmp_path)
    originals = {name: (root / name).read_bytes() for name in capability_checkout_paths()}
    backups = tmp_path / "backups"
    backups.mkdir()

    def unavailable_replace(*arguments: object) -> None:
        raise OSError("ordinary unavailable destination fixture")

    monkeypatch.setattr(helper.os, "replace", unavailable_replace)
    with pytest.raises(RuntimeError, match="original bytes retained"):
        helper.refresh(root, apply=True, backup_parent=backups)
    (backup,) = backups.iterdir()
    assert json.loads((backup / "result.json").read_bytes()) == {"applied": [], "complete": False}
    assert originals == {name: (root / name).read_bytes() for name in originals}
    assert originals == {name: (backup / "files" / name).read_bytes() for name in originals}
    assert not [path for path in root.rglob(".*") if ".lf-" in path.name]
