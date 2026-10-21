# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for immutable, data-only research paper imports."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from html import escape
from html.parser import HTMLParser
import io
import json
from pathlib import Path
from typing import Any, Callable

import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, TextStringObject

from scripts import research_papers as papers
from scripts.build_service_worker import is_cache_asset, render_scripts


def pdf_bytes(title: str = "Fixture paper", edit: Callable[[PdfWriter], None] | None = None) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": title})
    if edit:
        edit(writer)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def paper_row(slug: str = "first", *, featured: bool = True, raw: bytes | None = None) -> dict[str, Any]:
    raw = pdf_bytes() if raw is None else raw
    return {
        "id": slug,
        "title": "Fixture paper",
        "display_title": "Fixture paper",
        "title_words": [],
        "symbol": "",
        "subtitle": "",
        "author": "Fixture Author",
        "date": "2026-10-21",
        "language": "en",
        "featured": featured,
        "topic": {"en": "Bounded research", "fr": "Recherche limitée"},
        "summary": {
            "en": "A bounded test, not a capability claim.",
            "fr": "Un test limité, pas une capacité générale.",
        },
        "pdf_title": "Fixture paper",
        "pdf": {"path": f"docs/papers/{slug}.pdf", "sha256": hashlib.sha256(raw).hexdigest()},
        "tex": None,
    }


def catalog(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"schema": papers.SCHEMA, "papers": list(rows) or [paper_row()]}


def encoded(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True).encode()


def write_paper_fixture(root: Path, *, count: int = 1) -> dict[str, Any]:
    """Small standalone tree, independent of the real repository's assets/history."""
    raw = pdf_bytes()
    rows = [paper_row(f"paper-{index}", featured=index == 0, raw=raw) for index in range(count)]
    data = catalog(*rows)
    for row in rows:
        target = root / row["pdf"]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (root / papers.CATALOG).write_bytes(encoded(data))
    (root / "README.md").write_text(
        f"Stable README before\n{papers.README_START}\n{papers.render_readme(data)}\n"
        f"{papers.README_END}\nStable after\n"
    )
    (root / "docs/index.html").write_text(
        f"<!doctype html><main>\n{papers.HTML_START}\n{papers.render_section(data)}\n{papers.HTML_END}\n</main>\n"
    )
    release_path = root / "alpha_factory_v1/demos/catalog.json"
    release_path.parent.mkdir(parents=True, exist_ok=True)
    release_path.write_text(json.dumps({"release": "fixture-release"}))
    refresh_fixture(root, data)
    return data


def refresh_fixture(root: Path, data: dict[str, Any]) -> None:
    (root / papers.CATALOG).write_bytes(encoded(data))
    for name, raw in papers.rendered_files(root, data).items():
        (root / name).write_bytes(raw)
    assets = {
        path.relative_to(root / "docs").as_posix(): path.read_bytes()
        for path in (root / "docs").rglob("*")
        if path.is_file() and is_cache_asset(path.relative_to(root / "docs"))
    }
    release = json.loads((root / "alpha_factory_v1/demos/catalog.json").read_text())["release"]
    for name, raw in render_scripts(assets, release).items():
        target = root / "docs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "../escape"),
        ("id", "UPPER"),
        ("id", "x" * 65),
        ("id", 1),
        ("title", ""),
        ("title", "x" * 401),
        ("title", "a\x00b"),
        ("title", "a\ud800b"),
        ("display_title", None),
        ("author", []),
        ("subtitle", "line\nbreak"),
        ("date", "2026-02-30"),
        ("date", "20261021"),
        ("date", 20261021),
        ("language", "fr"),
        ("featured", 1),
        ("featured", False),
        ("title_words", "not a list"),
        ("title_words", ["x"] * 11),
        ("title_words", [""]),
        ("topic", {"en": "only English"}),
        ("summary", {"en": "English", "fr": "Français", "de": "Extra"}),
        ("summary", {"en": "x" * 1201, "fr": "Français"}),
        ("pdf", None),
    ],
)
def test_catalog_rejects_invalid_record_fields(field: str, value: Any) -> None:
    data = catalog()
    data["papers"][0][field] = value
    with pytest.raises(ValueError):
        papers.parse_catalog(encoded(data))


