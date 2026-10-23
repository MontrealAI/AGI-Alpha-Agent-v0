# SPDX-License-Identifier: Apache-2.0
"""Reading guides bind originals and link the existing implementations."""

import copy
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from scripts.generate_research_editions import EDITIONS, generate
from scripts.research_papers import load_catalog, resource_records

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.targets.extend(value for key, value in attrs if key == "href" and value)


@pytest.mark.parametrize("edition", EDITIONS, ids=lambda edition: edition["directory"])
def test_edition_has_original_downloads_and_existing_journey(edition: dict[str, Any]) -> None:
    rows = {row["id"]: row for row in load_catalog(ROOT)["papers"]}
    row = rows[edition["id"]]
    binding = row["resources"]["reading"]
    path = ROOT / binding["path"]
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == binding["sha256"]
    page = raw.decode()
    assert 'data-language="en" lang="en"' in page
    assert 'data-language="fr" lang="fr"' in page
    assert "<noscript>" in page and "skip" in page
    assert "grid-template-columns:1fr" in page
    links = Links()
    links.feed(page)
    assert edition["journey"] in links.targets
    for kind in ("pdf", "tex"):
        assert "../../" + row[kind]["path"].removeprefix("docs/") in links.targets
    for _, _, target in edition["downloads"]:
        assert target in links.targets
    for target in links.targets:
        parsed = urlsplit(target)
        if parsed.scheme:
            assert parsed.scheme == "https" and parsed.hostname in {"github.com", "raw.githubusercontent.com"}
        elif parsed.path:
            local = (path.parent / parsed.path).resolve()
            assert local.is_relative_to(ROOT / "docs")
            assert local.is_file() or (local / "index.html").is_file(), target


def test_edition_generator_and_catalogue_identities_are_current() -> None:
    generate(ROOT, check=True)
    rows = {row["id"]: row for row in load_catalog(ROOT)["papers"]}
    # A reading action retains the same closed local-HTML boundary as experiences.
    resource = copy.deepcopy(rows[EDITIONS[0]["id"]]["resources"]["reading"])
    for bad_path in ("docs/reports/../index.html", "https://example.com/guide.html", "docs/reports/guide/run.py"):
        with pytest.raises(ValueError):
            resource_records({"reading": {**resource, "path": bad_path}})
