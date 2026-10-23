# SPDX-License-Identifier: Apache-2.0
"""Validate immutable research originals and render their small bilingual presentation.

Paper text is data, never a template or program. TEX is stored, never compiled.
"""

from __future__ import annotations

# Exact builtin schema types reject numeric coercion and subclasses (E721 sites below).

import argparse
from datetime import date
import hashlib
from html import escape
import io
import json
from pathlib import Path
import re
import shutil
import unicodedata
from typing import Any

CATALOG = "docs/research-papers.json"
SCHEMA = "agialpha.research-papers.v1"
RESOURCE_SCHEMA = "agialpha.research-papers.v2"
MAX_CATALOG = 512_000
MAX_PAPER = 25_000_000
MAX_EXPERIENCE = 25_000_000
MAX_COMPANION = (2**31) - 1
ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SITE = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
RELEASE_SITE = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/"
SOURCE_SITE = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/"
RESOURCE_LABELS = {
    "reading": {"en": "Read the edition and resources", "fr": "Lire l’édition et ses ressources"},
    "tex_source": {"en": "Download standalone TeX", "fr": "Télécharger le TeX autonome"},
    "experimental_source": {
        "en": "Experimental companion source and assembly (unmerged)",
        "fr": "Sources et assemblage du compagnon expérimental (non fusionné)",
    },
    "experience": {"en": "Explore the interactive foundry", "fr": "Explorer la fonderie interactive"},
    "companion": {"en": "Download the research companion", "fr": "Télécharger le compagnon de recherche"},
    "source_archive": {
        "en": "Download complete research source ZIP",
        "fr": "Télécharger les sources de recherche complètes ZIP",
    },
    "visual_signature": {
        "en": "Download visual signature (not cryptographic)",
        "fr": "Télécharger la signature visuelle (non cryptographique)",
    },
    "source_evidence": {"en": "View source and evidence", "fr": "Consulter les sources et les preuves"},
}
README_START = "<!-- featured-research-papers -->"
README_END = "<!-- /featured-research-papers -->"
HTML_START = "<!-- research-papers:start -->"
HTML_END = "<!-- research-papers:end -->"
RECORD_KEYS = {
    "id",
    "title",
    "display_title",
    "title_words",
    "symbol",
    "subtitle",
    "author",
    "date",
    "language",
    "featured",
    "topic",
    "summary",
    "pdf_title",
    "pdf",
    "tex",
}


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate catalog key: {key}")
        result[key] = value
    return result


def plain(value: Any, maximum: int = 1200, *, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not value.strip() and not empty):
        raise ValueError("Invalid bounded paper text")
    if any(unicodedata.category(c) in {"Cc", "Cs"} for c in value):
        raise ValueError("Control characters are not paper text")
    return value