@pytest.mark.parametrize("value", [[], {}, None, {"schema": "wrong", "papers": []}])
def test_catalog_requires_exact_top_level_schema(value: Any) -> None:
    with pytest.raises(ValueError):
        papers.parse_catalog(encoded(value))


@pytest.mark.parametrize("where", ["top", "row", "file"])
def test_catalog_rejects_unknown_keys(where: str) -> None:
    data = catalog()
    target = data if where == "top" else data["papers"][0] if where == "row" else data["papers"][0]["pdf"]
    target["unexpected"] = "must not be silently ignored"
    with pytest.raises(ValueError):
        papers.parse_catalog(encoded(data))


@pytest.mark.parametrize("count", [0, 101])
def test_catalog_bounds_record_count(count: int) -> None:
    data = {"schema": papers.SCHEMA, "papers": [paper_row(f"p-{i}", featured=i == 0) for i in range(count)]}
    with pytest.raises(ValueError):
        papers.parse_catalog(encoded(data))


def test_catalog_rejects_duplicate_json_keys_and_oversize() -> None:
    raw = encoded(catalog())
    with pytest.raises(ValueError, match="Duplicate"):
        papers.parse_catalog(raw.replace(b'"author":', b'"author":"shadow", "author":'))
    with pytest.raises(ValueError, match="size"):
        papers.parse_catalog(b" " * (papers.MAX_CATALOG + 1))


@pytest.mark.parametrize(
    "path",
    [
        "../paper.pdf",
        "/docs/paper.pdf",
        "docs/../paper.pdf",
        "docs/papers/sub/paper.pdf",
        "docs/papers/a.PDF",
        "docs/papers/a.pdf?x",
        "docs/papers/a%2epdf",
        "docs/papers/a b.pdf",
        "docs/papers/a\\b.pdf",
        "docs/papers/é.pdf",
        "docs/papers/a.html",
        "docs/papers/.hidden.pdf",
    ],
)
def test_catalog_rejects_ambiguous_or_executable_paths(path: str) -> None:
    data = catalog()
    data["papers"][0]["pdf"]["path"] = path
    with pytest.raises(ValueError):
        papers.parse_catalog(encoded(data))


@pytest.mark.parametrize("digest", ["A" * 64, "0" * 63, "0" * 65, 0, "g" * 64])
def test_catalog_requires_lowercase_exact_sha256(digest: Any) -> None:
    data = catalog()
    data["papers"][0]["pdf"]["sha256"] = digest
    with pytest.raises(ValueError):
        papers.parse_catalog(encoded(data))


@pytest.mark.parametrize("conflict", ["id", "path", "case-path", "featured", "featured-order"])
def test_catalog_rejects_cross_record_ambiguity(conflict: str) -> None:
    first, second = paper_row(), paper_row("second", featured=False)
    if conflict == "id":
        second["id"] = first["id"]
    elif conflict in {"path", "case-path"}:
        second["pdf"]["path"] = first["pdf"]["path"].replace("first", "FIRST" if conflict == "case-path" else "first")
    elif conflict == "featured":
        second["featured"] = True
    else:
        first["featured"], second["featured"] = False, True
    with pytest.raises(ValueError):
        papers.parse_catalog(encoded(catalog(first, second)))


@pytest.mark.parametrize("mutation", ["remove", "rename-id", "pdf-path", "pdf-hash", "tex-remove", "tex-hash"])
def test_historical_ids_paths_and_bytes_are_immutable(mutation: str) -> None:
    old = catalog()
    old["papers"][0]["tex"] = {"path": "docs/Legacy.tex", "sha256": "1" * 64}
    new = deepcopy(old)
    row = new["papers"][0]
    if mutation == "remove":
        new["papers"] = []
    elif mutation == "rename-id":
        row["id"] = "renamed"
    elif mutation == "pdf-path":
        row["pdf"]["path"] = "docs/papers/new-path.pdf"
    elif mutation == "pdf-hash":
        row["pdf"]["sha256"] = "2" * 64
    elif mutation == "tex-remove":
        row["tex"] = None
    else:
        row["tex"]["sha256"] = "2" * 64
    with pytest.raises(ValueError):
        papers.preserve_catalog(old, new)


