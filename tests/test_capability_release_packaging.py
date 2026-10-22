# SPDX-License-Identifier: Apache-2.0
"""The new operator guides preserve prior releases and carry an auditable source closure."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
import shutil
from urllib.parse import urlsplit
import zipfile

import pytest

from scripts import package_agent_release as packaging

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "version,digest",
    [
        ("1.35.0", "c6a9f2f36a28fdae93360bb6bc7faf69c731860e742f59d97cad1009544480c7"),
        ("1.36.0", "81f4175f36bb46d63fccc76d28fcd3b338d80540ca19fb47e91aa1ca70554bd8"),
        ("1.37.1", "e37828e5cefe15a660b4930b6bbdb1cedeae854c5d4d97761091e555c842d9e7"),
    ],
)
def test_historical_document_lists_are_unchanged(version: str, digest: str) -> None:
    encoded = json.dumps(packaging.release_documents(version), separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == digest


def test_new_guide_set_covers_the_complete_operating_documents_without_name_collisions() -> None:
    expected = {path.relative_to(ROOT).as_posix() for path in (ROOT / "docs/discovery-lab").iterdir() if path.is_file()}
    expected.update({"examples/successor-capability/README.md", "examples/successor-capability/out-execute/README.md"})
    assert set(packaging.CAPABILITY_GUIDES) == expected
    previous = set(packaging.release_documents("1.37.1")) - {"docs/agent/RELEASE_NOTES_1.37.1.md"}
    current = packaging.release_documents("1.38.0")
    assert set(current) == previous | expected | {"docs/agent/PAPER_UPLOADS.md", "docs/agent/RELEASE_NOTES_1.38.0.md"}
    destinations = [packaging.release_document_name(name) for name in current]
    assert len(destinations) == len(set(destinations))


def test_standalone_release_guides_remain_ordinary_top_level_assets(tmp_path: Path) -> None:
    packaging.copy_release_documents(ROOT, tmp_path, "1.38.0", "a" * 40)
    assets = packaging.require_asset_limits(tmp_path)
    assert len(assets) == len(packaging.release_documents("1.38.0"))
    assert all((tmp_path / packaging.release_document_name(name)).is_file() for name in packaging.CAPABILITY_GUIDES)
    assert not any(path.is_dir() for path in tmp_path.iterdir())


def test_operator_archive_retains_original_sources_papers_and_usable_nested_guide_links(tmp_path: Path) -> None:
    shutil.copyfile(
        ROOT / "docs/transformational-intelligence/index.html",
        tmp_path / "transformational-intelligence-workspace.html",
    )
    archive_path = packaging.package_operator_guide(ROOT, tmp_path, "1.38.0", "a" * 40)
    catalog = json.loads((ROOT / "docs/successor/capabilities/sources.json").read_bytes())
    with zipfile.ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        mapping = json.loads(archive.read("capability/source-map.json"))
        assert (mapping["commit"], mapping["version"], mapping["sourceHash"]) == (
            "a" * 40,
            "1.38.0",
            catalog["sourceHash"],
        )
        assert set(catalog["sources"]) <= set(mapping["files"])
        for source, binding in mapping["files"].items():
            packaged = archive.read(binding["archivePath"])
            assert binding["archivePath"] == "capability/" + source
            assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == binding["sourceSha256"]
            assert hashlib.sha256(packaged).hexdigest() == binding["packagedSha256"]
            if not source.endswith(".md") or source not in packaging.CAPABILITY_GUIDES:
                assert packaged == (ROOT / source).read_bytes()
        for source in packaging.CAPABILITY_GUIDES:
            if not source.endswith(".md"):
                continue
            destination = mapping["files"][source]["archivePath"]
            text = re.sub(r"```.*?```", "", archive.read(destination).decode(), flags=re.S)
            for link in re.findall(r"\]\(([^\s)]+)\)", text):
                parsed = urlsplit(link)
                if parsed.path and not parsed.scheme and not parsed.netloc:
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(destination), parsed.path))
                    assert target in archive.namelist(), (source, link, target)
        page = "capability/docs/successor/capabilities/index.html"
        assert archive.read(page) == (ROOT / "docs/successor/capabilities/index.html").read_bytes()
        for name in ["Out_Execute.pdf", "The_World_as_an_Output.pdf", "Invent_the_Economy.pdf"]:
            assert archive.read("capability/docs/" + name) == (ROOT / "docs" / name).read_bytes()
        entry = mapping["entry"]
        original = archive.read(entry["originalArchivePath"])
        adapted = archive.read(entry["archivePath"])
        assert entry["originalSha256"] == hashlib.sha256(original).hexdigest()
        assert entry["adaptedSha256"] == hashlib.sha256(adapted).hexdigest()
        for tag in ["script", "style"]:
            pattern = rb"<" + tag.encode() + rb"\b[^>]*>(.*?)</" + tag.encode() + rb">"
            assert re.findall(pattern, adapted, flags=re.S) == re.findall(pattern, original, flags=re.S)

        class EntryLinks(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.links: list[str] = []
                self.ids: list[str] = []
                self.csp: list[str | None] = []

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                values = dict(attrs)
                if values.get("id"):
                    self.ids.append(str(values["id"]))
                for attribute in ["href", "src"]:
                    if values.get(attribute):
                        self.links.append(str(values[attribute]))
                if tag == "meta" and values.get("http-equiv") == "Content-Security-Policy":
                    self.csp.append(values.get("content"))

        raw_parser, entry_parser = EntryLinks(), EntryLinks()
        raw_parser.feed(original.decode())
        entry_parser.feed(adapted.decode())
        assert entry_parser.csp == raw_parser.csp
        assert len(entry_parser.ids) == len(set(entry_parser.ids))
        assert "not an accepted live deployment" in adapted.decode()
        for link in entry_parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            if parsed.path:
                destination = posixpath.normpath(posixpath.join("capability", parsed.path))
                assert destination in archive.namelist(), (link, destination)
            elif parsed.fragment:
                assert parsed.fragment in entry_parser.ids, link


def test_changed_installed_source_cannot_be_archived_under_the_catalog_identity(tmp_path: Path, monkeypatch) -> None:
    shutil.copyfile(
        ROOT / "docs/transformational-intelligence/index.html",
        tmp_path / "transformational-intelligence-workspace.html",
    )
    target = ROOT / "examples/successor-capability/discovery-lab.mjs"
    read_bytes = Path.read_bytes

    def altered(path: Path) -> bytes:
        value = read_bytes(path)
        return value + b"\n// changed after catalog generation\n" if path == target else value

    monkeypatch.setattr(Path, "read_bytes", altered)
    with pytest.raises(ValueError, match="Capability source differs from catalog"):
        packaging.package_operator_guide(ROOT, tmp_path, "1.38.0", "a" * 40)


@pytest.mark.parametrize("source", ["examples/successor-capability/discovery-lab.mjs", "docs/Out_Execute.pdf"])
def test_verified_source_bytes_are_used_without_a_second_filesystem_read(
    tmp_path: Path, monkeypatch, source: str
) -> None:
    shutil.copyfile(
        ROOT / "docs/transformational-intelligence/index.html",
        tmp_path / "transformational-intelligence-workspace.html",
    )
    target = ROOT / source
    read_bytes, reads = Path.read_bytes, []

    def changing(path: Path) -> bytes:
        value = read_bytes(path)
        if path == target:
            reads.append(path)
            if len(reads) > 1:
                return value + b"\n// changed between verification and copy\n"
        return value

    monkeypatch.setattr(Path, "read_bytes", changing)
    path = packaging.package_operator_guide(ROOT, tmp_path, "1.38.0", "a" * 40)
    with zipfile.ZipFile(path) as archive:
        assert archive.read("capability/" + source) == read_bytes(target)
    assert len(reads) == 1


def test_changed_temporary_guide_copies_cannot_replace_owned_originals(tmp_path: Path, monkeypatch) -> None:
    shutil.copyfile(
        ROOT / "docs/transformational-intelligence/index.html",
        tmp_path / "transformational-intelligence-workspace.html",
    )
    original_copy = packaging.copy_release_documents
    inventory = "docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json"
    guide = "docs/discovery-lab/README.md"

    def altered_copies(root: Path, output: Path, *args, **kwargs):
        rendered = original_copy(root, output, *args, **kwargs)
        (output / packaging.operator_document_name(inventory)).write_text(
            '{"schema":"independent-unreviewed-snapshot"}'
        )
        (output / packaging.operator_document_name(guide)).write_text("# Independent unreviewed guide copy\n")
        return rendered

    monkeypatch.setattr(packaging, "copy_release_documents", altered_copies)
    path = packaging.package_operator_guide(ROOT, tmp_path, "1.38.0", "a" * 40)
    with zipfile.ZipFile(path) as archive:
        mapping = json.loads(archive.read("capability/source-map.json"))
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert archive.read("capability/" + inventory) == (ROOT / inventory).read_bytes()
        assert b"Independent unreviewed guide copy" not in archive.read("capability/" + guide)
        for source in (inventory, guide):
            assert mapping["files"][source]["sourceSha256"] == hashlib.sha256((ROOT / source).read_bytes()).hexdigest()


def test_markdown_rewrite_and_original_identity_share_one_entry_snapshot(tmp_path: Path, monkeypatch) -> None:
    shutil.copyfile(
        ROOT / "docs/transformational-intelligence/index.html",
        tmp_path / "transformational-intelligence-workspace.html",
    )
    source = "docs/discovery-lab/README.md"
    target = ROOT / source
    read_bytes, read_text = Path.read_bytes, Path.read_text
    original = read_bytes(target)
    reads = []

    def observed(path: Path) -> bytes:
        if path != target:
            return read_bytes(path)
        reads.append(path)
        return original if len(reads) == 1 else b"# Changed after entry snapshot\n"

    def observed_text(path: Path, *args, **kwargs) -> str:
        return observed(path).decode() if path == target else read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", observed)
    monkeypatch.setattr(Path, "read_text", observed_text)
    path = packaging.package_operator_guide(ROOT, tmp_path, "1.38.0", "a" * 40)
    with zipfile.ZipFile(path) as archive:
        mapping = json.loads(archive.read("capability/source-map.json"))
        assert mapping["files"][source]["sourceSha256"] == hashlib.sha256(original).hexdigest()
        assert b"Changed after entry snapshot" not in archive.read("capability/" + source)
    assert len(reads) == 1
