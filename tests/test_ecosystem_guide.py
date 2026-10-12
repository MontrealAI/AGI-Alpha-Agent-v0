# SPDX-License-Identifier: Apache-2.0
"""Guard the static public contract directory against omissions and misleading links."""
from __future__ import annotations

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from scripts import generate_ecosystem as guide


def test_browser_probe_expressions_have_valid_javascript_syntax() -> None:
    """Compile the actual browser probes before expensive hosted gallery acceptance."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to check browser probe syntax")
    module = ast.parse((guide.ROOT / "scripts/validate_ecosystem.py").read_text())
    expressions = []
    for call in ast.walk(module):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "inspect"
            and len(call.args) > 1
        ):
            continue
        try:
            expression = ast.literal_eval(call.args[1])
        except (ValueError, TypeError):
            continue
        if isinstance(expression, str):
            expressions.append(expression)
    assert expressions
    result = subprocess.run(
        [
            node,
            "-e",
            "const vm = require('node:vm'); const fs = require('node:fs'); "
            "for (const expression of JSON.parse(fs.readFileSync(0, 'utf8'))) new vm.Script(expression);",
        ],
        input=json.dumps(expressions),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


class DirectoryLinks(HTMLParser):
    """Read the shipped HTML without executing its optional enhancements."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.text: list[str] = []
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(str(attributes["href"]))
        if tag == "h1":
            self.h1_count += 1

    def handle_data(self, data: str) -> None:
        self.text.append(data)


@pytest.fixture
def guide_root(tmp_path: Path) -> Path:
    for relative in (
        "docs/assets/ecosystem/contracts.json",
        "deployments/ethereum-mainnet/2026-10-11/manifest.json",
        "alpha_factory_v1/demos/catalog.json",
        "scripts/templates/ecosystem-en.html",
        "scripts/templates/ecosystem-fr.html",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(guide.ROOT / relative, destination)
    return tmp_path


@pytest.mark.parametrize("language", ["en", "fr"])
def test_every_recorded_address_and_evidence_link_is_readable_without_javascript(
    guide_root: Path, language: str
) -> None:
    guide.build(guide_root)
    data = json.loads((guide_root / "docs/assets/ecosystem/contracts.json").read_text())
    page = guide_root / "docs/ecosystem" / ("fr/index.html" if language == "fr" else "index.html")
    parser = DirectoryLinks()
    parser.feed(page.read_text())
    text = " ".join(parser.text)
    contracts = data["alpha"]["contracts"] + data["jobs"]["contracts"]
    expected = {data["token"]["address"], *(contract["address"] for contract in contracts)}
    explorer_links = {link for link in parser.links if link.startswith("https://etherscan.io/address/")}
    assert explorer_links == {f"https://etherscan.io/address/{address}#code" for address in expected}
    for contract in contracts:
        assert contract["name"] in text
        assert contract["address"] in text
        assert contract["purpose"][language] in text
    for suite in ("alpha", "jobs"):
        assert data[suite]["source"] in parser.links
        assert re.search(r"/blob/[0-9a-f]{40}/", data[suite]["source"])
    assert parser.h1_count == 1
    assert data["token"]["address"] in text
    assert "docs/DISCLAIMER_SNIPPET.md" in text
    assert "{{" not in page.read_text()


@pytest.mark.parametrize("corruption", ["network", "token", "omission", "duplicate", "alpha_archive"])
def test_generation_refuses_an_inconsistent_public_directory(guide_root: Path, corruption: str) -> None:
    path = guide_root / "docs/assets/ecosystem/contracts.json"
    data = json.loads(path.read_text())
    if corruption == "network":
        data["chainId"] = 11155111
    elif corruption == "token":
        data["token"]["address"] = "0x" + "1" * 40
    elif corruption == "omission":
        data["jobs"]["contracts"].pop()
    elif corruption == "duplicate":
        data["jobs"]["contracts"][0]["address"] = data["alpha"]["contracts"][0]["address"]
    else:
        data["alpha"]["contracts"][0]["address"] = "0x" + "1" * 40
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        guide.build(guide_root)
    assert not (guide_root / "docs/ecosystem/index.html").exists()


def test_regeneration_keeps_the_published_directory_deterministic(guide_root: Path) -> None:
    guide.build(guide_root)
    paths = [guide_root / "docs/ecosystem/index.html", guide_root / "docs/ecosystem/fr/index.html"]
    before = [path.read_bytes() for path in paths]
    guide.build(guide_root)
    assert before == [path.read_bytes() for path in paths]
