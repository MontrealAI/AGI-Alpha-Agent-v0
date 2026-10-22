# SPDX-License-Identifier: Apache-2.0
"""Include successful public Pages acceptance in an unpublished release package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from scripts.ascension_protocol_evidence import verify_report as verify_protocol_report
from scripts.business3_evidence import verify_report as verify_business3_report
from scripts.curriculum_evidence import verify_report as verify_curriculum_report
from scripts.discovery_evidence import verify_report as verify_discovery_report
from scripts.experience_evidence import verify_report as verify_experience_report
from scripts.governance_evidence import verify_report as verify_governance_report
from scripts.homepage_evidence import verify_report as verify_homepage_report
from scripts.mats_evidence import verify_report as verify_mats_report
from scripts.release_packs import (
    MAX_ASSET_BYTES,
    MAX_MANIFEST_BYTES,
    digest,
    pack,
    require_asset_limits,
    restore,
    safe_name,
)
from scripts.sovereign_evidence import verify_report as verify_sovereign_report
from scripts.successor_evidence import verify_report as verify_successor_report
from scripts.onboarding_evidence import verify_report as verify_onboarding_report


def verify_workbench_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    """Require exact deployed workbench bytes and completed browser journeys."""
    root = Path(__file__).resolve().parents[1]
    sources = json.loads((root / "alpha_factory_v1/core/runtime/successor/workbench_sources.json").read_text())
    expected = {
        "schema": "agialpha.successor-workbench.acceptance.v1",
        "commit": commit,
        "version": version,
        "origin": origin + "successor/work/",
        "sourceHash": sources["sourceHash"],
        "page_sha256": hashlib.sha256((root / "docs/successor/work/index.html").read_bytes()).hexdigest(),
        "families": ["reliability", "performance", "documentation", "public-data", "numerical"],
        "offline_save_reopen": "PASS",
        "keyboard": "PASS",
        "languages": ["en", "fr"],
        "viewports": [1440, 390, 320],
        "axe": "PASS",
        "errors": [],
    }
    if report.get("passed") is not True or any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Workbench must pass every journey against the exact public release and source bytes")


def _inventory(folder: Path) -> dict[str, tuple[int, str]]:
    """Retain every ordinary capture file and reject extraction-ambiguous paths."""
    result = {}
    folded = set()
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Evidence must contain ordinary files and directories")
        if path.is_file():
            name = safe_name(path.relative_to(folder).as_posix())
            if name.casefold() in folded:
                raise ValueError("Evidence contains case-ambiguous capture paths")
            folded.add(name.casefold())
            result[name] = (path.stat().st_size, digest(path))
    return result


def _local_validation(folder: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    path = folder / f"alpha-agent-v{manifest['version']}-validation.zip"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ASSET_BYTES:
        raise ValueError("Local validation archive must remain an ordinary bounded release asset")
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": digest(path)}


def prepare_public_validation(
    folder: Path, evidence: Path, manifest: dict[str, Any], *, limit: int = MAX_ASSET_BYTES
) -> dict[str, Any]:
    """Keep local evidence intact; shard and independently restore every public capture byte."""
    before = _inventory(evidence)
    prefix = f"alpha-agent-v{manifest['version']}-public-validation"
    packed = pack(evidence, folder, prefix, commit=manifest["commit"], version=manifest["version"], limit=limit)
    data = json.loads(packed.read_bytes())
    record = {
        "schema": "agialpha.validation-evidence.v1",
        "commit": manifest["commit"],
        "version": manifest["version"],
        "local": _local_validation(folder, manifest),
        "public": {
            "manifest": packed.name,
            "bytes": packed.stat().st_size,
            "sha256": digest(packed),
            "files": len(data["files"]),
            "packs": len(data["packs"]),
        },
    }
    verify_public_validation(folder, evidence, {**manifest, "validation_evidence": record})
    if _inventory(evidence) != before:
        raise ValueError("Public capture changed during packaging")
    return record


def verify_public_validation(folder: Path, evidence: Path, manifest: dict[str, Any]) -> None:
    """Make an unchanged rerun a no-op; reject changed, partial or tampered finalized captures."""
    record = manifest.get("validation_evidence")
    if not isinstance(record, dict) or set(record) != {"schema", "commit", "version", "local", "public"}:
        raise ValueError("Invalid retained validation-evidence identity")
    if (
        record["schema"] != "agialpha.validation-evidence.v1"
        or record["commit"] != manifest["commit"]
        or record["version"] != manifest["version"]
        or record["local"] != _local_validation(folder, manifest)
    ):
        raise ValueError("Retained local validation or release identity differs")
    name = f"alpha-agent-v{manifest['version']}-public-validation-packs.json"
    path = folder / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Public validation pack manifest must be an ordinary bounded release asset")
    data = json.loads(path.read_bytes())
    expected = {
        "manifest": name,
        "bytes": path.stat().st_size,
        "sha256": digest(path),
        "files": len(data["files"]),
        "packs": len(data["packs"]),
    }
    if record["public"] != expected:
        raise ValueError("Retained public validation pack identity differs")
    with tempfile.TemporaryDirectory(prefix="alpha-public-verify-") as temporary:
        restored = Path(temporary) / "restored"
        identity = restore(path, restored)
        if identity["commit"] != manifest["commit"] or identity["version"] != manifest["version"]:
            raise ValueError("Public validation packs identify a different release")
        if _inventory(restored) != _inventory(evidence):
            raise ValueError("Public validation packs omit, change or add capture bytes")


@contextmanager
def staged_release(folder: Path) -> Iterator[Path]:
    """Stage and check assets before promotion; roll back reported promotion errors."""
    original = {path.name for path in folder.iterdir()}
    metadata = {name: (folder / name).read_bytes() for name in ("release-manifest.json", "SHA256SUMS")}
    with tempfile.TemporaryDirectory(prefix=".alpha-public-release-", dir=folder.resolve().parent) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        for path in folder.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError("Release assets must be ordinary files")
            if path.name in metadata:
                shutil.copyfile(path, stage / path.name)
            else:
                os.link(path, stage / path.name)
        yield stage
        if original != {path.name for path in folder.iterdir()} or any(
            (folder / name).read_bytes() != raw for name, raw in metadata.items()
        ):
            raise ValueError("Release assets changed while finalization was staged")
        promoted = []
        changed = []
        try:
            for path in sorted(stage.iterdir()):
                if path.name not in original:
                    os.link(path, folder / path.name)
                    promoted.append(folder / path.name)
            for name in metadata:
                os.replace(stage / name, folder / name)
                changed.append(name)
        except BaseException:
            for name in changed:
                backup = Path(temporary) / (name + ".original")
                backup.write_bytes(metadata[name])
                os.replace(backup, folder / name)
            for path in promoted:
                path.unlink()
            raise


def verify_legacy_evidence(folder: Path, evidence: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    """Require complete local and direct public URL evidence for new releases."""
    if tuple(map(int, manifest["version"].split("."))) < (1, 37, 1):
        return None
    from scripts.legacy_public_urls import verify_report

    local = manifest.get("legacy_public_urls")
    if not isinstance(local, dict):
        raise ValueError("Missing packaged legacy public URL acceptance")
    packs = folder / "site-packs.json"
    verify_report(local, manifest["commit"], manifest["version"], packs, mode="local")
    public = json.loads((evidence / "public-pages/legacy-public-urls.json").read_text(encoding="utf-8"))
    verify_report(public, manifest["commit"], manifest["version"], packs, mode="public")
    return public


def finalize(folder: Path, evidence: Path) -> None:
    """Bind public evidence to the packaged commit and refresh package checksums."""
    manifest_path = folder / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    public = json.loads((evidence / "public-pages" / "release.json").read_text(encoding="utf-8"))
    workspace = json.loads((evidence / "public-pages" / "workspace.json").read_text(encoding="utf-8"))
    url = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
    if public["commit"] != manifest["commit"] or public["version"] != manifest["version"]:
        raise ValueError("Public Pages evidence differs from the packaged source")
    if workspace["origin"] != url or not workspace["model_required"] or public["url"] != url:
        raise ValueError("Public Pages acceptance must exercise the full canonical site")
    legacy_public_urls = verify_legacy_evidence(folder, evidence, manifest)
    flagship = None
    if tuple(map(int, manifest["version"].split("."))) >= (1, 34, 0):
        from scripts.successor_alpha_evidence import load_report, verify_release_workspace, verify_report

        flagship = load_report(evidence / "public-pages" / "successor-alpha" / "report.json")
        verify_report(flagship, manifest["commit"], manifest["version"], mode="public")
        verify_release_workspace(manifest.get("successor_alpha"), folder, manifest["commit"], manifest["version"])
    transformational = None
    if tuple(map(int, manifest["version"].split("."))) >= (1, 36, 0):
        from scripts.transformational_evidence import load_report, verify_release_workspace, verify_report

        transformational = load_report(evidence / "public-pages/transformational-intelligence/report.json")
        verify_report(transformational, manifest["commit"], manifest["version"], mode="public")
        verify_release_workspace(
            manifest.get("transformational_intelligence"), folder, manifest["commit"], manifest["version"]
        )
    workbench = None
    ascension = None
    insight = None
    bloom = None
    compounding = None
    studio = None
    protocol = None
    business3 = None
    governance = None
    discovery = None
    experience = None
    mats = None
    curriculum = None
    sovereign = None
    successor = None
    onboarding = None
    homepage = None
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 5, 0):
        ascension = json.loads((evidence / "public-pages" / "ascension" / "ascension.json").read_text(encoding="utf-8"))
        if ascension.get("passed") is not True or ascension.get("origin") != url:
            raise ValueError("Ascension must pass on the canonical public site")
        if ascension.get("paper_sha256") != "fd14d444d51e9f6ebaec13387fc8d2170615d1bbfab13edc7e84ea1f655d20aa":
            raise ValueError("Public white paper differs from the preserved original")
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 6, 0):
        insight = json.loads(
            (evidence / "public-pages" / "insight-atlas" / "insight-atlas.json").read_text(encoding="utf-8")
        )
        required = {
            "all-three-scenarios",
            "stale-proof-rejected",
            "tampered-proof-rejected",
            "unsafe-quorum-blocked",
            "native-mission-schema",
            "native-research-execution-and-signed-export",
            "reviewed-design-reuse-requires-fresh-evidence",
            "recovery-replays-promotions",
            "tampered-history-rejected",
            "revocation-survives-recovery",
            "mirrored-page",
            "offline-reload-recovery-and-replay",
            "axe-wcag-a-aa-no-violations",
            "keyboard-selection-retains-focus",
        }
        if (
            insight.get("schema") != "agialpha.insight.acceptance.v1"
            or insight.get("passed") is not True
            or insight.get("origin") != url
            or insight.get("browser_errors") != []
            or not required.issubset(insight.get("checks", []))
            or {item.get("id") for item in insight.get("scenarios", [])} != {"energy", "science", "enterprise"}
        ):
            raise ValueError("Insight Atlas must pass every required journey on the canonical public site")
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 7, 0):
        bloom = json.loads((evidence / "public-pages" / "proof-bloom" / "proof-bloom.json").read_text(encoding="utf-8"))
        bloom_required = {
            "all-five-experiences",
            "original-gallery-preserved",
            "baseline-and-stress-computed",
            "native-missions-executed-and-signed-returns",
            "signature-key-and-input-binding",
            "self-declared-verdict-rejected",
            "tampered-and-stale-return-rejected",
            "reviewed-failure-remains-hold",
            "exact-benchmark-reuse-needs-fresh-probes",
            "transitive-revocation",
            "unchanged-recovery-roundtrip",
            "tampered-history-rejected-atomically",
            "jobspec-download-sha256",
            "keyboard-focus-preserved",
            "input-text-escaped",
            "mirrored-page",
            "offline-recovery-and-execution",
            "mobile-no-overflow",
            "axe-wcag-a-aa-no-violations",
        }
        if (
            bloom.get("schema") != "agialpha.bloom.acceptance.v1"
            or bloom.get("passed") is not True
            or bloom.get("origin") != url
            or bloom.get("browser_errors") != []
            or not bloom_required.issubset(bloom.get("checks", []))
            or {item.get("id") for item in bloom.get("experiences", [])}
            != {"nova", "sovereign", "omega", "invention", "proof"}
        ):
            raise ValueError("Proof Bloom must pass every required journey on the canonical public site")
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 8, 0):
        compounding = json.loads(
            (evidence / "public-pages" / "compounding" / "compounding.json").read_text(encoding="utf-8")
        )
        required_transfer = {
            "exact-198-page-manuscript",
            "all-three-scenarios",
            "python-javascript-exact-replay",
            "complete-docket-zip-replay",
            "review-does-not-override-loss",
            "archive-ablation-zero-gain",
            "eci-e2-no-independent-claim",
            "native-cli-browser-handoff",
            "imported-review-keeps-timing-provenance",
            "tampered-and-stale-import-rejected-atomically",
            "cost-overhead-closes-gate",
            "changed-inputs-clear-review",
            "keyboard-focus-preserved",
            "axe-wcag-a-aa-no-violations",
            "mobile-no-overflow",
            "offline-recovery-and-execution",
            "mirrored-page",
        }
        if (
            compounding.get("schema") != "agialpha.transfer.acceptance.v1"
            or compounding.get("passed") is not True
            or compounding.get("origin") != url
            or compounding.get("browser_errors") != []
            or compounding.get("manuscript_sha256")
            != "4b290d5a8232364b8808c0af8a96e7c9b152afd7ac3f5ba05668a538e073791a"
            or not required_transfer.issubset(compounding.get("checks", []))
            or {item.get("id") for item in compounding.get("scenarios", [])} != {"seasonal", "shift", "ablation"}
        ):
            raise ValueError("Compounding Lab and exact manuscript must pass on the canonical public site")
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 10, 0):
        studio = json.loads(
            (evidence / "public-pages" / "decision-studio" / "decision-studio.json").read_text(encoding="utf-8")
        )
        required_studio = {
            "all-case-calculations",
            "downloaded-dossier-cli-replay",
            "edited-input-invalidation",
            "worker-cancellation",
            "forgery-rejection",
            "csv-import-infeasibility",
            "explicit-save-restore-clear",
            "all-artifact-downloads",
            "mobile-no-overflow",
            "accessible-controls",
            "practical-catalog-search",
            "legacy-route-bridge",
            "offline-recalculation",
            "public-current-assets",
            "staffing-cap-and-backlog-hold",
            "editable-table-keyboard-focus",
            "archived-dossier-replay",
        }
        if (
            studio.get("schema") != "agialpha.decision.acceptance.v1"
            or studio.get("passed") is not True
            or studio.get("origin") != url
            or studio.get("commit") != manifest["commit"]
            or studio.get("version") != manifest["version"]
            or studio.get("calculation_version") != "1.10.0"
            or studio.get("browser_errors") != []
            or studio.get("http_failures") != []
            or not required_studio.issubset(studio.get("checks", []))
            or {item.get("id") for item in studio.get("cases", [])}
            != {
                "capital",
                "invention",
                "supply",
                "delivery",
                "launch",
                "inventory",
                "service",
                "energy",
                "proof",
                "nova",
                "agency",
            }
            or len(studio.get("cases", [])) != 11
        ):
            raise ValueError("Decision Studio must pass every public journey for the exact packaged commit and version")
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 12, 1):
        protocol = json.loads(
            (evidence / "public-pages" / "ascension-protocol" / "report.json").read_text(encoding="utf-8")
        )
        verify_protocol_report(protocol, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 13, 0):
        business3 = json.loads((evidence / "public-pages" / "business3" / "business3.json").read_text(encoding="utf-8"))
        verify_business3_report(business3, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 14, 0):
        governance = json.loads(
            (evidence / "public-pages" / "governance" / "governance.json").read_text(encoding="utf-8")
        )
        verify_governance_report(governance, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 15, 0):
        discovery = json.loads((evidence / "public-pages" / "discovery" / "discovery.json").read_text(encoding="utf-8"))
        verify_discovery_report(discovery, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 16, 0):
        experience = json.loads(
            (evidence / "public-pages" / "experience" / "experience.json").read_text(encoding="utf-8")
        )
        verify_experience_report(experience, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 17, 0):
        mats = json.loads((evidence / "public-pages" / "mats" / "mats.json").read_text(encoding="utf-8"))
        verify_mats_report(mats, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 18, 0):
        curriculum = json.loads(
            (evidence / "public-pages" / "curriculum" / "curriculum.json").read_text(encoding="utf-8")
        )
        verify_curriculum_report(curriculum, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 22, 0):
        sovereign = json.loads((evidence / "public-pages" / "sovereign" / "sovereign.json").read_text(encoding="utf-8"))
        verify_sovereign_report(sovereign, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 24, 0):
        successor = json.loads((evidence / "public-pages" / "successor" / "successor.json").read_text(encoding="utf-8"))
        verify_successor_report(successor, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 25, 0):
        onboarding = json.loads(
            (evidence / "public-pages" / "onboarding" / "onboarding.json").read_text(encoding="utf-8")
        )
        verify_onboarding_report(onboarding, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 26, 2):
        homepage = json.loads((evidence / "public-pages" / "homepage" / "homepage.json").read_text(encoding="utf-8"))
        verify_homepage_report(homepage, manifest["commit"], manifest["version"], url)
    if tuple(int(part) for part in manifest["version"].split(".")) >= (1, 29, 0):
        workbench = json.loads(
            (evidence / "public-pages" / "successor-workbench" / "browser-report.json").read_text(encoding="utf-8")
        )
        verify_workbench_report(workbench, manifest["commit"], manifest["version"], url)
    if tuple(map(int, manifest["version"].split("."))) >= (1, 30, 0):
        from scripts.mark_wallet_evidence import verify_report as verify_wallet

        wallet = json.loads((evidence / "public-pages" / "mark-wallet" / "report.json").read_text())
        verify_wallet(wallet, manifest["commit"], manifest["version"], url)
        from scripts.nova_studio_evidence import verify_browser

        studio = json.loads((evidence / "public-pages" / "nova-studio" / "report.json").read_text())
        verify_browser(studio, manifest["commit"], manifest["version"], url)
    checksummed = set()
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if name in checksummed or name == "SHA256SUMS":
            raise ValueError("Duplicate or self-referential package checksum")
        checksummed.add(name)
        path = folder / name
        if path.parent != folder or not path.is_file() or path.is_symlink():
            raise ValueError("Invalid packaged asset")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"Packaged asset changed before public acceptance: {name}")
    if {path.name for path in folder.iterdir()} != checksummed | {"SHA256SUMS"}:
        raise ValueError("Every packaged asset must be covered by SHA256SUMS")
    if "validation_evidence" in manifest:
        verify_public_validation(folder, evidence, manifest)
        require_asset_limits(folder)
        return
    with staged_release(folder) as stage:
        folder = stage
        manifest_path = folder / "release-manifest.json"
        manifest["validation_evidence"] = prepare_public_validation(folder, evidence, manifest)
        manifest["public_pages"] = public
        if legacy_public_urls is not None:
            manifest["public_legacy_public_urls"] = legacy_public_urls
            manifest["release_gates"].append(
                "public direct-200 legacy paths/index routes/anchors and exact original PDFs without redirects"
            )
        if flagship:
            manifest["public_successor_alpha"] = flagship
            manifest["release_gates"].append(
                "public HTTPS SUCCESSOR Alpha exact packaged bytes, complete useful mission, constructed strategy, "
                "native Node host return, EN/FR accessibility and offline continuity"
            )
        if transformational:
            manifest["public_transformational_intelligence"] = transformational
            manifest["release_gates"].append(
                "public HTTPS TI exact-byte readback, full native/browser journey and saved offline recovery"
            )
        if workbench:
            manifest["public_successor_workbench"] = workbench
            manifest["release_gates"].append(
                "public five-family workbench, exact source bytes, EN/FR accessibility and saved offline artifacts"
            )
        if homepage:
            manifest["public_homepage"] = homepage
            manifest["release_gates"].append(
                "public welcoming homepage, English/French handoff, larger text, keyboard access and mobile reflow"
            )
        if onboarding:
            manifest["public_onboarding"] = onboarding
            manifest["release_gates"].append(
                "public English/French onboarding, exact downloads, review and accessibility"
            )
        if successor:
            manifest["public_successor"] = successor
            manifest["release_gates"].append(
                "public SUCCESSOR bilingual lifecycle, native handoff, cache upgrade and offline recovery"
            )
        if sovereign:
            manifest["public_sovereign"] = sovereign
            manifest["release_gates"].append(
                "public Sovereign canonical/mirrored galleries, six exact signed fixture downloads and accessibility"
            )
        if curriculum:
            manifest["public_curriculum"] = curriculum
            manifest["release_gates"].append(
                "public Curriculum Lab independent solving, exact exports, lineage, accessibility and offline replay"
            )
        if mats:
            manifest["public_mats"] = mats
            manifest["release_gates"].append(
                "public MATS exact tree search, six-file exports, independent gates, accessibility and offline replay"
            )
        if experience:
            manifest["public_experience"] = experience
            manifest["release_gates"].append(
                "public Experience Lab exact learning, six-file exports, independent review gates, "
                "accessibility and offline replay"
            )
        if discovery:
            manifest["public_discovery"] = discovery
            manifest["release_gates"].append(
                "public Insight Discovery exact review portfolios, six-file exports, input-bound jobs, "
                "accessibility and offline replay"
            )
        if governance:
            manifest["public_governance"] = governance
            manifest["release_gates"].append(
                "public Governance Workbench exact decisions, five-file exports, input-bound jobs, "
                "accessibility and offline replay"
            )
        if business3:
            manifest["public_business3"] = business3
            manifest["release_gates"].append(
                "public Business 3 exact decisions, seven-file exports, Ascension jobs, "
                "accessibility and offline recovery"
            )
        if protocol:
            manifest["public_ascension_protocol"] = protocol
            manifest["release_gates"].append(
                "public Ascension protocol exact assets, evidence download, mirrored routes, "
                "accessibility and offline use"
            )
        if studio:
            manifest["public_decision_studio"] = studio
            manifest["release_gates"].append(
                "public Decision Studio staffing, deadline-aware plans, archived replay, exports, "
                "accessibility and offline use"
            )
        if compounding:
            manifest["public_compounding"] = compounding
            manifest["release_gates"].append(
                "public future-task transfer, native/browser dossier replay, failure gates "
                "and exact 198-page manuscript"
            )
        if bloom:
            manifest["public_proof_bloom"] = bloom
            manifest["release_gates"].append(
                "public Proof Bloom jobs, native signed returns, reviewed gates, "
                "transitive revocation and offline recovery"
            )
        if insight:
            manifest["public_insight_atlas"] = insight
            manifest["release_gates"].append(
                "public Insight Atlas, native exports, adversarial proof checks and offline recovery"
            )
        if ascension:
            manifest["public_ascension"] = ascension
            manifest["release_gates"].append(
                "public Ascension journey, authenticated recovery, exact settlement and offline use"
            )
        manifest["release_gates"].append("public HTTPS Pages workflows and actual offline model generation")
        manifest["assets"] = [
            item for item in require_asset_limits(folder) if item["name"] not in {"release-manifest.json", "SHA256SUMS"}
        ]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        checksums = []
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.name != "SHA256SUMS":
                with path.open("rb") as stream:
                    checksums.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {path.name}")
        (folder / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")
        require_asset_limits(folder)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path("release"))
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    finalize(args.release, args.evidence)


if __name__ == "__main__":
    main()