def file_record(value: Any, suffix: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise ValueError("Invalid paper file record")
    path = value["path"]
    if not isinstance(path, str) or not re.fullmatch(
        r"docs/(?:papers/)?[A-Za-z0-9][A-Za-z0-9_-]{0,119}" + re.escape(suffix), path
    ):
        raise ValueError("Paper paths must be simple, relative PDF/TEX names")
    if not isinstance(value["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
        raise ValueError("Invalid paper digest")
    return value


def resource_records(value: Any) -> dict[str, Any]:
    """Validate closed navigation metadata, without fetching or executing targets."""
    if not isinstance(value, dict) or not value or set(value) - RESOURCE_LABELS.keys():
        raise ValueError("Unexpected research resource roles")
    for role, item in value.items():
        if not isinstance(item, dict):
            raise ValueError("Invalid research resource record")
        expected = {
            "reading": {"path", "sha256"},
            "tex_source": {"path", "sha256"},
            "experimental_source": {"url"},
            "experience": {"path", "sha256"},
            "companion": {"url", "sha256", "bytes"},
            "source_archive": {"url", "sha256", "bytes"},
            "visual_signature": {"url", "sha256", "bytes"},
            "source_evidence": {"url"},
        }[role]
        if set(item) != expected:
            raise ValueError("Unexpected research resource fields")
        if role == "tex_source":
            file_record(item, ".tex")
            continue
        if role == "experimental_source":
            if not isinstance(item["url"], str) or not re.fullmatch(
                re.escape(SOURCE_SITE) + r"[0-9a-f]{40}/studies/[a-z][a-z0-9-]{0,63}/README\.md", item["url"]
            ):
                raise ValueError("Experimental source requires a commit-pinned study README in this repository")
            continue
        if role in {"reading", "experience"}:
            if not isinstance(item["path"], str) or not re.fullmatch(
                r"docs/reports/[a-z][a-z0-9-]{0,63}/[A-Za-z0-9][A-Za-z0-9_-]{0,119}\.html", item["path"]
            ):
                raise ValueError("Research experiences require a simple versioned local HTML path")
        else:
            tag = r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}"
            route = "tag/" + tag
            if role in {"companion", "source_archive"}:
                route = "download/" + tag + r"/[A-Za-z0-9][A-Za-z0-9._-]{0,179}\.zip"
            elif role == "visual_signature":
                route = "download/" + tag + r"/[A-Za-z0-9][A-Za-z0-9._-]{0,179}\.png"
            if not isinstance(item["url"], str) or not re.fullmatch(re.escape(RELEASE_SITE) + route, item["url"]):
                raise ValueError("Research resources require a canonical release URL in this repository")
        if role != "source_evidence" and (
            not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        ):
            raise ValueError("Invalid research resource digest")
        if role in {"companion", "source_archive", "visual_signature"} and (
            type(item["bytes"]) is not int  # noqa: E721
            or not 0 < item["bytes"] <= (MAX_PAPER if role == "visual_signature" else MAX_COMPANION)
        ):
            raise ValueError("Invalid bounded research companion size")
    if "source_evidence" in value:
        for role in ("companion", "source_archive", "visual_signature"):
            if role in value:
                download_tag = value[role]["url"].removeprefix(RELEASE_SITE + "download/").split("/")[0]
                if value["source_evidence"]["url"] != RELEASE_SITE + "tag/" + download_tag:
                    raise ValueError("Companion and source/evidence must identify the same research release")
    return value


def resource_href(role: str, record: dict[str, Any], *, readme: bool = False) -> str:
    """Return a validated navigation target; local experiences are never paper assets."""
    item = resource_records({role: record})[role]
    if role in {"reading", "experience", "tex_source"}:
        return (PUBLIC_SITE if readme else "") + str(item["path"]).removeprefix("docs/")
    return str(item["url"])


def parse_catalog(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_CATALOG:
        raise ValueError("Paper catalog exceeds size limit")
    data = json.loads(raw, object_pairs_hook=unique_object)
    if (
        not isinstance(data, dict)
        or set(data) != {"schema", "papers"}
        or not isinstance(data["schema"], str)
        or data["schema"] not in {SCHEMA, RESOURCE_SCHEMA}
    ):
        raise ValueError("Unsupported paper catalog")
    rows = data["papers"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("Paper catalog must contain 1–100 records")
    identifiers: set[str] = set()
    paths: set[str] = set()
    experiences: dict[str, tuple[str, str]] = {}
    companions: dict[str, tuple[str, int]] = {}
    featured = 0
    for row in rows:
        allowed = RECORD_KEYS | ({"resources"} if data["schema"] == RESOURCE_SCHEMA else set())
        if not isinstance(row, dict) or not RECORD_KEYS <= set(row) or set(row) - allowed:
            raise ValueError("Unexpected paper fields")
        if "resources" in row:
            resources = resource_records(row["resources"])
            for role in ("reading", "experience"):
                if role not in resources:
                    continue
                item = resources[role]
                key = item["path"].casefold()
                identity = (item["path"], item["sha256"])
                if key in experiences and experiences[key] != identity:
                    raise ValueError("Ambiguous research experience identity")
                experiences[key] = identity
            for role in ("companion", "source_archive", "visual_signature"):
                if role not in resources:
                    continue
                item = resources[role]
                companion_identity = (item["sha256"], item["bytes"])
                if item["url"] in companions and companions[item["url"]] != companion_identity:
                    raise ValueError("Ambiguous research companion identity")
                companions[item["url"]] = companion_identity
        slug = row["id"]
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", slug) or slug in identifiers:
            raise ValueError("Invalid or duplicate paper ID")
        identifiers.add(slug)
        for key in ("title", "display_title", "author", "pdf_title"):
            plain(row[key], 400)
        for key in ("symbol", "subtitle"):
            plain(row[key], 400, empty=True)
        words = row["title_words"]
        if not isinstance(words, list) or len(words) > 10:
            raise ValueError("Invalid display title words")
        for word in words:
            plain(word, 100)
        if row["language"] != "en" or type(row["featured"]) is not bool:  # noqa: E721
            raise ValueError("This presentation supports English originals and bilingual descriptions")
        featured += row["featured"]
        publication_date = row["date"]
        if not isinstance(publication_date, str) or not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", publication_date):
            raise ValueError("Invalid paper publication date")
        date.fromisoformat(publication_date + "-01" if len(publication_date) == 7 else publication_date)
        for key in ("topic", "summary"):
            if not isinstance(row[key], dict) or set(row[key]) != {"en", "fr"}:
                raise ValueError("Both English and French paper text are required")
            for value in row[key].values():
                plain(value, 1200 if key == "summary" else 150)
        for key, suffix in (("pdf", ".pdf"), ("tex", ".tex")):
            if row[key] is None and key == "tex":
                continue
            item = file_record(row[key], suffix)
            if item["path"].casefold() in paths:
                raise ValueError("Duplicate or case-ambiguous paper path")
            paths.add(item["path"].casefold())
        if "tex_source" in row.get("resources", {}) and row["resources"]["tex_source"] != row["tex"]:
            raise ValueError("Standalone TeX navigation must match the paper's exact original")
    if featured != 1 or not rows[0]["featured"]:
        raise ValueError("Exactly the first paper must be featured")
    return data


def ordinary_path(root: Path, relative: str, *, must_exist: bool = True) -> Path:
    """Do not follow repository-provided symlinks while inspecting/rendering data."""
    current = root
    for part in Path(relative).parts:
        if part in {".", ".."}:
            raise ValueError("Unsafe paper path")
        current = current / part
        if current.is_symlink():
            raise ValueError("Paper rendering cannot follow symlinks")
    if must_exist and (not current.is_file() or current.stat().st_mode & 0o111):
        raise ValueError("Paper rendering requires ordinary non-executable files")
    return current


def load_catalog(root: Path = ROOT) -> dict[str, Any]:
    path = ordinary_path(root, CATALOG)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CATALOG:
        raise ValueError("Catalog must be a bounded ordinary file")
    return parse_catalog(path.read_bytes())


def asset_hashes(catalog: dict[str, Any]) -> dict[str, str]:
    return {row[key]["path"]: row[key]["sha256"] for row in catalog["papers"] for key in ("pdf", "tex") if row[key]}


def pdf_hashes(catalog: dict[str, Any]) -> dict[str, str]:
    return {row["pdf"]["path"].removeprefix("docs/"): row["pdf"]["sha256"] for row in catalog["papers"]}


def experience_hashes(catalog: dict[str, Any]) -> dict[str, str]:
    """Identify declared reading/experience pages separately from paper originals."""
    return {
        row["resources"][role]["path"]: row["resources"][role]["sha256"]
        for row in catalog["papers"]
        for role in ("reading", "experience")
        if role in row.get("resources", {})
    }


def preserve_catalog(previous: dict[str, Any], current: dict[str, Any]) -> None:
    """Published IDs and original file identities cannot be removed or retargeted."""
    old = {row["id"]: row for row in previous["papers"]}
    new = {row["id"]: row for row in current["papers"]}
    if not old.keys() <= new.keys():
        raise ValueError("Historical paper IDs must remain present")
    for slug, row in old.items():
        for key in ("pdf", "tex"):
            if row[key] is not None and new[slug][key] != row[key]:
                raise ValueError("Historical paper paths and bytes are immutable; add a versioned record")
        for role, resource in row.get("resources", {}).items():
            if new[slug].get("resources", {}).get(role) != resource:
                raise ValueError("Historical research resource identities are immutable; add a versioned record")
    for slug, row in new.items():
        for key in ("pdf", "tex"):
            if row[key] and (slug not in old or old[slug][key] is None):
                if not row[key]["path"].startswith("docs/papers/"):
                    raise ValueError("New paper files belong under docs/papers with versioned names")


def normalized_title(value: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold(), re.UNICODE))


def verify_pdf(raw: bytes, expected_title: str) -> None:
    """Parse, never rewrite; allow ordinary academic links and local view destinations."""
    from pypdf import PdfReader
    from pypdf.generic import (
        ArrayObject,
        ByteStringObject,
        DictionaryObject,
        FloatObject,
        IndirectObject,
        NameObject,
        NullObject,
        NumberObject,
        StreamObject,
        TextStringObject,
    )

    if not raw.startswith(b"%PDF-") or len(raw) > MAX_PAPER:
        raise ValueError("Invalid or oversized PDF")
    reader = PdfReader(io.BytesIO(raw), strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 1000:
        raise ValueError("Paper must be an unencrypted bounded PDF")
    metadata_title = str(reader.metadata.title or "") if reader.metadata else ""
    if not normalized_title(expected_title) or normalized_title(expected_title) != normalized_title(metadata_title):
        raise ValueError("PDF title metadata differs from the catalog")
    forbidden = {"/JS", "/JavaScript", "/RichMedia", "/XFA", "/AA", "/AcroForm", "/FT", "/FS", "/RF"}

    def local_destination(destination: Any) -> bool:
        destination = destination.get_object()
        if isinstance(destination, (NameObject, TextStringObject, ByteStringObject)):
            return bool(destination)
        if not isinstance(destination, ArrayObject) or not 2 <= len(destination) <= 6:
            return False
        page = destination[0].get_object()
        return (
            isinstance(page, DictionaryObject)
            and page.get("/Type") == "/Page"
            and isinstance(destination[1], NameObject)
            and destination[1] in {"/Fit", "/FitB", "/FitH", "/FitBH", "/FitV", "/FitBV", "/FitR", "/XYZ"}
            and all(isinstance(item.get_object(), (NumberObject, FloatObject, NullObject)) for item in destination[2:])
        )

    def verify_open_action(open_action: Any) -> None:
        # Initial navigation runs automatically, unlike a user-clicked academic link.
        # Every chained action must also remain within this document.
        actions: list[tuple[Any, bool]] = [(open_action, True)]
        seen_actions: set[int] = set()
        while actions:
            candidate, initial = actions.pop()
            candidate = candidate.get_object()
            if initial and local_destination(candidate):
                continue
            if (
                not isinstance(candidate, DictionaryObject)
                or candidate.get("/S") != "/GoTo"
                or "/D" not in candidate
                or not local_destination(candidate["/D"])
            ):
                raise ValueError("Automatic PDF navigation must use local destinations only")
            if id(candidate) in seen_actions or len(seen_actions) >= 1000:
                raise ValueError("Automatic PDF action chain is cyclic or oversized")
            seen_actions.add(id(candidate))
            if "/Next" in candidate:
                following = candidate["/Next"].get_object()
                actions.extend(
                    (item, False) for item in (following if isinstance(following, ArrayObject) else [following])
                )

    active_actions = {
        "/JavaScript",
        "/Launch",
        "/SubmitForm",
        "/ImportData",
        "/GoToR",
        "/GoToE",
        "/Rendition",
        "/Movie",
        "/Sound",
    }
    pending: list[Any] = [reader.trailer["/Root"]]
    visited: set[tuple[int, int]] = set()
    count = 0
    while pending:
        value = pending.pop()
        count += 1
        if count > 200_000:
            raise ValueError("PDF object graph exceeds validation bounds")
        if isinstance(value, IndirectObject):
            object_identity = (value.idnum, value.generation)
            if object_identity in visited:
                continue
            visited.add(object_identity)
            pending.append(value.get_object())
        elif isinstance(value, DictionaryObject):
            if "/OpenAction" in value:
                verify_open_action(value["/OpenAction"])
            file_descriptor = (
                value.get("/Type") == "/Filespec"
                or any(key in value for key in ("/UF", "/DOS", "/Mac", "/Unix"))
                or "/F" in value
                and isinstance(value["/F"], (TextStringObject, ByteStringObject))
            )
            if file_descriptor and "/EF" not in value or isinstance(value, StreamObject) and "/F" in value:
                raise ValueError("External PDF file references are forbidden")
            if "/EF" in value:
                # Passive C2PA provenance is present in the preserved Out-Evolve original.
                # It is not a program, file-launch target, or permission to trust its claims.
                embedded_files = value["/EF"].get_object()
                if (
                    not isinstance(embedded_files, DictionaryObject)
                    or value.get("/Type") != "/Filespec"
                    or value.get("/AFRelationship") != "/C2PA_Manifest"
                    or value.get("/Subtype") != "application/c2pa"
                    or set(embedded_files) != {"/F"}
                    or not set(value) <= {"/Type", "/AFRelationship", "/Desc", "/F", "/UF", "/EF", "/Subtype"}
                    or any(
                        not isinstance(value[key], TextStringObject)
                        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,127}", str(value[key]))
                        for key in ("/F", "/UF")
                        if key in value
                    )
                ):
                    raise ValueError("Arbitrary embedded PDF files are forbidden")
                embedded = embedded_files["/F"].get_object()
                if (
                    not isinstance(embedded, StreamObject)
                    or embedded.get("/Type") != "/EmbeddedFile"
                    or embedded.get("/Subtype") != "/application/c2pa"
                ):
                    raise ValueError("Invalid passive PDF content credentials")
            if value.get("/Type") == "/EmbeddedFile":
                if (
                    not isinstance(value, StreamObject)
                    or value.get("/Subtype") != "/application/c2pa"
                    or "/Filter" in value
                ):
                    raise ValueError("Unsupported embedded PDF stream")
                payload = value.get_data()
                if len(payload) > 2_000_000 or payload[4:8] != b"jumb" or b"c2pa" not in payload[:64]:
                    raise ValueError("Invalid bounded C2PA metadata stream")
            if value.get("/Subtype") in {
                "/RichMedia",
                "/Movie",
                "/Sound",
                "/Screen",
                "/3D",
                "/Widget",
                "/FileAttachment",
            }:
                raise ValueError("Active PDF annotations are forbidden")
            if forbidden.intersection(value) or value.get("/S") in active_actions:
                raise ValueError("Active or embedded PDF behavior is forbidden")
            if (
                value.get("/Type") == "/Action"
                or "/S" in value
                and any(key in value for key in ("/D", "/URI", "/Next", "/T", "/H"))
            ) and value.get("/S") not in {"/GoTo", "/URI"}:
                raise ValueError("Unsupported PDF action")
            if "/URI" in value:
                uri = str(value["/URI"])
                if not re.match(r"^(?:https?://|mailto:)", uri, re.IGNORECASE):
                    raise ValueError("Unsafe PDF link scheme")
            for key in ("/OpenAction", "/A") + (("/Next",) if value.get("/S") in {"/GoTo", "/URI"} else ()):
                action = value.get(key)
                if action is not None:
                    action = action.get_object()
                    actions = list(action) if key == "/Next" and isinstance(action, ArrayObject) else [action]
                    for candidate in actions:
                        candidate = candidate.get_object()
                        if (
                            isinstance(candidate, DictionaryObject)
                            and candidate.get("/S") not in {"/GoTo", "/URI"}
                            or key == "/Next"
                            and not isinstance(candidate, DictionaryObject)
                        ):
                            raise ValueError("Unsupported PDF action")
            pending.extend(value.values())
        elif isinstance(value, ArrayObject):
            pending.extend(value)


def verify_files(root: Path, catalog: dict[str, Any], *, pdf_checks: bool = True) -> None:
    for row in catalog["papers"]:
        for kind in ("pdf", "tex"):
            item = row[kind]
            if item is None:
                continue
            path = root / item["path"]
            if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file():
                raise ValueError("Paper files cannot contain symlinks")
            if path.stat().st_mode & 0o111 or not 0 < path.stat().st_size <= MAX_PAPER:
                raise ValueError("Paper files must be bounded and non-executable")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError(
                    f"Paper digest mismatch: {item['path']}. Original bytes are required; "
                    "local edits, corruption, or an older text-converting checkout may be responsible. "
                    "Preserve this worktree and see docs/agent/PAPER_UPLOADS.md#recovering-a-byte-mismatched-checkout."
                )
            if kind == "pdf":
                if not raw.startswith(b"%PDF-"):
                    raise ValueError("Catalog PDF is not a PDF")
                if pdf_checks:
                    verify_pdf(raw, row["pdf_title"])
            else:
                raw.decode("utf-8")  # Opaque downloadable source, never evaluated or compiled.
    for name, expected in experience_hashes(catalog).items():
        path = ordinary_path(root, name)
        if not 0 < path.stat().st_size <= MAX_EXPERIENCE:
            raise ValueError("Research experience exceeds the declared local-file bound")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Research experience differs from its catalogued source: {name}")
        raw.decode("utf-8")  # Hash-check the code as text; this does not qualify or execute it.


def translated(tag: str, key: str, text: dict[str, str], attrs: str = "") -> str:
    french = escape(text["fr"], quote=True)
    english = escape(text["en"])
    return f'<{tag}{attrs} data-paper-key="{key}" data-paper-fr="{french}">{english}</{tag}>'


def render_section(catalog: dict[str, Any]) -> str:
    lines = [
        '<section class="papers-section welcome-wrap" id="papers" aria-labelledby="papers-title">',
        '  <div class="papers-heading">',
        '    <p class="welcome-eyebrow" data-home-key="papers-eyebrow">THE RESEARCH</p>',
        '    <h2 id="papers-title" data-home-key="papers-title">'
        "Better strategies. A different game. New capabilities.</h2>",
        '    <p data-home-key="papers-intro">Research manuscripts on changing the conditions of success, '
        "while preserving the purpose of the work.</p>",
        "  </div>",
        '  <nav class="papers-index" aria-labelledby="papers-index-title">',
        '    <p id="papers-index-title" data-home-key="papers-index-title">Choose your reading path</p>',
    ]
    lead = catalog["papers"][0]
    lines.append(
        f'    <a class="papers-foundation" href="#paper-{lead["id"]}-title" lang="en">'
        + escape(lead["display_title"])
        + "</a>"
    )
    if len(catalog["papers"]) > 1:
        lines.append('    <ol class="papers-mission-list">')
        for row in catalog["papers"][1:]:
            lines.append(
                f'      <li><a href="#paper-{row["id"]}-title" lang="en">' + escape(row["display_title"]) + "</a></li>"
            )
        lines.append("    </ol>")
    lines.extend(["  </nav>", '  <div class="papers-grid">'])
    for index, row in enumerate(catalog["papers"]):
        slug = row["id"]
        extra = " paper-featured" if row["featured"] else ""
        lines.append(f'    <article class="paper-card{extra}" aria-labelledby="paper-{slug}-title">')
        lines.append("      " + translated("p", f"{slug}-topic", row["topic"], ' class="paper-topic"'))
        title = escape(row["display_title"])
        if row["title_words"]:
            title = " ".join(
                '<span class="paper-title-word">' + escape(word).replace("\u00ad", "&shy;") + "</span>"
                for word in row["title_words"]
            )
            if row["symbol"]:
                title += ' <span class="paper-infinity">' + escape(row["symbol"]) + "</span>"
        lines.append(f'      <h3 id="paper-{slug}-title" lang="en" tabindex="-1">{title}</h3>')
        if row["subtitle"]:
            lines.append('      <p class="paper-subtitle" lang="en">' + escape(row["subtitle"]) + "</p>")
        lines.append("      " + translated("p", f"{slug}-summary", row["summary"]))
        read = {
            "en": "Read the featured paper" if row["featured"] else "Read the paper",
            "fr": "Lire la publication à la une" if row["featured"] else "Lire la publication",
        }
        link = row["pdf"]["path"].removeprefix("docs/")
        lines.append(
            f'      <a class="paper-link" href="{link}" type="application/pdf" hreflang="en">'
            + translated("span", f"{slug}-read", read)
            + '<span class="sr-only" lang="en">: '
            + escape(row["title"])
            + "</span>"
            + translated(
                "span", f"{slug}-format", {"en": "English PDF", "fr": "PDF en anglais"}, ' class="paper-format"'
            )
            + '<span aria-hidden="true">↗</span></a>'
        )
        for role, labels in RESOURCE_LABELS.items():
            if role not in row.get("resources", {}):
                continue
            href = resource_href(role, row["resources"][role])
            lines.append(
                f'      <a class="paper-resource-link" data-paper-resource="{role}" href="{escape(href, quote=True)}">'
                + translated("span", f"{slug}-{role}", labels)
                + '<span class="sr-only" lang="en">: '
                + escape(row["title"])
                + '</span><span aria-hidden="true">↗</span></a>'
            )
        lines.append("    </article>")
    lines.extend(
        [
            "  </div>",
            '  <p class="papers-note" data-home-key="papers-note">English originals. '
            "Research proposals and bounded studies, not claims of general autonomous capability "
            "or physical deployment.</p>",
            "</section>",
        ]
    )
    return "\n".join(lines)


def markdown_text(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", escape(text, quote=False))


def render_readme(catalog: dict[str, Any]) -> str:
    lines = ["## Featured research", ""]
    for row in catalog["papers"]:
        target = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/" + row["pdf"]["path"]
        if row["featured"]:
            lines.extend(
                [
                    f"### [{markdown_text(row['display_title'])}]({target})",
                    "",
                    f"**{markdown_text(row['subtitle'])}**" if row["subtitle"] else "**The foundation**",
                    "",
                    markdown_text(row["summary"]["en"]),
                    f"{markdown_text(row['author'])} · {row['date']} · English PDF.",
                    "",
                ]
            )
            if len(catalog["papers"]) > 1:
                lines.extend(["**Companion papers · reading order**", ""])
        else:
            lines.append(
                f"- **[{markdown_text(row['display_title'])}]({target})** · {markdown_text(row['summary']['en'])}"
            )
            lines.append(f"  {markdown_text(row['author'])} · {row['date']} · English PDF.")
        resources = row.get("resources", {})
        if resources:
            links = [
                f"[{labels['en']}]({resource_href(role, resources[role], readme=True)})"
                for role, labels in RESOURCE_LABELS.items()
                if role in resources
            ]
            lines.append("  " + " · ".join(links))
    lines.extend(
        [
            "",
            "Research proposals and bounded studies, not claims of general autonomous capability "
            "or physical deployment.",
            "[Explore the papers in English or French](https://montrealai.github.io/AGI-Alpha-Agent-v0/#papers)",
        ]
    )
    return "\n".join(lines)


def replace_block(text: str, start: str, end: str, body: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
        raise ValueError("Missing, duplicate, or disordered paper presentation markers")
    before, rest = text.split(start)
    _, after = rest.split(end)
    return before + start + "\n" + body + "\n" + end + after


def rendered_files(root: Path, catalog: dict[str, Any]) -> dict[str, bytes]:
    return {
        "README.md": replace_block(
            ordinary_path(root, "README.md").read_text(), README_START, README_END, render_readme(catalog)
        ).encode(),
        "docs/index.html": replace_block(
            ordinary_path(root, "docs/index.html").read_text(), HTML_START, HTML_END, render_section(catalog)
        ).encode(),
    }


def render(root: Path = ROOT, *, check: bool = False) -> None:
    from scripts.build_service_worker import build, gather_assets, render_scripts

    catalog = load_catalog(root)
    ordinary_path(root, "alpha_factory_v1/demos/catalog.json")
    for name in (
        "docs/service-worker.js",
        "docs/assets/service-worker.js",
        "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
    ):
        ordinary_path(root, name, must_exist=False)
    verify_files(root, catalog, pdf_checks=False)
    for name, raw in rendered_files(root, catalog).items():
        path = root / name
        if check and path.read_bytes() != raw:
            raise ValueError(f"Regenerate paper presentation: {name}")
        if not check:
            path.write_bytes(raw)
    if check:
        release = json.loads((root / "alpha_factory_v1/demos/catalog.json").read_bytes())["release"]
        assets = {name: (root / "docs" / name).read_bytes() for name in gather_assets(root / "docs")}
        for name, script in render_scripts(assets, release).items():
            if (root / "docs" / name).read_bytes() != script.encode():
                raise ValueError(f"Regenerate paper worker: {name}")
    else:
        build(root / "docs")


def add_paper(root: Path, pdf: Path, metadata: Path, tex: Path | None = None) -> None:
    """One local import, preserving bytes. No network writes or TEX execution."""
    catalog = load_catalog(root)
    row = json.loads(metadata.read_bytes(), object_pairs_hook=unique_object)
    required = {"id", "title", "author", "date", "topic", "summary"}
    if (
        not isinstance(row, dict)
        or not required <= set(row)
        or set(row) - ((RECORD_KEYS - {"pdf", "tex"}) | {"resources"})
    ):
        raise ValueError("Metadata requires id/title/author/date/topic/summary and only documented fields")
    from pypdf import PdfReader

    defaults = {
        "display_title": row["title"],
        "title_words": [],
        "symbol": "",
        "subtitle": "",
        "language": "en",
        "featured": False,
    }
    for key, value in defaults.items():
        row.setdefault(key, value)
    for kind, source in (("pdf", pdf), ("tex", tex)):
        row[kind] = None
        if source is not None:
            if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= MAX_PAPER:
                raise ValueError("Input must be a bounded ordinary file")
            raw = source.read_bytes()
            row[kind] = {"path": f"docs/papers/{row['id']}.{kind}", "sha256": hashlib.sha256(raw).hexdigest()}
    if "pdf_title" not in row:
        # Inspect original metadata, never alter or compile the supplied document.
        reader = PdfReader(io.BytesIO(pdf.read_bytes()), strict=True)
        row["pdf_title"] = str(reader.metadata.title or "") if reader.metadata else ""
    schema = RESOURCE_SCHEMA if "resources" in row else catalog["schema"]
    candidate = parse_catalog(json.dumps({"schema": schema, "papers": [*catalog["papers"], row]}).encode())
    preserve_catalog(catalog, candidate)
    for name, expected in experience_hashes(candidate).items():
        target = ordinary_path(root, name)
        if not 0 < target.stat().st_size <= MAX_EXPERIENCE:
            raise ValueError("Research experience exceeds the declared local-file bound")
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Import requires the exact existing catalogued research experience")
        raw.decode("utf-8")  # Reject invalid text before mutating the paper/catalog destinations.
    verify_pdf(pdf.read_bytes(), row["pdf_title"])
    if tex:
        tex.read_bytes().decode("utf-8")
    targets = [(root / row[kind]["path"], source) for kind, source in (("pdf", pdf), ("tex", tex)) if source]
    if any(target.exists() or target.is_symlink() for target, _ in targets):
        raise ValueError("Paper destination already exists; originals are never overwritten")
    if any(part.is_symlink() for target, _ in targets for part in (target, *target.parents)):
        raise ValueError("Paper destination parents cannot contain symlinks")
    rendered_files(root, candidate)  # Validate both presentation boundaries before copying.
    for target, source in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o644)
    (root / CATALOG).write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("command", choices=("check", "render", "add"))
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--tex", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    if args.command == "add":
        if not args.pdf or not args.metadata:
            parser.error("add requires --pdf and --metadata")
        add_paper(args.root, args.pdf, args.metadata, args.tex)
    else:
        verify_files(args.root, load_catalog(args.root))
        render(args.root, check=args.command == "check")


if __name__ == "__main__":
    main()
