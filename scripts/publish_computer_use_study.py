#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build and verify the public study edition without touching agent behavior."""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs/reports/computer-use-study"
SOURCES = ("index.html", "study.css", "study.js", "REPORT.md", "results.json", "PUBLICATION.md")
ORIGINAL = "0e9d8a7f3d163f2461af99261d11f464ead71411ae9803074171ac934a123035"
URL = "https://montrealai.github.io/AGI-Alpha-Agent-v0/reports/computer-use-study/"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inline(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)

    def link(match: re.Match[str]) -> str:
        label, target = match.groups()
        if ":" in target and not target.startswith("https://"):
            raise ValueError("Unsupported report link")
        return f'<a href="{target}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, value)


def render_report() -> bytes:
    lines = (STUDY / "REPORT.md").read_text(encoding="utf-8").splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("|"):
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].startswith("|"):
                current = lines[index]
                if not re.fullmatch(r"[| :\-]+", current):
                    rows.append([inline(cell.strip()) for cell in current.strip("|").split("|")])
                index += 1
            head = "".join(f'<th scope="col">{cell}</th>' for cell in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows[1:])
            blocks.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
            continue
        heading = re.match(r"^(#{1,3}) (.+)$", line)
        if heading:
            level = len(heading[1])
            blocks.append(f"<h{level}>{inline(heading[2])}</h{level}>")
        elif line == "---":
            blocks.append("<hr>")
        elif line.startswith("> "):
            blocks.append(f"<blockquote>{inline(line[2:])}</blockquote>")
        else:
            paragraph = [line]
            while index + 1 < len(lines) and lines[index + 1].strip():
                if lines[index + 1].startswith(("#", "|", "> ")):
                    break
                index += 1
                paragraph.append(lines[index])
            blocks.append(f"<p>{inline(' '.join(paragraph))}</p>")
        index += 1
    body = "\n".join(blocks)
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="description" '
        'content="The complete public report edition of the AGI Alpha computer-use study.">'
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'self'; "
        "script-src 'self'; connect-src 'none'; base-uri 'none'; object-src 'none'\">"
        "<title>Full report | AGI Alpha computer-use study</title>"
        '<link rel="stylesheet" href="study.css"><script src="study.js" defer></script></head><body>'
        '<a class="skip" href="#main">Skip to the report</a><header class="shell topbar">'
        '<a class="brand" href="index.html">AGI ALPHA <small>STUDY REPORT</small></a>'
        '<nav aria-label="Report controls"><a class="button" href="index.html">Overview</a>'
        '<button type="button" data-print>Print / Save PDF</button></nav></header>'
        f'<main id="main" class="shell reader">{body}</main>'
        '<footer class="shell"><a href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/'
        'blob/main/docs/DISCLAIMER_SNIPPET.md">Project notice</a></footer></body></html>'
    )
    return page.encode("utf-8")


def bundle_files(report: bytes) -> dict[str, bytes]:
    data = {name: (STUDY / name).read_bytes() for name in SOURCES}
    data["report.html"] = report
    data["START_HERE.html"] = data["index.html"]
    data["README.txt"] = (
        "AGI Alpha — public report edition\n\n"
        "Open START_HERE.html in a modern desktop browser. Read report.html for the complete English web report.\n"
        "Use Print / Save PDF for a printable copy. The report itself does not run an AI agent.\n"
        "This compact edition includes curated records, "
        "not the original 98-file archive or its full executable study.\n"
        "No account, wallet or API key is required. External project/download links require a network connection.\n"
        "Verify files with: sha256sum -c SHA256SUMS (or shasum -a 256 -c SHA256SUMS on macOS).\n"
        "Checksums establish byte consistency, not independent authenticity or production readiness.\n"
    ).encode("utf-8")
    sums = "".join(f"{sha(content)}  {name}\n" for name, content in sorted(data.items()))
    data["SHA256SUMS"] = sums.encode("ascii")
    return data


