# SPDX-License-Identifier: Apache-2.0
"""Build the PDF and self-contained browser editions from complete Markdown sources."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import json
import math
import random
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import markdown
import pdfplumber
from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

TITLE = "🌌♾️ AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
SUBTITLE = "Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work"
AUTHOR = "Vincent Boucher — President of MONTREAL.AI"
DATE = "27 October 2026"
DEEP = colors.HexColor("#22113E")
PURPLE = colors.HexColor("#4D287A")
LILAC = colors.HexColor("#CDB9EC")
INK = colors.HexColor("#211A2C")
MUTED = colors.HexColor("#675E73")
PALE = colors.HexColor("#F3EFF8")
GOLD = colors.HexColor("#E5C88B")
PAGE_W, PAGE_H = A4
MARGIN = 51
WIDTH = PAGE_W - 2 * MARGIN
FONTS = Path("/usr/share/fonts/truetype/dejavu")


def sha(path: Path) -> str:
    """Return a SHA-256 source/artifact identity."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_fonts() -> None:
    """Embed Unicode fonts with explicit bold-family mappings."""
    paths = {
        "Sans": "DejaVuSans.ttf",
        "SansBold": "DejaVuSans-Bold.ttf",
        "Body": "DejaVuSerif.ttf",
        "BodyBold": "DejaVuSerif-Bold.ttf",
        "Mono": "DejaVuSansMono.ttf",
    }
    for name, filename in paths.items():
        pdfmetrics.registerFont(TTFont(name, str(FONTS / filename)))
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="SansBold", italic="Sans", boldItalic="SansBold")
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold", italic="Body", boldItalic="BodyBold")
    pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono", italic="Mono", boldItalic="Mono")