def test_preservation_allows_copy_edits_but_requires_versioned_new_asset_paths() -> None:
    old = catalog()
    new = deepcopy(old)
    new["papers"][0]["summary"]["fr"] = "Une description corrigée."
    papers.preserve_catalog(old, new)
    extra = paper_row("second", featured=False)
    new["papers"].append(extra)
    papers.preserve_catalog(old, new)
    extra["pdf"]["path"] = "docs/New.pdf"
    with pytest.raises(ValueError, match="docs/papers"):
        papers.preserve_catalog(old, new)
    new = deepcopy(old)
    new["papers"][0]["tex"] = {"path": "docs/New.tex", "sha256": "2" * 64}
    with pytest.raises(ValueError, match="docs/papers"):
        papers.preserve_catalog(old, new)


class CapturedHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))


def test_catalog_text_is_html_data_not_markup_or_attributes() -> None:
    data = catalog()
    row = data["papers"][0]
    attack = '<img src=x onerror="alert(1)"> & "quotes" </p><script>bad()</script>'
    for key in ("title", "display_title", "subtitle", "symbol", "author"):
        row[key] = attack
    row["title_words"] = [attack]
    row["summary"] = {"en": attack, "fr": attack}
    row["topic"] = {"en": attack, "fr": attack}
    papers.parse_catalog(encoded(data))
    html = papers.render_section(data)
    parsed = CapturedHTML()
    parsed.feed(html)
    assert not {"img", "script", "iframe"}.intersection(tag for tag, _ in parsed.elements)
    assert all(not key.startswith("on") for _, attrs in parsed.elements for key in attrs)
    assert escape(attack, quote=True) in html
    assert any(attrs.get("data-paper-fr") == attack for _, attrs in parsed.elements)
    assert [attrs["href"] for tag, attrs in parsed.elements if tag == "a"] == ["papers/first.pdf"]


def test_readme_escapes_markdown_and_raw_html() -> None:
    data = catalog()
    attack = "<img src=x onerror=alert(1)> &copy; [click](javascript:bad) ![image](evil) `code` *strong*"
    row = data["papers"][0]
    row["display_title"] = row["summary"]["en"] = row["author"] = attack
    result = papers.render_readme(data)
    assert "<img" not in result
    assert "&copy;" not in result
    assert r"\[click\]\(javascript:bad\)" in result
    assert r"\!\[image\]\(evil\)" in result
    assert r"\`code\`" in result
    assert r"\*strong\*" in result
    assert "docs/papers/first.pdf" in result


def test_fifth_paper_is_generated_generically_with_both_languages() -> None:
    data = catalog(*(paper_row(f"paper-{i}", featured=i == 0) for i in range(5)))
    last = data["papers"][-1]
    last["summary"] = {"en": "A fifth contribution.", "fr": "Une cinquième contribution."}
    papers.parse_catalog(encoded(data))
    html, readme = papers.render_section(data), papers.render_readme(data)
    assert html.count("<article ") == 5
    assert html.count('class="paper-card paper-featured"') == 1
    assert 'data-paper-key="paper-4-summary"' in html
    assert 'data-paper-fr="Une cinquième contribution."' in html
    assert 'href="papers/paper-4.pdf"' in html
    assert readme.count("https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/papers/") == 5
    assert html == papers.render_section(data)
    assert readme == papers.render_readme(data)


@pytest.mark.parametrize("text", ["start end start", "end start", "start only", "start end end"])
def test_generation_requires_one_ordered_marker_pair(text: str) -> None:
    with pytest.raises(ValueError):
        papers.replace_block(text, "start", "end", "replacement")


def test_generation_preserves_all_bytes_outside_markers() -> None:
    assert papers.replace_block("outside\nSTART\nold\nEND\nafter", "START", "END", "new") == (
        "outside\nSTART\nnew\nEND\nafter"
    )