def make_zip(files: dict[str, bytes]) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compresslevel=9)
    return target.getvalue()


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.links: list[str] = []
        self.script_sources: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids.append(str(data["id"]))
        for key in ("href", "src"):
            if data.get(key):
                self.links.append(str(data[key]))
        if tag == "script":
            self.script_sources.append(data.get("src"))


def validate_sources() -> None:
    for name in SOURCES:
        if not (STUDY / name).is_file():
            raise ValueError(f"Missing public source: {name}")
    data = json.loads((STUDY / "results.json").read_text(encoding="utf-8"))
    expected = {
        "A_before": (8, 31),
        "A_after": (31, 31),
        "B_before": (9, 35),
        "B_after": (35, 35),
        "B_without-portability-fix": (29, 35),
    }
    for key, counts in expected.items():
        row = data["acceptance"][key]
        if (row["passed"], row["total"]) != counts:
            raise ValueError(f"Changed study acceptance: {key}")
    recovery = data["recovery"]
    if recovery["passed"] != 19 or recovery["total"] != 19 or len(recovery["tests"]) != 19:
        raise ValueError("Recovery headline differs from records")
    if not all(item["passed"] is True for item in recovery["tests"]):
        raise ValueError("A recovery failure was hidden")
    effort = data["ownerEffort"]
    if effort["participants"] != 0 or len(effort["runs"]) != 10:
        raise ValueError("Owner-study scope differs")
    for mode, actions in (("familiar-no-profile", 14), ("retained-profile", 11)):
        runs = [item for item in effort["runs"] if item["mode"] == mode]
        if len(runs) != 5 or any(item["actions"] != actions for item in runs):
            raise ValueError("Owner action totals differ")
        if any(
            (item["reviewChecks"], item["freshScopeApprovals"], item["qualityPassed"], item["qualityTotal"])
            != (3, 1, 35, 35)
            for item in runs
        ):
            raise ValueError("Quality or review obligations differ")
    if abs(effort["reductionFraction"] - 3 / 14) > 1e-12:
        raise ValueError("Incorrect reduction")
    if data["sourceArchive"]["sha256"] != ORIGINAL:
        raise ValueError("Original archive identity changed")
    if data["sourceArchive"]["manifestListedFilesVerified"] != 97 or data["sha256TestVectorsMatched"] != 105:
        raise ValueError("Original evidence counts changed")
    protocol = data["protocol"]
    if protocol["repositoryExecuted"] or protocol["humanParticipants"] != 0:
        raise ValueError("Unsupported study scope")
    for name in ("index.html", "REPORT.md", "PUBLICATION.md"):
        text = (STUDY / name).read_text(encoding="utf-8")
        if "sandbox:/" in text or "chatgpt-content-reference" in text:
            raise ValueError("A private or broken attachment link escaped")
    page = (STUDY / "index.html").read_text(encoding="utf-8")
    for phrase in ("21.4", "Simulated owner", "Human time was not measured", "98-file", "data-fr="):
        if phrase not in page:
            raise ValueError(f"Missing reader scope: {phrase}")
    parser = Links()
    parser.feed(page)
    if len(parser.ids) != len(set(parser.ids)):
        raise ValueError("Duplicate HTML IDs")
    if parser.script_sources != ["study.js"]:
        raise ValueError("Unexpected reader script")
    for link in parser.links:
        if link.startswith("#") and link[1:] not in parser.ids:
            raise ValueError(f"Broken anchor: {link}")
        if ":" in link and not link.startswith("https://"):
            raise ValueError(f"Unexpected link scheme: {link}")