def styles() -> dict[str, ParagraphStyle]:
    """One restrained typographic system for all three deliverables."""
    base = dict(
        fontName="Body",
        fontSize=10.1,
        leading=15,
        textColor=INK,
        spaceAfter=8,
        allowWidows=0,
        allowOrphans=0,
        splitLongWords=1,
    )
    return {
        "body": ParagraphStyle("BodyText", **base),
        "h1": ParagraphStyle(
            "H1",
            fontName="SansBold",
            fontSize=22,
            leading=27,
            textColor=DEEP,
            spaceBefore=8,
            spaceAfter=14,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName="SansBold",
            fontSize=18,
            leading=23,
            textColor=PURPLE,
            spaceBefore=14,
            spaceAfter=10,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            fontName="SansBold",
            fontSize=12.3,
            leading=17,
            textColor=PURPLE,
            spaceBefore=10,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h4": ParagraphStyle(
            "H4",
            fontName="SansBold",
            fontSize=10.5,
            leading=15,
            textColor=INK,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "bullet": ParagraphStyle("Bullet", **{**base, "leftIndent": 13, "firstLineIndent": -11, "spaceAfter": 6}),
        "quote": ParagraphStyle(
            "Quote",
            fontName="Body",
            fontSize=10.8,
            leading=16.2,
            textColor=PURPLE,
            leftIndent=12,
            rightIndent=12,
            spaceAfter=9,
            spaceBefore=5,
        ),
        "table": ParagraphStyle(
            "TableCell",
            fontName="Sans",
            fontSize=8.1,
            leading=11.5,
            textColor=INK,
            spaceAfter=0,
            splitLongWords=1,
            allowWidows=1,
            allowOrphans=1,
        ),
        "table_head": ParagraphStyle(
            "TableHeader",
            fontName="SansBold",
            fontSize=8.1,
            leading=11.5,
            textColor=colors.white,
            spaceAfter=0,
            splitLongWords=1,
        ),
        "caption": ParagraphStyle(
            "Caption", fontName="Sans", fontSize=8.5, leading=12.2, textColor=MUTED, spaceBefore=4, spaceAfter=11
        ),
        "code": ParagraphStyle(
            "Code",
            fontName="Mono",
            fontSize=7.8,
            leading=11.5,
            textColor=INK,
            backColor=PALE,
            borderPadding=9,
            spaceBefore=5,
            spaceAfter=10,
            splitLongWords=1,
            allowWidows=1,
            allowOrphans=1,
        ),
        "reference": ParagraphStyle(
            "Reference",
            fontName="Sans",
            fontSize=8.4,
            leading=12.5,
            textColor=INK,
            spaceAfter=7,
            splitLongWords=1,
            allowWidows=1,
            allowOrphans=1,
        ),
    }


def inline(node: Any) -> str:
    """Translate Markdown HTML into ReportLab's deliberately small inline vocabulary."""
    if isinstance(node, NavigableString):
        return html.escape(str(node))
    if not isinstance(node, Tag):
        return ""
    text = "".join(inline(child) for child in node.children)
    if node.name in {"strong", "b"}:
        return "<b>" + text + "</b>"
    if node.name in {"em", "i"}:
        return "<i>" + text + "</i>"
    if node.name == "code":
        return '<font name="Mono" size="8.7">' + text + "</font>"
    if node.name == "a":
        href = node.get("href", "")
        if href.startswith(("https://", "http://", "mailto:")):
            return '<a href="' + html.escape(href, quote=True) + '" color="#4D287A">' + text + "</a>"
        return text
    if node.name == "br":
        return "<br/>"
    if node.name in {"sup", "sub"}:
        return f"<{node.name}>" + text + f"</{node.name}>"
    if node.name == "img":
        return ""
    return text


def parsed(source: Path) -> BeautifulSoup:
    """Keep explicit page breaks while producing standard, editable Markdown HTML."""
    raw = source.read_text(encoding="utf-8")
    raw = re.sub(r"<!--\s*PAGEBREAK\s*-->", '<div class="page-break"></div>', raw, flags=re.I)
    output = markdown.markdown(raw, extensions=["tables", "fenced_code", "toc", "sane_lists"], output_format="html")
    soup = BeautifulSoup(output, "html.parser")
    # Preserve source wording while making bare primary-source URLs usable in
    # both editions.  Avoid already linked text and executable/code literals.
    for node in list(soup.find_all(string=True)):
        if isinstance(node, Comment) or any(parent.name in {"a", "code", "pre"} for parent in node.parents):
            continue
        text = str(node)
        matches = list(re.finditer(r"https?://[^\s<>\"']+", text))
        if not matches:
            continue
        position = 0
        for match in matches:
            url = match.group(0).rstrip(".,;")
            if match.start() > position:
                node.insert_before(NavigableString(text[position:match.start()]))
            link = soup.new_tag("a", href=url)
            link.string = url
            node.insert_before(link)
            position = match.start() + len(url)
        if position < len(text):
            node.insert_before(NavigableString(text[position:]))
        node.extract()
    first_heading = soup.find("h1")
    if first_heading is not None:
        first_heading.decompose()
    for node in list(soup.find_all(["p", "h2", "h3"], recursive=False))[:6]:
        if node.get_text(" ", strip=True) in {TITLE, SUBTITLE, AUTHOR}:
            node.decompose()
    return soup


def figure_path(source: Path, src: str, root: Path) -> Path:
    """Require local study images; never silently depend on an external image server."""
    if src.startswith(("http:", "https:", "data:")):
        raise ValueError("figures must be local study files: " + src)
    path = (source.parent / src).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("missing or external figure: " + str(path))
    return path


def table_widths(rows: list[list[Tag]]) -> list[float]:
    """Allocate legible columns from actual cell text, not equal-width defaults."""
    count = len(rows[0])
    weights = []
    for i in range(count):
        lengths = [len(row[i].get_text(" ", strip=True)) for row in rows if i < len(row)]
        weight = math.sqrt(max(10, min(100, max(lengths, default=10))))
        weights.append(weight)
    minimum = 53 if count <= 6 else 40
    remaining = WIDTH - minimum * count
    if remaining <= 0:
        return [WIDTH / count] * count
    return [minimum + remaining * weight / sum(weights) for weight in weights]


def flowables(source: Path, root: Path, theme: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Map source blocks to splittable text, tables and vector-safe layout elements."""
    soup = parsed(source)
    result: list[Flowable] = []
    reference_mode = False

    def append_node(node: Any) -> None:
        nonlocal reference_mode
        if isinstance(node, (Comment, NavigableString)):
            return
        if not isinstance(node, Tag):
            return
        if node.name == "div" and "page-break" in node.get("class", []):
            if result and not isinstance(result[-1], PageBreak):
                result.append(PageBreak())
            return
        if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            title = node.get_text(" ", strip=True)
            if re.match(r"^(?:\d+[.\s]+)?(?:References|Sources|Bibliography)", title, re.I):
                reference_mode = True
            heading = Paragraph(inline(node), theme.get(node.name, theme["h4"]))
            heading._outline_text = title
            heading._outline_level = max(0, int(node.name[1]) - 2)
            result.append(heading)
            return
        if node.name == "table":
            rows = [row.find_all(["th", "td"], recursive=False) for row in node.find_all("tr")]
            rows = [row for row in rows if row]
            if not rows:
                return
            header = any(cell.name == "th" for cell in rows[0])
            width = table_widths(rows)
            cells = [
                [Paragraph(inline(cell), theme["table_head"] if header and i == 0 else theme["table"]) for cell in row]
                for i, row in enumerate(rows)
            ]
            table = Table(cells, colWidths=width, repeatRows=1 if header else 0, hAlign="LEFT", splitByRow=1)
            commands = [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.HexColor("#D4C9E1")),
            ]
            if header:
                commands.append(("BACKGROUND", (0, 0), (-1, 0), DEEP))
            for index in range(1 if header else 0, len(rows)):
                if index % 2:
                    commands.append(("BACKGROUND", (0, index), (-1, index), PALE))
            table.setStyle(TableStyle(commands))
            table.spaceBefore = 4
            table.spaceAfter = 11
            result.append(table)
            return
        if node.name in {"ul", "ol"}:
            for index, item in enumerate(node.find_all("li", recursive=False), 1):
                bullet = str(index) + "." if node.name == "ol" else "•"
                result.append(
                    Paragraph(
                        html.escape(bullet) + "  " + inline(item),
                        theme["reference"] if reference_mode else theme["bullet"],
                    )
                )
            return
        if node.name == "pre":
            text = html.escape(node.get_text()).replace(" ", "&#160;").replace("\n", "<br/>")
            result.append(Paragraph(text, theme["code"]))
            return
        if node.name == "blockquote":
            for child in node.find_all("p", recursive=False):
                result.append(Paragraph(inline(child), theme["quote"]))
            return
        if node.name == "hr":
            result.append(Spacer(1, 7))
            return
        images = node.find_all("img") if node.name == "p" else ([node] if node.name == "img" else [])
        for image_node in images:
            path = figure_path(source, image_node["src"], root)
            with PILImage.open(path) as bitmap:
                w, h = bitmap.size
            scale = min(WIDTH / w, 315 / h)
            image = Image(str(path), width=w * scale, height=h * scale, hAlign="CENTER")
            image.spaceBefore = 5
            image.spaceAfter = 5
            result.append(image)
        if node.name in {"p", "div"}:
            if node.get_text(" ", strip=True):
                value = inline(node)
                caption = bool(re.match(r"^(?:Figure|Fig\.|Table)\s*\d", node.get_text(" ", strip=True)))
                style = theme["caption"] if caption else theme["reference"] if reference_mode else theme["body"]
                result.append(Paragraph(value, style))
            return
        for child in node.children:
            append_node(child)

    for child in soup.children:
        append_node(child)
    while result and isinstance(result[-1], (PageBreak, Spacer)):
        result.pop()
    return result


class Publication(BaseDocTemplate):
    """Preserve PDF metadata and section bookmarks without changing source prose."""

    def afterFlowable(self, flowable: Flowable) -> None:
        if hasattr(flowable, "_outline_text"):
            name = "section-" + str(self.seq.nextf("section"))
            self.canv.bookmarkPage(name)
            level = min(getattr(flowable, "_outline_level"), getattr(self, "_last_level", -1) + 1)
            self.canv.addOutlineEntry(flowable._outline_text, name, level=max(0, level), closed=False)
            self._last_level = level


def draw_cover(canvas: Any, document: Any, label: str) -> None:
    """Original vector cover: purple field, astronomical rings and restrained stars."""
    canvas.saveState()
    canvas.setFillColor(DEEP)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    for index in range(16):
        canvas.setFillColor(colors.Color(0.14 + index * 0.004, 0.067 + index * 0.002, 0.25 + index * 0.006))
        canvas.rect(PAGE_W * index / 16, 0, PAGE_W / 16 + 1, PAGE_H, fill=1, stroke=0)
    rng = random.Random(20261027)
    canvas.setFillColor(LILAC)
    for _ in range(77):
        x, y = rng.uniform(25, PAGE_W - 25), rng.uniform(25, PAGE_H - 25)
        canvas.setFillAlpha(rng.uniform(0.15, 0.7))
        canvas.circle(x, y, rng.uniform(0.4, 1.0), fill=1, stroke=0)
    canvas.setFillAlpha(1)
    canvas.setStrokeColor(LILAC)
    canvas.setStrokeAlpha(0.17)
    canvas.setLineWidth(0.65)
    for radius in (160, 188, 218, 252):
        canvas.circle(PAGE_W - 12, PAGE_H - 240, radius, fill=0, stroke=1)
    canvas.setStrokeAlpha(1)
    canvas.setFillAlpha(0.065)
    canvas.setFont("Body", 190)
    canvas.setFillColor(LILAC)
    canvas.drawString(360, 225, "Ω")
    canvas.setFillAlpha(1)
    canvas.setFont("SansBold", 12)
    canvas.setFillColor(GOLD)
    canvas.drawString(MARGIN, PAGE_H - 66, "MONTREAL.AI")
    canvas.setFont("Sans", 8)
    canvas.setFillColor(LILAC)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 64, label.upper())
    canvas.setFillColor(colors.white)
    y = PAGE_H - 177
    for value in ("AGI ALPHA", "FLYWHEEL"):
        canvas.setFont("SansBold", 43)
        canvas.drawString(MARGIN - 1, y, value)
        y -= 50
    canvas.setFont("Sans", 25)
    canvas.drawString(MARGIN, y - 12, "— When Capability")
    canvas.drawString(MARGIN, y - 46, "Creates Opportunity")
    subtitle = Paragraph(
        html.escape(SUBTITLE),
        ParagraphStyle("CoverSubtitle", fontName="Sans", fontSize=13, leading=20, textColor=LILAC),
    )
    _, height = subtitle.wrap(WIDTH - 32, 120)
    subtitle.drawOn(canvas, MARGIN, y - 92 - height)
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.4)
    canvas.line(MARGIN, 226, MARGIN + 72, 226)
    canvas.setFillColor(colors.white)
    canvas.setFont("SansBold", 10.7)
    canvas.drawString(MARGIN, 191, AUTHOR)
    canvas.setFont("Sans", 9)
    canvas.setFillColor(LILAC)
    canvas.drawString(MARGIN, 165, "FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.")
    canvas.setFont("Sans", 8.5)
    canvas.drawString(MARGIN, 73, DATE + "  ·  Executable research edition")
    canvas.restoreState()


def draw_compact(canvas: Any, document: Any, label: str, total: int | None) -> None:
    """Compact title block keeps the executive edition concise."""
    canvas.saveState()
    canvas.setFillColor(DEEP)
    canvas.rect(0, PAGE_H - 185, PAGE_W, 185, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.setFont("SansBold", 9)
    canvas.drawString(MARGIN, PAGE_H - 36, "MONTREAL.AI  /  " + label.upper())
    canvas.setFillColor(colors.white)
    canvas.setFont("SansBold", 23)
    canvas.drawString(MARGIN, PAGE_H - 75, "AGI ALPHA FLYWHEEL")
    canvas.setFont("Sans", 16)
    canvas.drawString(MARGIN, PAGE_H - 101, "— When Capability Creates Opportunity")
    canvas.setFont("Sans", 9)
    canvas.setFillColor(LILAC)
    canvas.drawString(MARGIN, PAGE_H - 131, AUTHOR)
    canvas.drawString(MARGIN, PAGE_H - 154, DATE + "  ·  Research edition")
    canvas.restoreState()
    footer(canvas, document, label, total, header=False)


def footer(canvas: Any, document: Any, label: str, total: int | None, header: bool = True) -> None:
    """Stable running furniture includes actual page totals from a prior build pass."""
    canvas.saveState()
    canvas.setFont("Sans", 7.2)
    canvas.setFillColor(MUTED)
    if header:
        canvas.drawString(MARGIN, PAGE_H - 29, "MONTREAL.AI")
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 29, "CAPABILITY CREATES OPPORTUNITY")
    canvas.setStrokeColor(colors.HexColor("#DDD5E7"))
    canvas.setLineWidth(0.45)
    canvas.line(MARGIN, 42, PAGE_W - MARGIN, 42)
    canvas.drawString(MARGIN, 28, label.upper() + "  ·  27 OCTOBER 2026")
    canvas.drawRightString(
        PAGE_W - MARGIN, 28, f"{document.page:02d} / {total:02d}" if total else f"{document.page:02d}"
    )
    canvas.restoreState()


def build_pdf(source: Path, output: Path, root: Path, label: str, full_cover: bool) -> dict[str, Any]:
    """Build twice so page totals and ordinary PDF links/bookmarks remain reliable."""
    theme = styles()
    output.parent.mkdir(parents=True, exist_ok=True)
    draft = root / "tmp" / "pdfs" / (output.stem + "-pagination.pdf")
    draft.parent.mkdir(parents=True, exist_ok=True)

    def one_pass(destination: Path, total: int | None) -> None:
        document = Publication(
            str(destination),
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=52,
            bottomMargin=56,
            title=TITLE,
            author=AUTHOR,
            subject=SUBTITLE,
        )
        normal = Frame(
            MARGIN, 56, WIDTH, PAGE_H - 108, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="normal"
        )
        body = PageTemplate(id="body", frames=[normal], onPage=lambda c, d: footer(c, d, label, total))
        if full_cover:
            first = PageTemplate(id="cover", frames=[normal], onPage=lambda c, d: draw_cover(c, d, label))
            document.addPageTemplates([first, body])
            story: list[Flowable] = [Spacer(1, 1), NextPageTemplate("body"), PageBreak()]
        else:
            compact = Frame(
                MARGIN,
                56,
                WIDTH,
                PAGE_H - 262,
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
                id="compact",
            )
            first = PageTemplate(
                id="compact",
                frames=[compact],
                onPage=lambda c, d: draw_compact(c, d, label, total),
                autoNextPageTemplate="body",
            )
            document.addPageTemplates([first, body])
            story = []
        story += flowables(source, root, theme)
        document.build(story)

    one_pass(draft, None)
    expected = len(PdfReader(draft).pages)
    one_pass(output, expected)
    actual = len(PdfReader(output).pages)
    if actual != expected:
        raise ValueError("pagination changed between identical layout passes")
    return {
        "file": str(output.relative_to(root)),
        "pages": actual,
        "bytes": output.stat().st_size,
        "sha256": sha(output),
        "source": str(source.relative_to(root)),
        "source_sha256": sha(source),
    }


CSS = """
:root{--deep:#22113e;--purple:#4d287a;--lilac:#cdb9ec;--ink:#211a2c;--muted:#675e73;--paper:#fff;--pale:#f3eff8}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f2f8;color:var(--ink);font:17px/1.75 Georgia,serif}
a{color:var(--purple);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:#8139af}img{max-width:100%;height:auto}
.hero{position:relative;overflow:hidden;background:radial-gradient(circle at 90% 20%,#4d287a 0,#27133f 43%,#1a0b2e 100%);color:white;padding:72px max(5vw,24px) 78px}
.hero:after{content:'Ω';position:absolute;right:3vw;top:70px;font-size:330px;line-height:1;opacity:.055;pointer-events:none}
.hero-inner{max-width:1100px;margin:auto;position:relative;z-index:1}.eyebrow{font:700 13px/1.5 system-ui,sans-serif;letter-spacing:.14em;color:#e5c88b;margin-bottom:35px}
.hero h1{max-width:1000px;font:700 clamp(32px,4.3vw,58px)/1.15 system-ui,sans-serif;letter-spacing:-.025em;margin:0 0 25px}
.subtitle{max-width:820px;color:var(--lilac);font:22px/1.55 system-ui,sans-serif}.author{margin:27px 0 8px;font:600 16px/1.7 system-ui,sans-serif}.meta{color:var(--lilac);font:14px/1.7 system-ui,sans-serif}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.actions a{display:inline-block;border:1px solid #8c73aa;border-radius:5px;padding:10px 18px;color:white;text-decoration:none;font:600 14px/1.5 system-ui,sans-serif}.actions a.primary{background:#e5c88b;color:#22113e;border-color:#e5c88b}
.layout{display:grid;grid-template-columns:240px minmax(0,850px);gap:45px;max-width:1180px;margin:0 auto;padding:55px 24px 80px}.navigation{position:sticky;top:22px;max-height:90vh;overflow:auto;align-self:start;font:13px/1.55 system-ui,sans-serif;padding:20px;border-left:2px solid #d7cbe4}.navigation h2{font-size:12px;letter-spacing:.1em;text-transform:uppercase;margin:0 0 15px}.navigation a{display:block;text-decoration:none;margin:10px 0;color:var(--muted)}
article{background:var(--paper);border:1px solid #e4dceb;border-radius:6px;padding:40px 42px;min-width:0;overflow-wrap:anywhere}article h1,article h2,article h3,article h4{font-family:system-ui,sans-serif;color:var(--purple);line-height:1.3;scroll-margin-top:25px}article h2{font-size:29px;margin:44px 0 18px;letter-spacing:-.02em}article h2:first-child{margin-top:0}article h3{font-size:20px;margin:29px 0 14px}article p{margin:0 0 20px}article li{margin:9px 0}blockquote{border-left:3px solid #b9a0d5;margin:25px 0;padding:5px 22px;color:var(--purple)}.table-wrap{overflow-x:auto;margin:25px 0}.table-wrap:focus-visible{outline:2px solid var(--purple);outline-offset:3px}table{border-collapse:collapse;width:100%;min-width:640px;overflow-wrap:normal;font:13px/1.55 system-ui,sans-serif}th{background:var(--deep);color:white;text-align:left}th,td{padding:12px 13px;vertical-align:top;border-bottom:1px solid #e3d9ec}tbody tr:nth-child(odd){background:var(--pale)}code{font:85%/1.6 ui-monospace,Consolas,monospace;overflow-wrap:anywhere;background:#f3eff8;padding:2px 4px;border-radius:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--pale);padding:18px;border-radius:5px;font-size:13px}pre code{padding:0}.page-break{height:1px;background:#e7ddec;margin:38px 0}figure{margin:30px 0}figure img{display:block;width:100%;border-radius:4px}.footer{max-width:1180px;margin:auto;padding:0 24px 45px;color:var(--muted);font:13px/1.6 system-ui,sans-serif}
@media(max-width:1050px){.layout{display:block;max-width:900px}.navigation{position:static;max-height:none;margin-bottom:28px}.navigation a{display:inline-block;margin:6px 14px 6px 0}article{padding:28px}}
@media(max-width:600px){body{font-size:16px}.hero{padding:45px 23px 48px}.subtitle{font-size:18px}.layout{padding:28px 13px 45px}article{padding:23px 20px}article h2{font-size:25px}.hero:after{font-size:230px;right:-25px}.navigation{padding:12px}.table-wrap{margin-left:-7px;margin-right:-7px}.table-wrap:before{content:'Swipe to read the full table →';display:block;font:12px/1.5 system-ui,sans-serif;color:var(--muted);padding:0 0 9px}th,td{padding:10px}}
@media print{body{background:white;font-size:10pt}.hero{background:white;color:#22113e;padding:20px}.hero h1{font-size:28pt}.hero:after,.navigation,.actions{display:none}.subtitle,.meta{color:#4d287a}.layout{display:block;padding:0}.layout article{border:0;padding:0}a{color:inherit}article h2{break-after:avoid;font-size:18pt}.page-break{break-after:page;visibility:hidden}.table-wrap{overflow:visible}tr,figure{break-inside:avoid}.footer{display:none}}
"""


def build_html(source: Path, output: Path, root: Path) -> dict[str, Any]:
    """Embed every figure and all CSS in the stable browser-readable edition."""
    soup = parsed(source)
    figures = []
    for node in soup.find_all("img"):
        path = figure_path(source, node["src"], root)
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml"}.get(
            path.suffix.lower()
        )
        if mime is None:
            raise ValueError("unsupported image format: " + str(path))
        node["src"] = "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        figures.append({"path": str(path.relative_to(root)), "sha256": sha(path)})
    for table in list(soup.find_all("table")):
        wrapper = soup.new_tag("div", attrs={"class": "table-wrap", "tabindex": "0", "role": "region", "aria-label": "Data table; scroll horizontally on narrow screens"})
        table.wrap(wrapper)
    headings = soup.find_all("h2")
    nav = "".join(
        '<a href="#'
        + html.escape(h.get("id", ""), quote=True)
        + '">'
        + html.escape(h.get_text(" ", strip=True))
        + "</a>"
        for h in headings
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    body = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="author" content="{html.escape(AUTHOR, quote=True)}"><meta name="description" content="{html.escape(SUBTITLE, quote=True)}">
<title>{html.escape(TITLE)}</title><style>{CSS}</style></head><body>
<header class="hero"><div class="hero-inner"><div class="eyebrow">MONTREAL.AI · RESEARCH EDITION</div>
<h1>{html.escape(TITLE.removeprefix("🌌♾️ "))}</h1><div class="subtitle">{html.escape(SUBTITLE)}</div><p class="author">{html.escape(AUTHOR)}</p>
<div class="meta">{DATE} · FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.</div>
<div class="actions"><a class="primary" href="../paper/paper.pdf">Download the paper PDF</a><a href="../paper/PAPER.md">Editable Markdown source</a><a href="../paper/executive_brief.pdf">Executive brief</a></div></div></header>
<div class="layout"><nav class="navigation" aria-label="Paper sections"><h2>In this paper</h2>{nav}</nav><article>{str(soup)}</article></div>
<footer class="footer">{html.escape(AUTHOR)} · {DATE}. The complete source, executable study and evidence accompany this research edition.</footer>
</body></html>'''
    output.write_text(body, encoding="utf-8")
    return {
        "file": str(output.relative_to(root)),
        "bytes": output.stat().st_size,
        "sha256": sha(output),
        "embedded_figures": figures,
        "external_assets": 0,
        "sections": len(headings),
    }


def inspect_pdf(path: Path, root: Path, dpi: int) -> dict[str, Any]:
    """Measure basic text geometry and render every page for mandatory visual review."""
    pages = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            outside = [
                c.get("text", "")
                for c in page.chars
                if c["x0"] < 12 or c["x1"] > page.width - 12 or c["top"] < 10 or c["bottom"] > page.height - 10
            ]
            pages.append(
                {
                    "page": index,
                    "characters": len(text),
                    "body_characters": len([c for c in page.chars if 48 < c["top"] < page.height - 48]),
                    "embedded_images": len(page.images),
                    "visible_text_bounds_violations": outside[:20],
                    "replacement_characters": text.count("\ufffd"),
                }
            )
    renderer = shutil.which("pdftoppm")
    if renderer is None:
        raise RuntimeError("pdftoppm is required for complete page visual review")
    directory = root / "tmp" / "pdfs" / path.stem / ("render-" + sha(path)[:12])
    directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [renderer, "-r", str(dpi), "-png", str(path), str(directory / "page")], check=True, capture_output=True
    )
    images = sorted(directory.glob("page-*.png"))
    if len(images) != len(pages):
        raise ValueError(f"rendered page count {len(images)} does not match PDF count {len(pages)} for {path.name}")
    cols = min(4, len(images))
    thumb_w, pad, label_h = 240, 16, 23
    thumb_h = round(thumb_w * PAGE_H / PAGE_W)
    contact = PILImage.new(
        "RGB",
        (cols * (thumb_w + pad) + pad, math.ceil(len(images) / cols) * (thumb_h + label_h + pad) + pad),
        "#e8e2ef",
    )
    draw = ImageDraw.Draw(contact)
    font = ImageFont.truetype(str(FONTS / "DejaVuSans.ttf"), 12)
    for index, image in enumerate(images):
        with PILImage.open(image) as bitmap:
            bitmap.thumbnail((thumb_w, thumb_h))
            x = pad + (index % cols) * (thumb_w + pad)
            y = pad + (index // cols) * (thumb_h + label_h + pad)
            contact.paste(bitmap.convert("RGB"), (x, y))
            draw.text((x, y + thumb_h + 4), f"{path.stem} · page {index + 1}", fill="#322044", font=font)
    sheet = directory / "contact-sheet.png"
    contact.save(sheet)
    shutil.copyfile(sheet, directory.parent / "contact-sheet.png")
    return {
        "file": str(path.relative_to(root)),
        "pages": pages,
        "render_dpi": dpi,
        "rendered_pages": [str(p.relative_to(root)) for p in images],
        "contact_sheet": str(sheet.relative_to(root)),
        "no_text_outside_page": all(not p["visible_text_bounds_violations"] for p in pages),
        "no_empty_pages": all(p["body_characters"] > 40 or p["embedded_images"] for p in pages),
        "no_replacement_characters": all(p["replacement_characters"] == 0 for p in pages),
    }


def build(root: Path, dpi: int) -> dict[str, Any]:
    """Produce publication artifacts and an honest pending visual-QA record."""
    started = time.perf_counter()
    register_fonts()
    root = root.resolve()
    specs = [
        ("PAPER.md", "paper.pdf", "Research paper", True),
        ("EXECUTIVE_BRIEF.md", "executive_brief.pdf", "Executive brief", False),
        ("CONNECTED_EXAMPLE.md", "connected_example.pdf", "Connected example", False),
    ]
    outputs = []
    inspections = []
    for source_name, output_name, label, full_cover in specs:
        source, output = root / "paper" / source_name, root / "paper" / output_name
        if not source.is_file():
            raise FileNotFoundError("complete editable source required: " + str(source))
        outputs.append(build_pdf(source, output, root, label, full_cover))
        inspections.append(inspect_pdf(output, root, dpi))
    browser = build_html(root / "paper" / "PAPER.md", root / "web" / "index.html", root)
    record = {
        "schema": "agialpha.opportunity-construction.publication-qa.v1",
        "builder_sha256": sha(Path(__file__)),
        "outputs": outputs,
        "browser": browser,
        "pdf_inspections": inspections,
        "elapsed_seconds": time.perf_counter() - started,
        "visual_review": {
            "status": "PENDING",
            "instruction": "Inspect every latest rendered page and contact sheet; record final artifact hashes and findings.",
        },
        "publication_boundary": "GitHub source reader and self-contained HTML file; no canonical Pages deployment inferred.",
        "editorial_boundary": "Scientific Markdown source remains unchanged; typography and rendering only.",
    }
    destination = root / "evidence" / "publication_qa.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--render-dpi", type=int, default=105)
    arguments = parser.parse_args()
    report = build(arguments.study_dir, arguments.render_dpi)
    print(
        json.dumps(
            {
                "pdfs": [{"file": row["file"], "pages": row["pages"]} for row in report["outputs"]],
                "browser": report["browser"]["file"],
                "visual_review": report["visual_review"]["status"],
            }
        )
    )