def action(name: str, **values: Any) -> DictionaryObject:
    return DictionaryObject({NameObject("/S"): NameObject(name), **{NameObject(k): v for k, v in values.items()}})


def clicked_action(writer: PdfWriter, value: DictionaryObject) -> None:
    annotation = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/A"): value,
        }
    )
    writer.pages[0][NameObject("/Annots")] = ArrayObject([writer._add_object(annotation)])


@pytest.mark.parametrize("kind", ["destination", "goto", "https", "http", "mailto"])
def test_pdf_allows_benign_navigation(kind: str) -> None:
    def edit(writer: PdfWriter) -> None:
        if kind == "destination":
            value = ArrayObject([writer.pages[0].indirect_reference, NameObject("/Fit")])
        elif kind == "goto":
            value = action("/GoTo", **{"/D": ArrayObject([writer.pages[0].indirect_reference, NameObject("/Fit")])})
        else:
            uri = {
                "https": "https://example.org/paper",
                "http": "http://example.org",
                "mailto": "mailto:a@example.org",
            }[kind]
            clicked_action(writer, action("/URI", **{"/URI": TextStringObject(uri)}))
            return
        writer._root_object[NameObject("/OpenAction")] = value

    papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize(
    "name",
    [
        "/JavaScript",
        "/Launch",
        "/SubmitForm",
        "/ImportData",
        "/GoToR",
        "/GoToE",
        "/Rendition",
        "/Movie",
        "/Sound",
        "/Hide",
        "/ResetForm",
        "/UnknownAction",
    ],
)
@pytest.mark.parametrize("explicit_type", [False, True])
def test_pdf_rejects_active_or_unknown_actions_even_without_optional_type(name: str, explicit_type: bool) -> None:
    def edit(writer: PdfWriter) -> None:
        value = action(name)
        if explicit_type:
            value[NameObject("/Type")] = NameObject("/Action")
        writer._root_object[NameObject("/OpenAction")] = value

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize("key", ["/JS", "/JavaScript", "/RichMedia", "/XFA", "/AA", "/AcroForm", "/FT", "/FS", "/RF"])
def test_pdf_rejects_active_keys_nested_in_indirect_objects(key: str) -> None:
    def edit(writer: PdfWriter) -> None:
        nested = DictionaryObject({NameObject(key): TextStringObject("payload")})
        writer._root_object[NameObject("/Extra")] = ArrayObject([writer._add_object(nested)])

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize("subtype", ["/RichMedia", "/Movie", "/Sound", "/Screen", "/3D", "/Widget", "/FileAttachment"])
def test_pdf_rejects_active_annotation_subtypes(subtype: str) -> None:
    def edit(writer: PdfWriter) -> None:
        value = DictionaryObject(
            {NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject(subtype)}
        )
        writer.pages[0][NameObject("/Annots")] = ArrayObject([writer._add_object(value)])

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize(
    "uri", ["javascript:alert(1)", "file:///etc/passwd", "data:text/html,bad", "//example.org", "ftp://x", " https://x"]
)
def test_pdf_rejects_unsafe_link_schemes(uri: str) -> None:
    def edit(writer: PdfWriter) -> None:
        clicked_action(writer, action("/URI", **{"/URI": TextStringObject(uri)}))

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


def test_pdf_rejects_arbitrary_embedded_files() -> None:
    with pytest.raises(ValueError):
        papers.verify_pdf(
            pdf_bytes(edit=lambda writer: writer.add_attachment("payload.js", b"alert(1)")), "Fixture paper"
        )


def c2pa_attachment(writer: PdfWriter, *, malformed: bool = False, active: bool = False) -> None:
    stream = DecodedStreamObject()
    stream.set_data(b"not provenance" if malformed else b"\x00\x00\x00\x18jumbc2pa fixture metadata")
    stream[NameObject("/Type")] = NameObject("/EmbeddedFile")
    stream[NameObject("/Subtype")] = NameObject("/application/c2pa")
    if active:
        stream[NameObject("/JS")] = TextStringObject("do not execute")
    descriptor = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Filespec"),
            NameObject("/AFRelationship"): NameObject("/C2PA_Manifest"),
            NameObject("/Subtype"): TextStringObject("application/c2pa"),
            NameObject("/EF"): DictionaryObject({NameObject("/F"): writer._add_object(stream)}),
        }
    )
    writer._root_object[NameObject("/AF")] = ArrayObject([writer._add_object(descriptor)])


