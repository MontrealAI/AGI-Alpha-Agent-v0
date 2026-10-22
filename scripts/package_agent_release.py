#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Package the exact committed source, installed wheel and acceptance evidence."""

from __future__ import annotations

import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from alpha_factory_v1.utils.disclaimer import DISCLAIMER
from scripts.check_agent_preservation import BADGE_MAINTENANCE
from scripts.check_factory_readiness import check as verify_factory
from scripts.check_manuscript import verify as verify_manuscript
from scripts.check_successor_preservation import check as verify_successor_preservation
from scripts.release_packs import MAX_ASSET_BYTES, digest, require_asset_limits, restore
from scripts.wait_for_release_ci import require_historical_evidence

TI_PUBLIC_EXAMPLES = (
    "examples/transformational-intelligence/campaign.json",
    "examples/transformational-intelligence/policy-study/spec.json",
    "examples/transformational-intelligence/policy-study/training.json",
    "examples/transformational-intelligence/policy-study/confirmation.json",
    "examples/transformational-math/expected-results.json",
    "examples/transformational-intelligence/public-preparation/input.json",
    "examples/transformational-intelligence/public-preparation/retained-run.json",
    "examples/transformational-intelligence/public-preparation/direct-origination-profile.md",
    "examples/transformational-intelligence/public-preparation/ubuntu-ephemeral-creator.md",
    "examples/transformational-intelligence/public-preparation/LICENSE.Manager",
    "examples/transformational-source-audit/fixture.json",
    "examples/transformational-source-audit/expected-results.json",
)

CAPABILITY_GUIDES = (
    "docs/discovery-lab/README.md",
    "docs/discovery-lab/SPECIFICATION.md",
    "docs/discovery-lab/PAPER_TO_CODE.md",
    "docs/discovery-lab/SOURCES.json",
    "docs/discovery-lab/MODEL_REVIEW.json",
    "docs/discovery-lab/FOUNDATION_REPRODUCTION.json",
    "docs/discovery-lab/RELEASE_NOTES.md",
    "docs/discovery-lab/CONTINUATION_2026-10-21.md",
    "docs/discovery-lab/FUTURE_PROTOCOL.md",
    "docs/discovery-lab/EVIDENCE_DOCKET.md",
    "docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.md",
    "docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json",
    "docs/discovery-lab/REAL_TASK_ADAPTER.md",
    "examples/successor-capability/README.md",
    "examples/successor-capability/out-execute/README.md",
)


