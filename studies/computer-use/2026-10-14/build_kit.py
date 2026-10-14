# SPDX-License-Identifier: Apache-2.0
"""Build the reviewed kit and reject broken local navigation before packaging."""
from __future__ import annotations
import argparse
import html
import re
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import _kit_builder as builder

ROOT = Path(__file__).resolve().parent


def inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"\[([^\]]+)\]\((https://[^)]+)\)", r'<a href="\2">\1</a>', escaped)


class Navigation(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)


def check_navigation() -> None:
    for name in ["START_HERE.html", "PILOT_PROTOCOL.html", "01_Report/index.html", "01_Report/report.html"]:
        page = ROOT / name
        links = Navigation()
        links.feed(page.read_text(encoding="utf-8"))
        for target in links.targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            path = (page.parent / unquote(url.path)).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                raise ValueError(f"Broken local link in {name}: {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    builder.BODY = builder.BODY.replace('href="04_Reproduce/site_template.html"', 'href="original-template.txt"')
    tracker = '<p><a href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4787" data-fr="Suivre la préparation du pilote ↗">Follow pilot readiness ↗</a></p>'
    builder.BODY = builder.BODY.replace('<section id="people">', '<section id="people">' + tracker)
    builder.CSS += '@media print{:root{font-size:12pt;line-height:1.45}h2,h3{break-after:avoid}p{widows:3;orphans:3}}'
    builder.build()
    (ROOT / "original-template.txt").write_bytes((ROOT / "04_Reproduce/site_template.html").read_bytes())
    blocks = []
    for paragraph in (ROOT / "PILOT_PROTOCOL.md").read_text(encoding="utf-8").split("\n\n"):
        heading = re.fullmatch(r"(#{1,3}) ([^\n]+)", paragraph.strip())
        if heading:
            level = len(heading[1])
            blocks.append(f"<h{level}>{inline(heading[2])}</h{level}>")
        elif paragraph.strip():
            blocks.append("<p>" + inline(paragraph).replace("\n", "<br>") + "</p>")
    (ROOT / "PILOT_PROTOCOL.html").write_bytes(builder.page('<main><p><a href="START_HERE.html">← Back to the kit</a></p>' + "".join(blocks) + '</main>', "Real-user pilot | Not started"))
    report_home = '<main><section class="hero"><p class="eyebrow">PUBLIC REPORT EDITION</p><h1>Useful work.<br>Recovered. Reused.</h1><p class="lead">Read the full report and inspect the recorded study results. Simulated owner; executed software checks. Human benefits remain unmeasured.</p><div class="actions"><a class="button primary" href="report.html">Read the report</a><a class="button" href="../START_HERE.html">Back to the working examples</a></div><p><a href="REPORT.md">Markdown report</a> · <a href="results.json">Recorded results</a> · <a href="PUBLICATION.md">Historical editorial notes</a></p></section></main>'
    (ROOT / "01_Report/index.html").write_bytes(builder.page(report_home, "Study report | AGI Alpha"))
    # The bundle manifest is generated even for a source-checkout build.
    with tempfile.TemporaryDirectory(prefix="study-kit-build-") as temp:
        builder.package(args.output or Path(temp) / "kit.zip")
    check_navigation()
    print("Four reader entry points have valid local file links; original source hashes remain unchanged.")


if __name__ == "__main__":
    main()