def test_pdf_allows_only_passive_bounded_c2pa_exception() -> None:
    papers.verify_pdf(pdf_bytes(edit=c2pa_attachment), "Fixture paper")
    for options in ({"malformed": True}, {"active": True}):
        with pytest.raises(ValueError):
            papers.verify_pdf(pdf_bytes(edit=lambda writer: c2pa_attachment(writer, **options)), "Fixture paper")


def test_pdf_title_metadata_and_encryption_are_checked() -> None:
    with pytest.raises(ValueError, match="title"):
        papers.verify_pdf(pdf_bytes(), "An unrelated title")
    papers.verify_pdf(pdf_bytes(title="Ｆｉｘｔｕｒｅ PAPER!"), "Fixture paper")
    with pytest.raises(ValueError, match="unencrypted"):
        papers.verify_pdf(pdf_bytes(edit=lambda writer: writer.encrypt("password")), "Fixture paper")
    with pytest.raises(ValueError):
        papers.verify_pdf(b"not a PDF", "Fixture paper")


@pytest.mark.parametrize("kind", ["hash", "executable", "symlink", "parent-symlink"])
def test_files_reject_tampering_and_nonordinary_paths(tmp_path: Path, kind: str) -> None:
    data = write_paper_fixture(tmp_path)
    target = tmp_path / data["papers"][0]["pdf"]["path"]
    if kind == "hash":
        target.write_bytes(target.read_bytes() + b"\nchanged")
    elif kind == "executable":
        target.chmod(0o755)
    elif kind == "symlink":
        other = tmp_path / "original.pdf"
        target.rename(other)
        target.symlink_to(other)
    else:
        directory = target.parent
        relocated = tmp_path / "original-papers"
        directory.rename(relocated)
        directory.symlink_to(relocated, target_is_directory=True)
    with pytest.raises(ValueError):
        papers.verify_files(tmp_path, data)


def test_tex_is_opaque_utf8_never_executed(tmp_path: Path) -> None:
    data = write_paper_fixture(tmp_path)
    source = b"\\immediate\\write18{touch SHOULD_NOT_EXIST}\n\\input{/etc/passwd}\n"
    target = tmp_path / "docs/papers/fixture.tex"
    target.write_bytes(source)
    data["papers"][0]["tex"] = {"path": "docs/papers/fixture.tex", "sha256": hashlib.sha256(source).hexdigest()}
    papers.verify_files(tmp_path, data)
    assert target.read_bytes() == source
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()


def test_add_fifth_paper_preserves_originals_and_generates_all_outputs(tmp_path: Path) -> None:
    root = tmp_path / "site"
    old = write_paper_fixture(root, count=4)
    originals = {name: (root / name).read_bytes() for name in papers.asset_hashes(old)}
    incoming = tmp_path / "incoming.pdf"
    incoming.write_bytes(pdf_bytes())
    incoming_tex = tmp_path / "incoming.tex"
    incoming_tex.write_bytes(b"\\documentclass{article}\n% opaque original\n")
    row = paper_row("fifth", featured=False)
    metadata = tmp_path / "metadata.json"
    metadata.write_bytes(encoded({key: value for key, value in row.items() if key not in {"pdf", "tex"}}))
    papers.add_paper(root, incoming, metadata, incoming_tex)
    current = papers.load_catalog(root)
    assert len(current["papers"]) == 5
    assert (root / "docs/papers/fifth.pdf").read_bytes() == incoming.read_bytes()
    assert (root / "docs/papers/fifth.tex").read_bytes() == incoming_tex.read_bytes()
    assert {name: (root / name).read_bytes() for name in originals} == originals
    assert (root / "docs/index.html").read_text().count("<article ") == 5
    papers.verify_files(root, current)
    papers.render(root, check=True)
    for worker in (root / "docs").rglob("service-worker.js"):
        assert 'const RELEASE = "fixture-release";' in worker.read_text()