def qualify_legacy_site(
    site: Path, pack_manifest: Path, commit: str, version: str, evidence: Path
) -> dict[str, Any] | None:
    """Check retained public addresses against the exact restored distribution."""
    if tuple(map(int, version.split("."))) < (1, 37, 1):
        return None
    from scripts.legacy_public_urls import check_site, verify_report

    report = check_site(site, pack_manifest, commit, version)
    verify_report(report, commit, version, pack_manifest, mode="local")
    (evidence / "legacy-public-urls.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def release_documents(version: str) -> tuple[str, ...]:
    """Retain the existing release documents and include the complete operating path."""
    documents: tuple[str, ...] = (
        "requirements-agent.lock",
        "scripts/install_agent.py",
        "scripts/release_packs.py",
        "docs/agent/SUCCESSOR.md",
        "docs/agent/SUCCESSOR_OPERATIONS.md",
        "docs/agent/SUCCESSOR_ACCEPTANCE.md",
        "docs/agent/SUCCESSOR_ASCENSION.md",
        "docs/agent/SUCCESSOR_SOURCES.json",
        "docs/agent/SUCCESSOR_ARCHITECTURE.md",
        "docs/agent/SUCCESSOR_PACKAGING.md",
        "docs/agent/SUCCESSOR_ALPHA.md",
        "docs/agent/SUCCESSOR_ALPHA_DEPLOYMENT.md",
        "docs/agent/SUCCESSOR_ALPHA_CONTINUITY.md",
        "docs/agent/START_HERE.md",
        "docs/agent/ONBOARDING.md",
        "docs/agent/MAINNET_READINESS.md",
        "docs/agent/MAINNET_DEPLOYMENT.md",
        "docs/agent/CURRENT_MAINNET_DEPLOYMENT.md",
        "docs/agent/MARK_WALLET.md",
        "docs/agent/NOVA_SEED_STUDIO.md",
        "docs/agent/NOVA_SEED_STUDIO_ENGINEERING.md",
        "docs/agent/ASCENSION_STACK_RELEASE.md",
        "docs/agent/ECOSYSTEM_ADAPTERS.md",
        "docs/agent/SUPPLIER_BROWSER_ADAPTER.md",
        "docs/agent/SUCCESSOR_COMPUTER_USE.md",
        "docs/agent/NATIVE_BUDGET_RESERVATIONS.md",
        "docs/agent/ASCENSION_CYCLE.md",
        "docs/agent/ASCENSION_CYCLE_HANDOFF.md",
        "docs/agent/ASCENSION_CYCLE_ENGINEERING.md",
        "docs/agent/REPOSITORY_GUIDE.md",
        "docs/agent/FACTORY_GUIDE.md",
        "docs/agent/DEMOS.md",
        "docs/agent/ASCENSION_PROTOCOL.md",
        "docs/agent/OPERATIONS.md",
        "docs/agent/CAPABILITIES.md",
        "docs/agent/VALIDATION.md",
        "docs/agent/DEMO_VALIDATION.md",
        "docs/agent/DEMO_AUDIT_2026-10-01.md",
        "docs/agent/PAGES_GUIDE.md",
        "docs/agent/WHITEPAPER_IMPLEMENTATION.md",
        "docs/agent/INSIGHT_ATLAS.md",
        "docs/agent/PROOF_BLOOM.md",
        "docs/agent/COMPOUNDING_LAB.md",
        "docs/agent/DECISION_STUDIO.md",
        "docs/agent/BUSINESS3.md",
        "docs/agent/GOVERNANCE.md",
        "docs/agent/DISCOVERY.md",
        "docs/agent/EXPERIENCE.md",
        "docs/agent/MATS.md",
        "docs/agent/CURRICULUM_LAB.md",
        "docs/agent/MUZERO.md",
        "docs/agent/MANUSCRIPT_ALIGNMENT.md",
        "docs/manuscript/AGI_ALPHA_Unified_Publication_Final.pdf",
        "docs/manuscript/AGI_ALPHA_Unified_Publication_Final.md",
        "docs/manuscript/source-manifest.json",
        "docs/agent/RELEASE_READINESS.md",
        f"docs/agent/RELEASE_NOTES_{version}.md",
    )
    if tuple(map(int, version.split("."))) >= (1, 36, 0):
        documents += (
            "docs/agent/TRANSFORMATIONAL_IMPLEMENTATION.md",
            "examples/transformational-intelligence/README.md",
            "examples/transformational-intelligence/LOCAL_MODEL.md",
            "examples/transformational-intelligence/policy-study/README.md",
            "examples/transformational-math/README.md",
            "examples/transformational-intelligence/public-preparation/README.md",
            "examples/transformational-source-audit/README.md",
        )
    if tuple(map(int, version.split("."))) >= (1, 38, 0):
        documents += (*CAPABILITY_GUIDES, "docs/agent/PAPER_UPLOADS.md")
    return documents


def release_document_name(name: str) -> str:
    """Keep distinct example guides usable in the flattened operator archive."""
    if name in CAPABILITY_GUIDES:
        if name.startswith("docs/discovery-lab/"):
            return "DISCOVERY_LAB_" + Path(name).stem + Path(name).suffix
        return "OUT_EXECUTE.md" if "/out-execute/" in name else "CAPABILITY_WORKSPACE.md"
    return {
        "examples/transformational-intelligence/README.md": "TRANSFORMATIONAL_DISCOVERY.md",
        "examples/transformational-intelligence/LOCAL_MODEL.md": "TRANSFORMATIONAL_LOCAL_MODEL.md",
        "examples/transformational-intelligence/policy-study/README.md": "TRANSFORMATIONAL_POLICY_STUDY.md",
        "examples/transformational-math/README.md": "TRANSFORMATIONAL_MATH.md",
        "examples/transformational-intelligence/public-preparation/README.md": "TRANSFORMATIONAL_PUBLIC_PILOT.md",
        "examples/transformational-source-audit/README.md": "TRANSFORMATIONAL_SOURCE_AUDIT.md",
    }.get(name, Path(name).name)


def operator_document_name(name: str) -> str:
    """Preserve new capability repository paths inside the operator archive."""
    return "capability/" + name if name in CAPABILITY_GUIDES else release_document_name(name)


def capability_archive_entry(
    root: Path, page: bytes, available: set[str], commit: str
) -> tuple[bytes, dict[str, bytes], list[dict[str, str]]]:
    """Adapt only anchor navigation; keep the original inline programs, styles and CSP."""
    text = page.decode("utf-8")
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    anchors: list[tuple[int, str, str]] = []

    class Links(HTMLParser):
        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            href = dict(attrs).get("href")
            if tag == "a" and href is not None:
                line, column = self.getpos()
                start_tag = self.get_starttag_text()
                if start_tag is None:
                    raise ValueError("Capability anchor has no original start-tag text")
                anchors.append((offsets[line - 1] + column, start_tag, href))

    Links().feed(text)
    additions = {}
    navigation = []
    replacements = []
    for offset, tag, href in anchors:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (root / "docs/successor/capabilities" / unquote(parsed.path)).resolve()
        if not target.is_relative_to(root):
            raise ValueError("Capability archive link leaves the repository")
        name = target.relative_to(root).as_posix()
        if target.suffix.lower() == ".pdf" and name not in available and name not in additions:
            additions[name] = target.read_bytes()
        if name in available or name in additions:
            adapted = (
                name + ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
            )
        else:
            if target.is_dir():
                target = target / "index.html"
            elif not target.exists() and target.with_suffix(".md").is_file():
                target = target.with_suffix(".md")
            if not target.is_file():
                raise ValueError("Capability navigation has no repository source: " + href)
            source = target.relative_to(root).as_posix()
            navigation.append(
                {
                    "originalHref": href,
                    "sourcePath": source,
                    "sourceUrl": f"https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/{commit}/{source}",
                }
            )
            adapted = "#archive-navigation"

        def replace_href(match: re.Match[str]) -> str:
            return match[1] + match[2] + escape(adapted, quote=True) + match[2]

        rewritten, count = re.subn(
            r"(\bhref\s*=\s*)([\"'])(.*?)\2",
            replace_href,
            tag,
            count=1,
        )
        if count != 1:
            raise ValueError("Capability navigation attribute cannot be adapted")
        replacements.append((offset, len(tag), rewritten))
    for offset, size, replacement in reversed(replacements):
        remaining_start = offset + size
        text = text[:offset] + replacement + text[remaining_start:]
    if 'id="archive-navigation"' in text:
        raise ValueError("Capability archive navigation identity collides")
    links = "".join(
        f'<li><a href="{escape(item["sourceUrl"], quote=True)}">'
        f'Exact source for {escape(item["originalHref"])}</a></li>'
        for item in {item["sourcePath"]: item for item in navigation}.values()
    )
    notice = (
        '<aside id="archive-navigation" class="panel" aria-labelledby="archive-navigation-heading">'
        '<h2 id="archive-navigation-heading">Other journeys and source guides</h2>'
        "<p>This operator archive runs the capability workspace and retains its linked papers and guides. "
        "The gallery and other journeys require the separate full site distribution. "
        "Their exact source remains available through the links below; these are source views, "
        "not an accepted live deployment.</p>"
        f"<ul>{links}</ul></aside>"
    )
    if text.count("</main>") != 1:
        raise ValueError("Capability archive entry needs one main region")
    return text.replace("</main>", notice + "</main>", 1).encode(), additions, navigation


def capture_capability_operator(
    root: Path, version: str, commit: str
) -> tuple[dict[str, bytes], dict[str, Any], bytes, list[dict[str, str]], set[str]]:
    """Own every original guide and validated raw input before creating any output."""
    captured: dict[str, bytes] = {}

    def capture(name: str) -> bytes:
        if name not in captured:
            captured[name] = (root / name).read_bytes()
        return captured[name]

    for name in release_documents(version):
        capture(name)
    for name in ("docs/transformational-intelligence/index.html", *TI_PUBLIC_EXAMPLES):
        capture(name)
    catalog_path = "docs/successor/capabilities/sources.json"
    page_path = "docs/successor/capabilities/index.html"
    paper_catalog_path = "docs/research-papers.json"
    catalog = json.loads(capture(catalog_path))
    sources = catalog["sources"]
    encoded = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != catalog["sourceHash"]:
        raise ValueError("Capability source catalog digest does not reproduce")
    for name, expected in sources.items():
        if hashlib.sha256(capture(name)).hexdigest() != expected:
            raise ValueError("Capability source differs from catalog: " + name)
    from scripts.research_papers import asset_hashes, parse_catalog

    papers = asset_hashes(parse_catalog(capture(paper_catalog_path)))
    for name, expected in papers.items():
        if hashlib.sha256(capture(name)).hexdigest() != expected:
            raise ValueError("Paper source differs from catalog: " + name)
    raw_names = set(sources) | set(papers) | {catalog_path, page_path, paper_catalog_path}
    entry, additions, navigation = capability_archive_entry(
        root, capture(page_path), raw_names | set(CAPABILITY_GUIDES), commit
    )
    captured.update(additions)
    raw_names.update(additions)
    return captured, catalog, entry, navigation, raw_names


def copy_release_documents(
    root: Path,
    output: Path,
    version: str,
    commit: str,
    *,
    archive_links: bool = False,
    captured: dict[str, bytes] | None = None,
) -> dict[str, bytes]:
    """Use pinned standalone fixture links or archive-local links; preserve manuscripts."""
    root = root.resolve()
    names = release_documents(version)
    if tuple(map(int, version.split("."))) >= (1, 38, 0) and captured is None:
        captured = {name: (root / name).read_bytes() for name in names}
    rendered = {}
    packaged = {name: operator_document_name(name) if archive_links else release_document_name(name) for name in names}
    if tuple(map(int, version.split("."))) >= (1, 36, 0):
        packaged["docs/transformational-intelligence/index.html"] = "transformational-intelligence-workspace.html"
        if archive_links:
            packaged.update(
                {name: "transformational-examples/" + name.removeprefix("examples/") for name in TI_PUBLIC_EXAMPLES}
            )
    if archive_links and tuple(map(int, version.split("."))) >= (1, 38, 0):
        from scripts.research_papers import asset_hashes, parse_catalog

        catalog_path = "docs/successor/capabilities/sources.json"
        assert captured is not None
        for name in (catalog_path, "docs/research-papers.json"):
            if name not in captured:
                captured[name] = (root / name).read_bytes()
        sources = json.loads(captured[catalog_path])["sources"]
        closure = (
            set(sources)
            | set(asset_hashes(parse_catalog(captured["docs/research-papers.json"])))
            | {catalog_path, "docs/successor/capabilities/index.html"}
        )
        packaged.update({name: "capability/" + name for name in closure})
        packaged["docs/successor/capabilities/index.html"] = "capability/index.html"
    for name in names:
        source = root / name
        target = output / packaged[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix != ".md" or name.startswith("docs/manuscript/"):
            if captured is None:
                shutil.copy2(source, target)
            else:
                rendered[name] = captured[name]
                target.write_bytes(rendered[name])
            continue

        def rewrite(match: re.Match[str], source: Path = source, name: str = name) -> str:
            link = match.group(1)
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return match.group(0)
            destination = (source.parent / parsed.path).resolve()
            if destination == root / "docs/assets/whitepaper_v0.1.0-alphav15.pdf":
                destination = root / "whitepaper_v0.1.0-alphav15.pdf"
            if not destination.is_relative_to(root) or not destination.exists():
                raise ValueError(f"Broken release guide link: {name}: {link}")
            relative = destination.relative_to(root).as_posix()
            if relative in packaged and not source.name.startswith("RELEASE_NOTES_"):
                url = Path(os.path.relpath(packaged[relative], Path(packaged[name]).parent)).as_posix()
            elif relative.startswith("docs/") and relative.endswith(".html"):
                url = "https://montrealai.github.io/AGI-Alpha-Agent-v0/" + relative.removeprefix("docs/").removesuffix(
                    "index.html"
                )
            else:
                kind = "tree" if destination.is_dir() else "blob"
                url = f"https://github.com/MontrealAI/AGI-Alpha-Agent-v0/{kind}/{commit}/{relative}"
            return (
                "]("
                + url
                + ("?" + parsed.query if parsed.query else "")
                + ("#" + parsed.fragment if parsed.fragment else "")
                + ")"
            )

        text = source.read_text(encoding="utf-8") if captured is None else captured[name].decode("utf-8")
        sections = re.split(r"(```.*?```)", text, flags=re.DOTALL)
        for index in range(0, len(sections), 2):
            sections[index] = re.sub(r"\]\(([^\s)]+)\)", rewrite, sections[index])
        rendered[name] = "".join(sections).encode("utf-8")
        if captured is None:
            target.write_text("".join(sections), encoding="utf-8")
        else:
            target.write_bytes(rendered[name])
    return rendered


def package_mainnet_record(root: Path, output: Path, version: str) -> Path:
    """Ship the pinned public deployment record without local operator files."""
    relative = Path("deployments/ethereum-mainnet/2026-10-11")
    record = root / relative
    raw = (record / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    verifier = (root / "tests/contracts/scripts/mainnet-record.js").read_text(encoding="utf-8")
    match = re.search(r'const RECORD_SHA256 = "([0-9a-f]{64})";', verifier)
    if not match or hashlib.sha256(raw).hexdigest() != match[1]:
        raise ValueError("Mainnet manifest differs from the pinned verifier identity")
    destination = output / f"alpha-agent-v{version}-mainnet-record.zip"
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, expected in manifest["files"].items():
            member = Path(name)
            if member.is_absolute() or ".." in member.parts:
                raise ValueError("Unsafe mainnet record member")
            source = record / member
            if source.is_symlink() or not source.is_file():
                raise ValueError("Mainnet record requires regular files")
            data = source.read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Mainnet evidence digest differs: {name}")
            archive.writestr(f"ascension-ethereum-mainnet-2026-10-11/{name}", data)
        archive.writestr("ascension-ethereum-mainnet-2026-10-11/manifest.json", raw)
        readme = (
            (record / "README.md")
            .read_text(encoding="utf-8")
            .replace("../../../docs/agent/MAINNET_DEPLOYMENT.md", "../MAINNET_DEPLOYMENT.md")
        )
        archive.writestr("ascension-ethereum-mainnet-2026-10-11/README.md", readme)
        archive.write(output / "MAINNET_DEPLOYMENT.md", "MAINNET_DEPLOYMENT.md")
        if tuple(map(int, version.split("."))) >= (1, 36, 0):
            for name in ("CURRENT_MAINNET_DEPLOYMENT.md", "MAINNET_READINESS.md"):
                archive.write(output / name, name)
    return destination


def package_successor_alpha_workspace(root: Path, output: Path) -> dict[str, str | int]:
    """Ship the exact accepted self-contained flagship page as a convenient offline asset."""
    from scripts.successor_alpha_evidence import asset_identity

    identity = asset_identity(root)
    raw = (root / "docs/successor/alpha/index.html").read_bytes()
    destination = output / "successor-alpha-workspace.html"
    with destination.open("xb") as stream:
        stream.write(raw)
    return {"name": destination.name, "bytes": len(raw), "sha256": identity["pageSha256"]}


def package_operator_guide(root: Path, output: Path, version: str, commit: str) -> Path:
    """Retain all guides with offline links, the exact TI page and public fixtures."""
    destination = output / f"alpha-agent-v{version}-operator-guide.zip"
    snapshot = (
        capture_capability_operator(root, version, commit)
        if tuple(map(int, version.split("."))) >= (1, 38, 0)
        else None
    )
    if snapshot is not None:
        captured, catalog, entry, navigation, raw_names = snapshot
        if (output / "transformational-intelligence-workspace.html").read_bytes() != captured[
            "docs/transformational-intelligence/index.html"
        ]:
            raise ValueError("Operator TI workspace differs from captured source")
    with tempfile.TemporaryDirectory(prefix="alpha-operator-guides-") as raw:
        guides = Path(raw)
        rendered = copy_release_documents(
            root, guides, version, commit, archive_links=True, captured=snapshot[0] if snapshot is not None else None
        )
        with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
            for name in release_documents(version):
                if name.startswith(("docs/agent/", "examples/transformational")):
                    path = guides / operator_document_name(name)
                    if snapshot is None:
                        archive.write(path, operator_document_name(name))
                    else:
                        archive.writestr(operator_document_name(name), rendered[name])
            if tuple(map(int, version.split("."))) >= (1, 36, 0):
                if snapshot is None:
                    archive.write(
                        output / "transformational-intelligence-workspace.html",
                        "transformational-intelligence-workspace.html",
                    )
                else:
                    archive.writestr(
                        "transformational-intelligence-workspace.html",
                        captured["docs/transformational-intelligence/index.html"],
                    )
                for name in TI_PUBLIC_EXAMPLES:
                    if snapshot is None:
                        archive.write(root / name, "transformational-examples/" + name.removeprefix("examples/"))
                    else:
                        archive.writestr("transformational-examples/" + name.removeprefix("examples/"), captured[name])
            if snapshot is not None:
                page_path = "docs/successor/capabilities/index.html"
                bindings = {}
                for name in sorted(raw_names | set(CAPABILITY_GUIDES)):
                    destination_name = "capability/" + name
                    original = captured[name]
                    packaged = original if name in raw_names else rendered[name]
                    archive.writestr(destination_name, packaged)
                    bindings[name] = {
                        "archivePath": destination_name,
                        "sourceSha256": hashlib.sha256(original).hexdigest(),
                        "packagedSha256": hashlib.sha256(packaged).hexdigest(),
                    }
                archive.writestr("capability/index.html", entry)
                archive.writestr(
                    "capability/source-map.json",
                    json.dumps(
                        {
                            "schema": "agialpha.capability-operator-guide.v1",
                            "commit": commit,
                            "version": version,
                            "sourceHash": catalog["sourceHash"],
                            "files": bindings,
                            "entry": {
                                "archivePath": "capability/index.html",
                                "originalArchivePath": "capability/" + page_path,
                                "originalSha256": hashlib.sha256(captured[page_path]).hexdigest(),
                                "adaptedSha256": hashlib.sha256(entry).hexdigest(),
                                "adaptation": (
                                    "Anchor navigation and archive scope only; original script/style/CSP unchanged."
                                ),
                                "externalJourneySources": navigation,
                            },
                        },
                        sort_keys=True,
                        indent=2,
                    )
                    + "\n",
                )
                archive.writestr(
                    "capability/README.md",
                    "# Capability operator guides\n\n"
                    "Open index.html for the self-contained browser workspace and usable archive navigation.\n"
                    "docs/discovery-lab/README.md and examples/successor-capability/README.md describe its scope.\n"
                    "Run CLI reproduction and full repository checks from the separate source archive; this guide\n"
                    "archive retains the browser import closure and all directly linked original papers, "
                    "not every test runner.\n"
                    "The full gallery and other journeys need the separate site distribution; "
                    "archive navigation explains this scope.\n"
                    "docs/successor/capabilities/index.html is the byte-preserved raw original for source inspection.\n"
                    "source-map.json binds repository paths, original bytes, packaged guide bytes "
                    "and this source identity.\n"
                    "Historical records are not current acceptance or authority to execute external work.\n",
                )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(["git", "diff", "--exit-code", "--quiet", "HEAD"], check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    historical_ci = require_historical_evidence(args.evidence, sha)
    output = args.output.resolve()
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("release version must be major.minor.patch")
    flagship = None
    if tuple(map(int, version.split("."))) >= (1, 34, 0):
        from scripts.successor_alpha_evidence import require_local_reports

        flagship = require_local_reports(args.evidence, sha, version)
    transformational = None
    if tuple(map(int, version.split("."))) >= (1, 36, 0):
        from scripts.transformational_evidence import require_local_reports as require_ti_local_reports

        transformational = require_ti_local_reports(args.evidence, sha, version)["full"]
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, "-m", "scripts.check_agent_preservation"], check=True)
    if tuple(map(int, version.split("."))) >= (1, 30, 0):
        from scripts.mark_wallet_evidence import verify_report as verify_wallet

        report = json.loads((args.evidence / "mark-wallet-browser" / "report.json").read_text())
        verify_wallet(report, sha, version)
        from scripts.nova_studio_evidence import verify_browser, verify_lifecycle

        verify_lifecycle(args.evidence / "nova-studio-acceptance", sha)
        studio = json.loads((args.evidence / "nova-studio-browser" / "report.json").read_text())
        verify_browser(studio, sha, version)
    manuscript_hashes = verify_manuscript()
    factory_preservation = verify_factory()
    subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            f"--prefix=AGI-Alpha-Agent-v{version}/",
            "-o",
            str(output / f"alpha-agent-v{version}-source.zip"),
            sha,
        ],
        check=True,
    )
    with tempfile.TemporaryDirectory(prefix="alpha-release-build-") as temporary:
        clean = Path(temporary)
        with zipfile.ZipFile(output / f"alpha-agent-v{version}-source.zip") as archive:
            archive.extractall(clean)
        source = clean / f"AGI-Alpha-Agent-v{version}"
        subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output)], cwd=source, check=True
        )
    wheel = next(output.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "alpha_factory_v1/core/runtime/web/index.html" in names
        assert "alpha_factory_v1/core/runtime/cli.py" in names
        assert "alpha_factory_v1/core/runtime/successor/cli.py" in names
        assert "alpha_factory_v1/core/runtime/successor/schemas.json" in names
        assert "alpha_factory_v1/core/runtime/successor/canonical-vectors.json" in names
        assert not any("/node_modules/" in name or "/.venv/" in name for name in names)
    subprocess.run(
        [sys.executable, "-m", "twine", "check", *map(str, output.glob("*.whl")), *map(str, output.glob("*.tar.gz"))],
        check=True,
    )
    copy_release_documents(Path.cwd(), output, version, sha)
    flagship_workspace = package_successor_alpha_workspace(Path.cwd(), output) if flagship else None
    ti_workspace = None
    if transformational:
        from scripts.transformational_evidence import package_workspace

        ti_workspace = package_workspace(Path.cwd(), output)
    subprocess.run([sys.executable, "scripts/publish_computer_use_study.py", "--check"], check=True)
    shutil.copy2("docs/reports/computer-use-study/report-pack.zip", output / "computer-use-study-report-pack.zip")
    package_mainnet_record(Path.cwd(), output, version)
    shutil.copy2("deployments/ethereum-mainnet/2026-10-18/manifest.json", output / "ethereum-mainnet-2026-10-18.json")
    package_operator_guide(Path.cwd(), output, version, sha)
    with zipfile.ZipFile(output / f"alpha-agent-v{version}-manuscript.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path("docs/manuscript").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to("docs/manuscript"))
    model_manifest = json.loads(Path("scripts/browser_model_manifest.json").read_text(encoding="utf-8"))
    distributions = {}
    legacy_public_urls = None
    for kind, folder_name in (("browser", "browser-distribution"), ("site", "pages-distribution")):
        source_folder = args.evidence / folder_name
        pack_manifest = source_folder / f"{kind}-packs.json"
        with tempfile.TemporaryDirectory(prefix=f"alpha-{kind}-verify-") as temporary:
            restored = Path(temporary) / "restored"
            identity = restore(pack_manifest, restored)
            if identity["commit"] != sha or identity["version"] != version:
                raise ValueError(f"{kind} distribution differs from the tested release identity")
            if kind == "browser":
                required = {
                    "index.html",
                    "service-worker.js",
                    "insight.bundle.js",
                    "assets/local-llm/transformers.min.js",
                    "assets/local-llm/THIRD_PARTY_MODEL_NOTICES.md",
                }
                if not all((restored / name).is_file() for name in required):
                    raise ValueError("Full browser distribution is incomplete")
                for name, expected in model_manifest["files"].items():
                    if digest(restored / "assets/local-llm/models/gpt2" / name) != expected:
                        raise ValueError(f"Packaged browser model checksum mismatch: {name}")
            else:
                release = json.loads((restored / "release.json").read_bytes())
                if release["commit"] != sha or release["version"] != version:
                    raise ValueError("Site release identity differs from the accepted source")
                legacy_public_urls = qualify_legacy_site(restored, pack_manifest, sha, version, args.evidence)
        data = json.loads(pack_manifest.read_bytes())
        for name in [pack_manifest.name, *(item["name"] for item in data["packs"])]:
            shutil.copy2(source_folder / name, output / name)
        distributions[kind] = {"manifest": pack_manifest.name, "files": len(data["files"]), "packs": len(data["packs"])}
    preservation = verify_successor_preservation()
    (output / "successor-preservation.json").write_text(json.dumps(preservation, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(output / f"alpha-agent-v{version}-validation.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(args.evidence.rglob("*")):
            if path.is_file() and not {"browser-distribution", "pages-distribution", "github-pages"}.intersection(
                path.relative_to(args.evidence).parts
            ):
                archive.write(path, path.relative_to(args.evidence))
        for path in sorted(Path("docs/agent/release-evidence").glob("*.json")):
            archive.write(path, "local/" + path.name)
    manifest = {
        "version": version,
        "manuscript": {"pages": 198, "files": manuscript_hashes},
        "factory": factory_preservation,
        "successor_preservation": {key: value for key, value in preservation.items() if key != "inventory"},
        "distributions": distributions,
        "maximum_asset_bytes": MAX_ASSET_BYTES,
        "commit": sha,
        "historical_ci": historical_ci,
        "baseline": "ac9b112a44670f67d53fc3d188ef73fa16e90894",
        "repository": "MontrealAI/AGI-Alpha-Agent-v0",
        "workflow_run": (
            f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'MontrealAI/AGI-Alpha-Agent-v0')}"
            f"/actions/runs/{os.getenv('GITHUB_RUN_ID', 'local')}"
        ),
        "python": sys.version,
        "original_files_preserved": 2125,
        "original_readme_text_and_flywheels_preserved": True,
        "permitted_readme_changes": BADGE_MAINTENANCE,
        "release_gates": [
            "runtime Python 3.11/3.12/3.13",
            "full offline Python regression",
            "strict runtime types",
            "blocking repository and changed-file security/integrity hooks; cosmetic formatting advisory",
            "real Docker isolation",
            "real PostgreSQL ledger and locked TypeScript integration",
            "pinned local model inference and generated-code evaluation",
            "Chromium operator workflow",
            "legacy browser tests",
            "complete gallery rebuild and offline simulation",
            "real browser ONNX generation online and offline",
            "complete browser workspace, native handoff and Ed25519 verification",
            "Insight Atlas exact allocation, architecture search, evidence replay and Chronicle recovery",
            "Proof Bloom jobs, native signed returns, reviewed gates, capability reuse and transitive revocation",
            (
                "Compounding Lab future-task transfer, costs, human review, native/browser replay "
                "and complete Evidence Docket"
            ),
            "byte-identical latest 198-page manuscript and pinned source manifest",
            "native CPU demos and Streamlit lineage UIs",
            "Sovereign Python 3.11/3.12/3.13 dependency-gated workflow, signed packets, recovery and Chromium reviews",
            "complete demo catalog and every browser replay",
            "Business 3 exact Python/browser portfolios and exports, notebook, installed wheel and isolated container",
            (
                "Decision Studio calculation oracles, versioned replay, staffing coverage, "
                "deadlines and public offline journeys"
            ),
            "Linux Python 3.11/3.12/3.13 and macOS/Windows Python 3.12 compatibility smoke",
            "Solidity tests with shipped identity logic",
            "contract toolchain full dependency audit: no moderate/high/critical advisories",
            "unsigned mainnet plan execution and read-only verification rejection tests",
            "real local EVM payments",
            "native Ascension commitments, signed reviewed deliveries and strict evidence types",
            "Ascension protocol exact assets, canonical and mirrored routes, keyboard access and offline recovery",
            "clean wheel installation",
            "complete operator Python advisory audit with exact lock digest",
            "source preservation",
            "SUCCESSOR complete offline lifecycle, strict protocol, authority, succession and settlement adapters",
            "SUCCESSOR installed-wheel and bilingual browser request/evidence round trip",
            "SUCCESSOR five real work families, extension SDK, offline artifacts and isolated Computer Use actuator",
            "complete baseline preservation inventory and bounded verified distribution packs",
        ],
        "limits": [
            "No mainnet transactions",
            "No general intelligence claim",
            "No automatic treasury spending",
            "Optional legacy skips do not establish those integrations",
        ],
    }
    if legacy_public_urls is not None:
        manifest["legacy_public_urls"] = legacy_public_urls
        manifest["release_gates"].append(
            "retained public file paths, index routes and known anchors; immutable original PDFs and direct copies"
        )
    if flagship:
        manifest["successor_alpha"] = {"local_acceptance": flagship, "workspace": flagship_workspace}
        manifest["release_gates"].append(
            "SUCCESSOR Alpha exact catalog outputs, constructed strategies, native Node host return, "
            "retained continuity, EN/FR accessibility and offline portable workspace in both gallery builds"
        )
    if transformational:
        manifest["transformational_intelligence"] = {"local_acceptance": transformational, "workspace": ti_workspace}
        manifest["release_gates"].append(
            "bounded TI exact native comparisons, separate measurement/reuse controls, complete browser recovery "
            "and byte-identical offline workspace with operator guides"
        )
    manifest["assets"] = require_asset_limits(output)
    (output / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    lines = []
    for path in sorted(output.iterdir()):
        if path.is_file():
            with path.open("rb") as stream:
                checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            lines.append(f"{checksum}  {path.name}")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    require_asset_limits(output)
    print(json.dumps({"commit": sha, "assets": len(lines) + 1, "output": str(output)}))


if __name__ == "__main__":
    main()