def link_entrypoints() -> None:
    readme_path = ROOT / "README.md"
    old = readme_path.read_text(encoding="utf-8")
    marker = "<!-- computer-use-study-publication -->"
    callout = (
        f"{marker}\n"
        "> **Useful work. Recovered. Reused. — "
        "[Read the computer-use study](docs/reports/computer-use-study/REPORT.md).**\n"
        "> Two repaired websites, 19/19 recovery checks and 21.4% fewer scripted setup controls.\n"
        "> Simulated owner; real software checks. Not a production benchmark or measured human time saving.\n"
        f"> [English / Français visual reader]({URL}) · [Public report pack]({URL}report-pack.zip) · "
        "[Recorded results](docs/reports/computer-use-study/results.json).\n"
        "<!-- /computer-use-study-publication -->\n\n"
    )
    if marker not in old:
        split = old.find("\n\n")
        if split < 0:
            raise ValueError("README opening boundary is missing")
        boundary = split + 2
        new = old[:boundary] + callout + old[boundary:]
        if new.replace(callout, "", 1) != old:
            raise ValueError("README preservation failed")
        readme_path.write_text(new, encoding="utf-8")
    guide = ROOT / "docs/agent/START_HERE.md"
    old = guide.read_text(encoding="utf-8")
    if marker not in old:
        callout = (
            f"\n{marker}\n"
            "**See what was actually demonstrated:** "
            "[Read the computer-use study](../reports/computer-use-study/REPORT.md) "
            "or open its [English/French visual reader](../reports/computer-use-study/index.html). "
            "Two repaired websites, tested recovery and fewer scripted setup controls; simulated owner, "
            "not a production benchmark.\n<!-- /computer-use-study-publication -->\n"
        )
        heading = re.search(r"(?m)^# .+\n", old)
        if not heading:
            raise ValueError("Start-guide heading is missing")
        boundary = heading.end()
        new = old[:boundary] + callout + old[boundary:]
        if new.replace(callout, "", 1) != old:
            raise ValueError("Guide preservation failed")
        guide.write_text(new, encoding="utf-8")

    config = ROOT / "mkdocs.yml"
    old = config.read_text(encoding="utf-8")
    new = old
    hook = "  - scripts/mkdocs_computer_use_study.py\n"
    if hook not in new:
        anchor = "  - scripts/mkdocs_assets.py\n"
        if new.count(anchor) != 1:
            raise ValueError("MkDocs hook anchor is ambiguous")
        new = new.replace(anchor, anchor + hook, 1)
    navigation = (
        "- Computer-use study (EN / FR): reports/computer-use-study/index.html\n"
        "- Computer-use study report: reports/computer-use-study/REPORT.md\n"
        "- Study publication notes: reports/computer-use-study/PUBLICATION.md\n"
    )
    if "- Computer-use study (EN / FR):" not in new:
        anchor = "- Start here (EN / FR): start/index.html\n"
        if new.count(anchor) != 1:
            raise ValueError("MkDocs navigation anchor is ambiguous")
        new = new.replace(anchor, anchor + navigation, 1)
    removed = new.replace(hook, "", 1).replace(navigation, "", 1)
    original_without_additions = old.replace(hook, "", 1).replace(navigation, "", 1)
    if removed != original_without_additions:
        raise ValueError("MkDocs preservation failed")
    config.write_text(new, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--link-entrypoints", action="store_true")
    args = parser.parse_args()
    if args.link_entrypoints and not args.build:
        parser.error("--link-entrypoints requires --build")
    validate_sources()
    report = render_report()
    archive = make_zip(bundle_files(report))
    outputs = {"report.html": report, "report-pack.zip": archive}
    web_files = {name: (STUDY / name).read_bytes() for name in SOURCES}
    web_files.update(outputs)
    outputs["SHA256SUMS"] = "".join(f"{sha(value)}  {name}\n" for name, value in sorted(web_files.items())).encode(
        "ascii"
    )
    for name, content in outputs.items():
        target = STUDY / name
        if args.build:
            target.write_bytes(content)
        elif not target.is_file() or target.read_bytes() != content:
            raise ValueError(f"Stale generated publication: {name}; run --build")
    with zipfile.ZipFile(io.BytesIO(archive)) as packed:
        if packed.testzip() is not None or set(packed.namelist()) != set(bundle_files(report)):
            raise ValueError("Public pack integrity failed")
    if args.link_entrypoints:
        link_entrypoints()
    print(
        json.dumps(
            {
                "publication": "checked",
                "originalStudyRerun": False,
                "publicPackFiles": len(bundle_files(report)),
                "publicPackBytes": len(archive),
                "publicPackSha256": sha(archive),
                "sourceScope": "curated public report edition",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
