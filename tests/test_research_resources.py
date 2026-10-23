# SPDX-License-Identifier: Apache-2.0
"""Closed research navigation never promotes executable HTML into passive papers."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import homepage_evidence as homepage
from scripts import paper_changes as changes
from scripts import publish_paper_site as publication
from scripts import research_papers as papers
from tests.test_homepage_evidence import featured_paper_report, report as report_fixture
from tests.test_paper_changes import append_paper, assert_full, history as history_fixture, save
from tests.test_research_papers import catalog, encoded, paper_row, pdf_bytes, refresh_fixture, write_paper_fixture

EXPERIENCE = "docs/reports/fixture-v2/experience.html"
HTML = b"<!doctype html><title>Explicit local fixture</title><p>Not a deployed instrument.</p>"
RELEASE = papers.RELEASE_SITE + "tag/study-fixture-v2-r1"
report = report_fixture
history = history_fixture


def resources() -> dict[str, Any]:
    return {
        "experience": {"path": EXPERIENCE, "sha256": hashlib.sha256(HTML).hexdigest()},
        "companion": {
            "url": papers.RELEASE_SITE + "download/study-fixture-v2-r1/Fixture_Companion.zip",
            "sha256": "a" * 64,
            "bytes": 1234,
        },
        "source_evidence": {"url": RELEASE},
    }


def source_download_resources() -> dict[str, Any]:
    return {
        "tex_source": {"path": "docs/papers/paper-0.tex", "sha256": "b" * 64},
        "experimental_source": {
            "url": papers.SOURCE_SITE + "a" * 40 + "/studies/fixture-v1/README.md",
        },
        "source_archive": {
            "url": papers.RELEASE_SITE + "download/study-fixture-v2-r1/Complete_Source.zip",
            "sha256": "c" * 64,
            "bytes": 2345,
        },
        "visual_signature": {
            "url": papers.RELEASE_SITE + "download/study-fixture-v2-r1/Visual_Signature.png",
            "sha256": "d" * 64,
            "bytes": 3456,
        },
    }


def with_resources(data: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(data)
    data["schema"] = papers.RESOURCE_SCHEMA
    data["papers"][-1]["resources"] = resources()
    return data


def write_experience(root: Path, raw: bytes = HTML) -> None:
    path = root / EXPERIENCE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def test_v1_catalogue_preserves_original_homepage_and_readme_bytes() -> None:
    data = catalog(paper_row("paper-0"), paper_row("paper-1", featured=False))
    # Golden fixture bytes rendered by the unchanged 61532fb8 source before this extension.
    assert hashlib.sha256(papers.render_section(data).encode()).hexdigest() == (
        "5f90f961324ef6d4abeaffca0666ee0d4027df11bb76f97da5d5fbbeed2fb7ad"
    )
    assert hashlib.sha256(papers.render_readme(data).encode()).hexdigest() == (
        "dd88825e0ffb2aaa35ab3db61179f8692d6af480ccf80169f25cb2b081c8d967"
    )
    assert papers.experience_hashes(data) == {}


def test_resource_schema_has_four_ctas_and_keeps_passive_assets_separate(tmp_path: Path) -> None:
    data = with_resources(write_paper_fixture(tmp_path, count=2))
    write_experience(tmp_path)
    parsed = papers.parse_catalog(encoded(data))
    papers.verify_files(tmp_path, parsed)
    html = papers.render_section(parsed)
    readme = papers.render_readme(parsed)
    assert html.count('class="paper-link"') == 2
    assert html.count('class="paper-resource-link"') == 3
    assert ">Read the paper</span>" in html
    for role, labels in papers.RESOURCE_LABELS.items():
        if role not in resources():
            continue
        assert f'data-paper-resource="{role}"' in html
        assert labels["en"] in html and labels["fr"] in html
        assert labels["en"] in readme
    assert 'href="reports/fixture-v2/experience.html"' in html
    assert papers.PUBLIC_SITE + "reports/fixture-v2/experience.html" in readme
    assert EXPERIENCE not in papers.asset_hashes(parsed)
    assert papers.experience_hashes(parsed) == {EXPERIENCE: hashlib.sha256(HTML).hexdigest()}
    with pytest.raises(ValueError, match="Only catalog-referenced docs PDF/TEX"):
        publication.site_assets(papers.experience_hashes(parsed))


@pytest.mark.parametrize(
    "role,field,value",
    [
        ("experience", "path", "docs/reports/fixture-v2/../experience.html"),
        ("experience", "path", "/docs/reports/fixture-v2/experience.html"),
        ("experience", "path", "docs/reports/fixture-v2/experience.html?x=1"),
        ("experience", "path", "docs/reports/fixture-v2/%2e%2e.html"),
        ("experience", "path", "docs/reports/fixture-v2/experience.js"),
        ("experience", "path", "docs/reports/fixture-v2/experience.htm"),
        ("experience", "path", "docs/reports/fixture-v2\\experience.html"),
        ("experience", "sha256", "A" * 64),
        ("experience", "sha256", "a" * 63),
        ("companion", "url", "https://example.org/fixture.zip"),
        ("companion", "url", "https://github.com@evil.example/fixture.zip"),
        ("companion", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/../Fixture.zip"),
        ("companion", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/Fixture.zip?x=1"),
        ("companion", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/Fixture.zip#fragment"),
        ("companion", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/%46ixture.zip"),
        ("companion", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/Fixture.exe"),
        ("companion", "bytes", True),
        ("companion", "bytes", 1.0),
        ("companion", "bytes", 0),
        ("companion", "bytes", -1),
        ("companion", "bytes", papers.MAX_COMPANION + 1),
        ("source_evidence", "url", "javascript:alert(1)"),
        ("source_evidence", "url", RELEASE + "/"),
        ("source_evidence", "url", RELEASE + "?x=1"),
        ("source_evidence", "url", RELEASE.replace("https:", "http:")),
        ("source_evidence", "url", RELEASE.replace("MontrealAI", "SomeoneElse")),
        ("source_evidence", "url", papers.RELEASE_SITE + "tag/another-release"),
    ],
)
def test_resource_records_reject_unsafe_or_inexact_targets(role: str, field: str, value: Any) -> None:
    items = resources()
    items[role][field] = value
    with pytest.raises(ValueError):
        papers.resource_records(items)


@pytest.mark.parametrize("value", [{}, [], None, {"other": {}}, {"experience": []}])
def test_resource_roles_are_closed(value: Any) -> None:
    with pytest.raises(ValueError):
        papers.resource_records(value)


@pytest.mark.parametrize("role", list(papers.RESOURCE_LABELS))
def test_resource_fields_are_closed(role: str) -> None:
    items = resources()
    items.update(source_download_resources())
    if role == "reading":
        items[role] = {"path": "docs/reports/fixture-v2/index.html", "sha256": hashlib.sha256(HTML).hexdigest()}
    items[role]["label"] = "Unsafe custom template"
    with pytest.raises(ValueError):
        papers.resource_records(items)
    del items[role]["label"]
    items[role].pop(next(iter(items[role])))
    with pytest.raises(ValueError):
        papers.resource_records(items)


@pytest.mark.parametrize(
    "role,field,value",
    [
        ("tex_source", "path", "docs/papers/../paper.tex"),
        ("tex_source", "path", "docs/papers/paper.html"),
        ("tex_source", "path", "https://example.org/paper.tex"),
        ("tex_source", "sha256", "B" * 64),
        ("experimental_source", "url", papers.SOURCE_SITE + "main/studies/fixture-v1/README.md"),
        ("experimental_source", "url", papers.SOURCE_SITE + "a" * 39 + "/studies/fixture-v1/README.md"),
        ("experimental_source", "url", papers.SOURCE_SITE + "A" * 40 + "/studies/fixture-v1/README.md"),
        ("experimental_source", "url", papers.SOURCE_SITE + "a" * 40 + "/studies/../README.md"),
        ("experimental_source", "url", papers.SOURCE_SITE + "a" * 40 + "/studies/fixture-v1/ASSEMBLE.py"),
        ("experimental_source", "url", papers.SOURCE_SITE + "a" * 40 + "/studies/fixture-v1/README.md?x=1"),
        ("experimental_source", "url", papers.SOURCE_SITE + "a" * 40 + "/studies/fixture-v1/README.md#run"),
        ("experimental_source", "url", "https://github.com@evil.example/blob/" + "a" * 40 + "/studies/x/README.md"),
        ("source_archive", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/Complete_Source.exe"),
        ("source_archive", "url", "https://example.org/Complete_Source.zip"),
        ("source_archive", "bytes", True),
        ("source_archive", "bytes", papers.MAX_COMPANION + 1),
        ("source_archive", "sha256", "C" * 64),
        ("visual_signature", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/Visual_Signature.svg"),
        ("visual_signature", "url", papers.RELEASE_SITE + "download/study-fixture-v2-r1/Visual_Signature.png#x"),
        ("visual_signature", "bytes", True),
        ("visual_signature", "bytes", 0),
        ("visual_signature", "bytes", papers.MAX_PAPER + 1),
        ("visual_signature", "sha256", "d" * 63),
    ],
)
def test_source_download_navigation_rejects_unpinned_or_unsafe_metadata(role: str, field: str, value: Any) -> None:
    items = source_download_resources()
    items[role][field] = value
    with pytest.raises(ValueError):
        papers.resource_records(items)


@pytest.mark.parametrize("role", ["source_archive", "visual_signature"])
def test_source_downloads_require_the_declared_publication_release(role: str) -> None:
    items = source_download_resources()
    items["source_evidence"] = {"url": RELEASE}
    items[role]["url"] = items[role]["url"].replace("study-fixture-v2-r1", "study-other-v1")
    with pytest.raises(ValueError, match="same research release"):
        papers.resource_records(items)


@pytest.mark.parametrize("damage", ["path", "sha256", "absent"])
def test_standalone_tex_navigation_cannot_substitute_another_original(damage: str) -> None:
    data = catalog()
    data["schema"] = papers.RESOURCE_SCHEMA
    row = data["papers"][0]
    row["tex"] = {"path": "docs/papers/first.tex", "sha256": "b" * 64}
    row["resources"] = {"tex_source": deepcopy(row["tex"])}
    if damage == "absent":
        row["tex"] = None
    else:
        row["resources"]["tex_source"][damage] = "docs/papers/other.tex" if damage == "path" else "e" * 64
    with pytest.raises(ValueError, match="exact original"):
        papers.parse_catalog(encoded(data))


def test_source_downloads_are_bilingual_navigation_without_executable_import(tmp_path: Path) -> None:
    data = write_paper_fixture(tmp_path)
    data["schema"] = papers.RESOURCE_SCHEMA
    row = data["papers"][0]
    tex = b"% Opaque original TeX; never compiled\n"
    row["tex"] = {"path": "docs/papers/paper-0.tex", "sha256": hashlib.sha256(tex).hexdigest()}
    (tmp_path / row["tex"]["path"]).write_bytes(tex)
    row["resources"] = source_download_resources() | {"source_evidence": {"url": RELEASE}}
    row["resources"]["tex_source"] = deepcopy(row["tex"])
    parsed = papers.parse_catalog(encoded(data))
    papers.verify_files(tmp_path, parsed)
    html = papers.render_section(parsed)
    readme = papers.render_readme(parsed)
    assert papers.experience_hashes(parsed) == {}
    assert papers.asset_hashes(parsed) == {row[kind]["path"]: row[kind]["sha256"] for kind in ("pdf", "tex")}
    assert '<script' not in html and '<iframe' not in html
    for role, item in row["resources"].items():
        labels = papers.RESOURCE_LABELS[role]
        assert f'href="{papers.resource_href(role, item)}"' in html
        assert labels["en"] in html and labels["fr"] in html
        assert papers.resource_href(role, item, readme=True) in readme
    assert "(unmerged)" in html and "(non fusionné)" in html
    assert "not cryptographic" in html and "non cryptographique" in html


def test_v1_rejects_resources_and_v2_rejects_case_ambiguous_identities(tmp_path: Path) -> None:
    data = with_resources(write_paper_fixture(tmp_path, count=2))
    data["schema"] = papers.SCHEMA
    with pytest.raises(ValueError, match="Unexpected paper fields"):
        papers.parse_catalog(encoded(data))
    data["schema"] = papers.RESOURCE_SCHEMA
    data["papers"][0]["resources"] = resources()
    papers.parse_catalog(encoded(data))  # Exact shared target is unambiguous.
    data["papers"][0]["resources"]["experience"]["path"] = EXPERIENCE.replace("experience", "Experience")
    with pytest.raises(ValueError, match="Ambiguous"):
        papers.parse_catalog(encoded(data))


@pytest.mark.parametrize("field,value", [("sha256", "b" * 64), ("bytes", 1235)])
def test_shared_companion_urls_cannot_claim_conflicting_bytes(tmp_path: Path, field: str, value: Any) -> None:
    data = with_resources(write_paper_fixture(tmp_path, count=2))
    data["papers"][0]["resources"] = resources()
    papers.parse_catalog(encoded(data))
    data["papers"][0]["resources"]["companion"][field] = value
    with pytest.raises(ValueError, match="Ambiguous research companion identity"):
        papers.parse_catalog(encoded(data))


@pytest.mark.parametrize("damage", ["remove", "retarget", "digest"])
def test_published_resources_are_immutable(tmp_path: Path, damage: str) -> None:
    old = with_resources(write_paper_fixture(tmp_path))
    new = deepcopy(old)
    item = new["papers"][0]["resources"]
    if damage == "remove":
        del item["experience"]
    elif damage == "retarget":
        item["experience"]["path"] = EXPERIENCE.replace("experience", "other")
    else:
        item["experience"]["sha256"] = "b" * 64
    with pytest.raises(ValueError, match="Historical research resource identities"):
        papers.preserve_catalog(old, new)


@pytest.mark.parametrize("damage", ["missing", "digest", "empty", "mode", "symlink", "utf8"])
def test_experience_local_checks_are_bounded_and_do_not_execute(tmp_path: Path, damage: str) -> None:
    data = with_resources(write_paper_fixture(tmp_path))
    write_experience(tmp_path)
    path = tmp_path / EXPERIENCE
    if damage == "missing":
        path.unlink()
    elif damage == "digest":
        path.write_bytes(HTML + b"changed")
    elif damage == "empty":
        path.write_bytes(b"")
    elif damage == "mode":
        path.chmod(0o755)
    elif damage == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / data["papers"][0]["pdf"]["path"])
    else:
        path.write_bytes(b"\xff")
        data["papers"][0]["resources"]["experience"]["sha256"] = hashlib.sha256(b"\xff").hexdigest()
    with pytest.raises(ValueError):
        papers.verify_files(tmp_path, data)


def test_import_rejects_invalid_experience_before_mutating_originals(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_paper_fixture(root)
    write_experience(root, b"\xff")
    row = paper_row("new-paper", featured=False)
    row["resources"] = resources()
    row["resources"]["experience"]["sha256"] = hashlib.sha256(b"\xff").hexdigest()
    del row["pdf"], row["tex"]
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps(row))
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(pdf_bytes())
    before = publication.inventory(root)
    with pytest.raises(UnicodeDecodeError):
        papers.add_paper(root, pdf, metadata)
    assert publication.inventory(root) == before
    assert not (root / "docs/papers/new-paper.pdf").exists()


@pytest.mark.parametrize("revert", [False, True])
def test_new_html_and_reverted_html_history_still_require_full_qualification(
    history: tuple[Path, str], revert: bool
) -> None:
    root, base = history
    write_experience(root)
    first = save(root, "Unqualified executable fixture")
    assert_full(root, base, first)
    if revert:
        (root / EXPERIENCE).unlink()
        append_paper(root)
        assert_full(root, base, save(root, "Reverted HTML and added a paper"))


def qualified_fixture(
    history: tuple[Path, str], tmp_path: Path
) -> tuple[Path, Path, str, dict[str, Any], dict[str, Any]]:
    root, _ = history
    write_experience(root)
    data = with_resources(papers.load_catalog(root))
    refresh_fixture(root, data)
    software = save(root, "Fixture qualified full-source baseline")
    site = tmp_path / "site"
    path = site / EXPERIENCE.removeprefix("docs/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(HTML)
    return root, site, software, publication.inventory(site), data


def test_overlay_can_link_only_byte_identical_already_qualified_html(history: tuple[Path, str], tmp_path: Path) -> None:
    root, site, software, baseline, data = qualified_fixture(history, tmp_path)
    publication.require_qualified_experiences(root, site, software_commit=software, baseline=baseline, catalog=data)
    assert publication.inventory(site) == baseline


def test_later_metadata_can_link_existing_qualified_html_without_reclassifying_it_as_a_paper_asset(
    history: tuple[Path, str], tmp_path: Path
) -> None:
    root, _ = history
    write_experience(root)
    software = save(root, "Fixture full source with pre-existing HTML")
    data = with_resources(papers.load_catalog(root))
    refresh_fixture(root, data)
    head = save(root, "Link already-qualified resource bytes")
    proof = changes.classify(root, software, head)
    assert proof["mode"] == "paper", proof
    assert proof["software_commit"] == software
    assert EXPERIENCE not in papers.asset_hashes(data)
    site = tmp_path / "site"
    target = site / EXPERIENCE.removeprefix("docs/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(HTML)
    baseline = publication.inventory(site)
    publication.require_qualified_experiences(root, site, software_commit=software, baseline=baseline, catalog=data)
    assert publication.inventory(site) == baseline


@pytest.mark.parametrize("damage", ["new", "source", "site", "manifest", "manifest_size", "missing_source"])
def test_overlay_refuses_unqualified_html_without_copying_or_mutating(
    history: tuple[Path, str], tmp_path: Path, damage: str
) -> None:
    root, site, software, baseline, data = qualified_fixture(history, tmp_path)
    name = EXPERIENCE.removeprefix("docs/")
    if damage == "new":
        del baseline[name]
    elif damage == "source":
        (root / EXPERIENCE).write_bytes(HTML + b"changed")
    elif damage == "site":
        (site / name).write_bytes(HTML + b"changed")
    elif damage == "manifest":
        baseline[name]["sha256"] = "b" * 64
    elif damage == "manifest_size":
        baseline[name]["bytes"] = papers.MAX_EXPERIENCE + 1
    else:
        software = history[1]  # Exact baseline predates the HTML, even if restored bytes exist.
    before = publication.inventory(site)
    with pytest.raises(ValueError):
        publication.require_qualified_experiences(root, site, software_commit=software, baseline=baseline, catalog=data)
    assert publication.inventory(site) == before


@pytest.mark.parametrize("damage", [None, "missing", "digest", "extra", "bytes_marker", "links_marker"])
def test_homepage_evidence_binds_resource_links_and_exact_experience_bytes(
    report: dict[str, Any], monkeypatch: pytest.MonkeyPatch, damage: str | None
) -> None:
    expected = {EXPERIENCE.removeprefix("docs/"): hashlib.sha256(HTML).hexdigest()}
    monkeypatch.setattr(homepage, "EXPERIENCE_ASSETS", expected)
    links = {"fixture": {role: papers.resource_href(role, item) for role, item in resources().items()}}
    monkeypatch.setattr(homepage, "RESOURCE_LINKS", links)
    value = featured_paper_report(report, "1.38.0")
    value["research_experience_assets"] = dict(expected)
    value["research_resources"] = deepcopy(links)
    value["checks"] = sorted(set(value["checks"]) | {"research-resource-links", "qualified-research-experience-bytes"})
    if damage == "missing":
        del value["research_experience_assets"]
    elif damage == "digest":
        value["research_experience_assets"][next(iter(expected))] = "b" * 64
    elif damage == "extra":
        value["research_experience_assets"]["reports/other/experience.html"] = "b" * 64
    elif damage == "bytes_marker":
        value["checks"].remove("qualified-research-experience-bytes")
    elif damage == "links_marker":
        value["checks"].remove("research-resource-links")
    if damage is None:
        homepage.verify_report(value, "a" * 40, "1.38.0", "https://site/")
    else:
        with pytest.raises(ValueError):
            homepage.verify_report(value, "a" * 40, "1.38.0", "https://site/")


def test_external_only_resource_links_still_require_evidence(
    report: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    links = {"fixture": {"source_evidence": RELEASE}}
    monkeypatch.setattr(homepage, "EXPERIENCE_ASSETS", {})
    monkeypatch.setattr(homepage, "RESOURCE_LINKS", links)
    value = featured_paper_report(report, "1.38.0")
    with pytest.raises(ValueError, match="Research resource navigation"):
        homepage.verify_report(value, "a" * 40, "1.38.0", "https://site/")
    value["research_resources"] = links
    value["checks"].append("research-resource-links")
    homepage.verify_report(value, "a" * 40, "1.38.0", "https://site/")