def test_add_rejects_symlink_destination_before_writing_anything(tmp_path: Path) -> None:
    root = tmp_path / "site"
    write_paper_fixture(root)
    incoming = tmp_path / "incoming.pdf"
    incoming.write_bytes(pdf_bytes())
    row = paper_row("second", featured=False)
    metadata = tmp_path / "metadata.json"
    metadata.write_bytes(encoded({key: value for key, value in row.items() if key not in {"pdf", "tex"}}))
    original_catalog = (root / papers.CATALOG).read_bytes()
    directory = root / "docs/papers"
    outside = tmp_path / "outside"
    directory.rename(outside)
    directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        papers.add_paper(root, incoming, metadata)
    assert not (outside / "second.pdf").exists()
    assert (root / papers.CATALOG).read_bytes() == original_catalog


@pytest.mark.parametrize("as_array", [False, True])
def test_pdf_rejects_unknown_chained_action_in_every_next_shape(as_array: bool) -> None:
    def edit(writer: PdfWriter) -> None:
        chained = action("/UnknownAction")
        next_value = ArrayObject([writer._add_object(chained)]) if as_array else writer._add_object(chained)
        writer._root_object[NameObject("/OpenAction")] = action(
            "/GoTo", **{"/D": TextStringObject("local-section"), "/Next": next_value}
        )

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


def test_pdf_accepts_benign_outline_siblings_and_action_chains() -> None:
    def edit(writer: PdfWriter) -> None:
        writer.add_outline_item("First section", 0)
        writer.add_outline_item("Second section", 0)
        writer._root_object[NameObject("/OpenAction")] = action(
            "/GoTo",
            **{
                "/D": TextStringObject("local-section"),
                "/Next": ArrayObject([action("/GoTo", **{"/D": TextStringObject("another-local-section")})]),
            },
        )

    papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


def test_pdf_indirect_cycles_do_not_hang_validation() -> None:
    def edit(writer: PdfWriter) -> None:
        reference = writer._add_object(DictionaryObject())
        reference.get_object()[NameObject("/Again")] = reference
        writer._root_object[NameObject("/Cycle")] = reference

    papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize("kind", ["existing-target", "invalid-pdf", "invalid-tex", "duplicate-id"])
def test_failed_import_does_not_overwrite_originals_or_change_catalog(tmp_path: Path, kind: str) -> None:
    root = tmp_path / "site"
    write_paper_fixture(root)
    incoming = tmp_path / "incoming.pdf"
    incoming.write_bytes(b"not PDF" if kind == "invalid-pdf" else pdf_bytes())
    incoming_tex = tmp_path / "incoming.tex"
    incoming_tex.write_bytes(b"\xff\xfe" if kind == "invalid-tex" else b"% opaque source")
    row = paper_row("paper-0" if kind == "duplicate-id" else "second", featured=False)
    metadata = tmp_path / "metadata.json"
    metadata.write_bytes(encoded({key: value for key, value in row.items() if key not in {"pdf", "tex"}}))
    if kind == "existing-target":
        (root / "docs/papers/second.pdf").write_bytes(b"pre-existing bytes must survive")
    snapshot = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        papers.add_paper(root, incoming, metadata, incoming_tex)
    assert {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()} == snapshot


def test_check_detects_stale_worker_without_rewriting_it(tmp_path: Path) -> None:
    write_paper_fixture(tmp_path)
    worker = tmp_path / "docs/service-worker.js"
    worker.write_text("// stale or tampered worker\n")
    with pytest.raises(ValueError):
        papers.render(tmp_path, check=True)
    assert worker.read_text() == "// stale or tampered worker\n"


def test_catalog_loader_rejects_symlink(tmp_path: Path) -> None:
    write_paper_fixture(tmp_path)
    target = tmp_path / papers.CATALOG
    original = tmp_path / "outside.json"
    target.rename(original)
    target.symlink_to(original)
    with pytest.raises(ValueError):
        papers.load_catalog(tmp_path)


def test_simple_six_field_metadata_infers_safe_defaults_and_original_pdf_title(tmp_path: Path) -> None:
    root = tmp_path / "site"
    write_paper_fixture(root)
    incoming = tmp_path / "incoming.pdf"
    incoming.write_bytes(pdf_bytes(title="Exact Original PDF Title"))
    row = paper_row("simple", featured=False)
    metadata = tmp_path / "metadata.json"
    required = {"id", "title", "author", "date", "topic", "summary"}
    metadata.write_bytes(encoded({key: value for key, value in row.items() if key in required}))
    papers.add_paper(root, incoming, metadata)
    actual = papers.load_catalog(root)["papers"][-1]
    assert actual["pdf_title"] == "Exact Original PDF Title"
    assert actual["display_title"] == row["title"]
    assert actual["featured"] is False
    assert actual["language"] == "en"
    assert actual["title_words"] == []
    assert actual["tex"] is None
    assert (root / actual["pdf"]["path"]).read_bytes() == incoming.read_bytes()
    papers.render(root, check=True)


@pytest.mark.parametrize("kind", ["oversized", "symlink"])
def test_simple_import_preflights_pdf_before_parser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    import pypdf

    root = tmp_path / "site"
    write_paper_fixture(root)
    incoming = tmp_path / "incoming.pdf"
    incoming.write_bytes(pdf_bytes())
    if kind == "oversized":
        monkeypatch.setattr(papers, "MAX_PAPER", 10)
    else:
        actual = tmp_path / "actual.pdf"
        incoming.rename(actual)
        incoming.symlink_to(actual)
    row = paper_row("simple", featured=False)
    metadata = tmp_path / "metadata.json"
    required = {"id", "title", "author", "date", "topic", "summary"}
    metadata.write_bytes(encoded({key: value for key, value in row.items() if key in required}))

    def forbidden_parse(*args: object, **kwargs: object) -> None:
        pytest.fail("Unbounded or nonordinary source reached the PDF parser")

    monkeypatch.setattr(pypdf, "PdfReader", forbidden_parse)
    with pytest.raises(ValueError):
        papers.add_paper(root, incoming, metadata)


def test_import_preflights_missing_presentation_markers_before_writes(tmp_path: Path) -> None:
    root = tmp_path / "site"
    write_paper_fixture(root)
    incoming = tmp_path / "incoming.pdf"
    incoming.write_bytes(pdf_bytes())
    row = paper_row("second", featured=False)
    metadata = tmp_path / "metadata.json"
    metadata.write_bytes(encoded({key: value for key, value in row.items() if key not in {"pdf", "tex"}}))
    (root / "README.md").write_text("missing generated boundaries")
    snapshot = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        papers.add_paper(root, incoming, metadata)
    assert {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()} == snapshot


def test_catalog_accepts_honest_month_precision_when_original_has_no_day():
    value = catalog(paper_row())
    value["papers"][0]["date"] = "2026-10"
    assert papers.parse_catalog(json.dumps(value).encode())["papers"][0]["date"] == "2026-10"


@pytest.mark.parametrize(
    "target",
    [
        "README.md",
        "docs/index.html",
        "docs/research-papers.json",
        "alpha_factory_v1/demos/catalog.json",
        "docs/assets/leak.js",
    ],
)
def test_preview_render_refuses_symlink_inputs_before_reading_secrets(tmp_path, target):
    root = tmp_path / "repo"
    root.mkdir()
    write_paper_fixture(root)
    secret = tmp_path / "private"
    secret.write_text("PRIVATE DO NOT COPY")
    path = root / target
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    path.symlink_to(secret)
    with pytest.raises(ValueError, match="symlink"):
        papers.render(root)
    assert secret.read_text() == "PRIVATE DO NOT COPY"


@pytest.mark.parametrize(
    "uri", ["https://example.invalid/track", "http://example.invalid", "mailto:author@example.org"]
)
def test_pdf_rejects_automatic_external_open_action(uri: str) -> None:
    def edit(writer: PdfWriter) -> None:
        writer._root_object[NameObject("/OpenAction")] = action("/URI", **{"/URI": TextStringObject(uri)})

    with pytest.raises(ValueError, match="Automatic PDF navigation"):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize("as_array", [False, True])
@pytest.mark.parametrize("depth", [1, 3])
def test_pdf_rejects_automatic_external_navigation_in_every_next_chain(as_array: bool, depth: int) -> None:
    def edit(writer: PdfWriter) -> None:
        following = writer._add_object(action("/URI", **{"/URI": TextStringObject("https://example.invalid/track")}))
        for _ in range(depth):
            following = writer._add_object(
                action(
                    "/GoTo",
                    **{
                        "/D": TextStringObject("local-section"),
                        "/Next": ArrayObject([following]) if as_array else following,
                    },
                )
            )
        writer._root_object[NameObject("/OpenAction")] = following

    with pytest.raises(ValueError, match="Automatic PDF navigation"):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


def test_pdf_rejects_automatic_action_cycles() -> None:
    def edit(writer: PdfWriter) -> None:
        following = writer._add_object(action("/GoTo", **{"/D": TextStringObject("local-section")}))
        following.get_object()[NameObject("/Next")] = following
        writer._root_object[NameObject("/OpenAction")] = following

    with pytest.raises(ValueError, match="cyclic"):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


def test_pdf_rejects_acroform_text_field_without_active_actions() -> None:
    def edit(writer: PdfWriter) -> None:
        field = DictionaryObject({NameObject("/FT"): NameObject("/Tx"), NameObject("/T"): TextStringObject("name")})
        writer._root_object[NameObject("/AcroForm")] = DictionaryObject(
            {NameObject("/Fields"): ArrayObject([writer._add_object(field)])}
        )

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize("placement", ["typed-filespec", "untyped-filespec", "attachment", "external-stream"])
@pytest.mark.parametrize("indirect_filename", [False, True])
def test_pdf_rejects_external_file_references_without_embedded_payload(placement: str, indirect_filename: bool) -> None:
    def edit(writer: PdfWriter) -> None:
        filename = TextStringObject("file:///etc/passwd")
        descriptor = DictionaryObject(
            {NameObject("/F"): writer._add_object(filename) if indirect_filename else filename}
        )
        if placement != "untyped-filespec":
            descriptor[NameObject("/Type")] = NameObject("/Filespec")
        if placement == "attachment":
            annotation = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Annot"),
                    NameObject("/Subtype"): NameObject("/FileAttachment"),
                    NameObject("/FS"): writer._add_object(descriptor),
                }
            )
            writer.pages[0][NameObject("/Annots")] = ArrayObject([writer._add_object(annotation)])
        elif placement == "external-stream":
            stream = DecodedStreamObject()
            stream.set_data(b"")
            stream[NameObject("/F")] = writer._add_object(descriptor)
            writer._root_object[NameObject("/Extra")] = writer._add_object(stream)
        else:
            writer._root_object[NameObject("/Extra")] = writer._add_object(descriptor)

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


def test_pdf_c2pa_exception_cannot_add_external_file_target() -> None:
    def edit(writer: PdfWriter) -> None:
        c2pa_attachment(writer)
        descriptor = writer._root_object["/AF"][0].get_object()
        descriptor[NameObject("/F")] = TextStringObject("https://example.invalid/payload")

    with pytest.raises(ValueError):
        papers.verify_pdf(pdf_bytes(edit=edit), "Fixture paper")


@pytest.mark.parametrize("row", papers.load_catalog()["papers"], ids=lambda row: row["id"])
def test_all_repository_pdfs_pass_without_rewriting_originals(row: dict[str, Any]) -> None:
    path = papers.ROOT / row["pdf"]["path"]
    original = path.read_bytes()
    papers.verify_pdf(original, row["pdf_title"])
    assert path.read_bytes() == original
    assert hashlib.sha256(original).hexdigest() == row["pdf"]["sha256"]
