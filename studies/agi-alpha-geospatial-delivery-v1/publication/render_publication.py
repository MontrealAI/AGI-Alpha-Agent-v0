# SPDX-License-Identifier: Apache-2.0
"""Create the paper, brief and self-contained browser edition from reviewed Markdown."""

from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import markdown
import matplotlib
from bs4 import BeautifulSoup, NavigableString, Tag
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TITLE = "🌌♾️ AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
SUBTITLE = "Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work"
AUTHOR = "Vincent Boucher — President of MONTREAL.AI"
REVIEW_BASE = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/research/geospatial-delivery-20261027/studies/agi-alpha-geospatial-delivery-v1/publication/"
INK, PURPLE, TEAL, LIGHT, MUTED = "#211335", "#622dc7", "#087e7a", "#f4effc", "#6d6479"
PAGE_W, PAGE_H = 595.276, 841.890
MARGIN = 49
WIDTH = PAGE_W - 2 * MARGIN
FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
for name, filename in [
    ("GeoSans", "DejaVuSans.ttf"),
    ("GeoSans-Bold", "DejaVuSans-Bold.ttf"),
    ("GeoSans-Oblique", "DejaVuSans-Oblique.ttf"),
    ("GeoSans-BoldOblique", "DejaVuSans-BoldOblique.ttf"),
    ("GeoMono", "DejaVuSansMono.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / filename)))
pdfmetrics.registerFontFamily(
    "GeoSans", normal="GeoSans", bold="GeoSans-Bold", italic="GeoSans-Oblique", boldItalic="GeoSans-BoldOblique"
)

STYLES = {
    "body": ParagraphStyle(
        "body",
        fontName="GeoSans",
        fontSize=9.8,
        leading=14.6,
        textColor=colors.HexColor(INK),
        spaceAfter=8,
        allowWidows=0,
        allowOrphans=0,
    ),
    "h1": ParagraphStyle(
        "h1",
        fontName="GeoSans-Bold",
        fontSize=23,
        leading=29,
        textColor=colors.HexColor(PURPLE),
        spaceAfter=17,
        keepWithNext=True,
    ),
    "h2": ParagraphStyle(
        "h2",
        fontName="GeoSans-Bold",
        fontSize=17,
        leading=22,
        textColor=colors.HexColor(PURPLE),
        spaceBefore=20,
        spaceAfter=10,
        keepWithNext=True,
    ),
    "h3": ParagraphStyle(
        "h3",
        fontName="GeoSans-Bold",
        fontSize=12,
        leading=17,
        textColor=colors.HexColor(INK),
        spaceBefore=13,
        spaceAfter=7,
        keepWithNext=True,
    ),
    "cell": ParagraphStyle(
        "cell", fontName="GeoSans", fontSize=8, leading=11.4, textColor=colors.HexColor(INK), spaceAfter=0
    ),
    "cellhead": ParagraphStyle("cellhead", fontName="GeoSans-Bold", fontSize=8, leading=11.4, textColor=colors.white),
    "caption": ParagraphStyle(
        "caption",
        fontName="GeoSans-Oblique",
        fontSize=8.1,
        leading=11.6,
        textColor=colors.HexColor(MUTED),
        spaceBefore=5,
        spaceAfter=14,
    ),
    "quote": ParagraphStyle(
        "quote",
        fontName="GeoSans-Oblique",
        fontSize=10,
        leading=15.5,
        textColor=colors.HexColor(PURPLE),
        leftIndent=15,
        rightIndent=14,
        borderPadding=10,
        spaceAfter=12,
    ),
    "code": ParagraphStyle(
        "code",
        fontName="GeoMono",
        fontSize=7.7,
        leading=11.2,
        textColor=colors.HexColor(INK),
        backColor=colors.HexColor(LIGHT),
        borderPadding=9,
        spaceAfter=12,
    ),
}


def inline(node) -> str:
    if isinstance(node, NavigableString):
        return html.escape(str(node)).replace("🌌", "").replace("♾️", "∞")
    if not isinstance(node, Tag):
        return ""
    content = "".join(inline(c) for c in node.children)
    if node.name in {"strong", "b"}:
        return f"<b>{content}</b>"
    if node.name in {"em", "i"}:
        return f"<i>{content}</i>"
    if node.name == "code":
        return f'<font name="GeoMono" size="8.1">{content}</font>'
    if node.name == "a":
        href = node.get("href", "")
        if href and not href.startswith("#"):
            destination = href if href.startswith(("https://", "http://")) else urljoin(REVIEW_BASE, href)
            return f'<link href="{html.escape(destination, quote=True)}" color="{PURPLE}">{content}</link>'
        return content
    if node.name == "br":
        return "<br/>"
    return content


class Cover(Flowable):
    def __init__(self, brief=False):
        super().__init__()
        self.width = WIDTH
        self.height = PAGE_H - 118
        self.brief = brief

    def draw(self):
        c = self.canv

        def para(text, y, size=12, leading=None, bold=False, color="#ffffff", width=WIDTH):
            s = ParagraphStyle(
                "cover",
                fontName="GeoSans-Bold" if bold else "GeoSans",
                fontSize=size,
                leading=leading or size * 1.35,
                textColor=colors.HexColor(color),
            )
            p = Paragraph(text, s)
            _, h = p.wrap(width, 500)
            p.drawOn(c, 0, y - h)
            return y - h

        y = self.height - 20
        y = para("MONTREAL.AI  /  RESEARCH", y, 10, bold=True, color="#bda6ee") - 24
        y = para("AGI ALPHA<br/>FLYWHEEL", y, 39, 43, bold=True) - 14
        y = para("When Capability<br/>Creates Opportunity", y, 25, 32, bold=True, color="#e7dcff") - 20
        y = para(SUBTITLE, y, 13, 19, color="#ccc0e0") - 23
        y = para(AUTHOR, y, 10.5, color="#ffffff") - 25
        y = (
            para(
                "TRANSFORMATIONAL INTELLIGENCE:<br/>LEARNING TO CHANGE THE GAME",
                y,
                12.3,
                18,
                bold=True,
                color="#70ded0",
            )
            - 18
        )
        if self.brief:
            y = para("EXECUTIVE BRIEF", y, 13, bold=True, color="#d3befb") - 18
        y = para("MONTRÉAL GEOSPATIAL DELIVERY  •  27 OCTOBER 2026", y, 8.4, bold=True, color="#bda6ee") - 21
        c.setFillColor(colors.HexColor("#2a1744"))
        c.roundRect(0, y - 86, WIDTH, 86, 10, fill=1, stroke=0)
        rows = [
            ("3,476", "actual facility records"),
            ("CAD 874", "modeled service price"),
            ("CAD 40,917", "modeled annual profit"),
        ]
        for i, (number, label) in enumerate(rows):
            xx = 15 + i * (WIDTH / 3)
            c.setFillColor(colors.HexColor("#ffffff"))
            c.setFont("GeoSans-Bold", 19 if i < 2 else 17)
            c.drawString(xx, y - 30, number)
            c.setFillColor(colors.HexColor("#c7b8df"))
            c.setFont("GeoSans", 8)
            c.drawString(xx, y - 48, label)
        y -= 101
        y = (
            para(
                "Executed public-data delivery. Commercial figures are simulations under stated assumptions; actual service collections are CAD 0.",
                y,
                8.7,
                13,
                color="#d6cce5",
            )
            - 17
        )
        y = para("FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.", y, 10.5, bold=True, color="#79e2d5")


def cover_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#130923"))
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#33204e"))
    canvas.setLineWidth(0.7)
    for radius in [165, 220, 285, 350, 430]:
        canvas.circle(PAGE_W + 55, PAGE_H - 55, radius, fill=0, stroke=1)
    for x, y, r in [(510, 770, 2), (478, 694, 1.4), (550, 540, 1.8), (447, 822, 1), (562, 308, 1.3), (503, 210, 1)]:
        canvas.setFillColor(colors.HexColor("#c1a5f1"))
        canvas.circle(x, y, r, fill=1, stroke=0)
    canvas.setFont("GeoSans", 7.8)
    canvas.setFillColor(colors.HexColor("#a48fbf"))
    canvas.drawString(MARGIN, 31, "Research edition 1.0  |  Exact-source executable study  |  MONTREAL.AI")
    canvas.restoreState()


def regular_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(PURPLE))
    canvas.rect(0, PAGE_H - 9, PAGE_W, 9, fill=1, stroke=0)
    canvas.setFont("GeoSans-Bold", 7.3)
    canvas.setFillColor(colors.HexColor(PURPLE))
    canvas.drawString(MARGIN, PAGE_H - 30, "AGI ALPHA FLYWHEEL")
    canvas.setFont("GeoSans", 7.1)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 30, "WHEN CAPABILITY CREATES OPPORTUNITY")
    canvas.setStrokeColor(colors.HexColor("#ddd3e8"))
    canvas.line(MARGIN, 43, PAGE_W - MARGIN, 43)
    canvas.setFont("GeoSans", 7.1)
    canvas.drawString(MARGIN, 29, "Vincent Boucher  ·  MONTREAL.AI  |  27 October 2026")
    canvas.drawRightString(PAGE_W - MARGIN, 29, str(doc.page))
    canvas.restoreState()


def content_flows(md: str, skip_title=True, compact=False):
    soup = BeautifulSoup(markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"]), "html.parser")
    styles = dict(STYLES)
    if compact:
        styles["body"] = ParagraphStyle("brief-body", parent=STYLES["body"], leading=13.8, spaceAfter=7)
        styles["h2"] = ParagraphStyle("brief-h2", parent=STYLES["h2"], spaceBefore=17, spaceAfter=8)
    flows = []
    blocks = [tag for tag in soup.children if isinstance(tag, Tag)]
    consumed = set()
    for block_index, tag in enumerate(blocks):
        if block_index in consumed:
            continue
        if tag.name == "h1" and skip_title:
            continue
        if tag.name in {"h1", "h2", "h3", "h4"}:
            flows.append(Paragraph(inline(tag), styles.get(tag.name, styles["h3"])))
        elif tag.name == "p":
            pictures = tag.find_all("img")
            if pictures:
                for pic in pictures:
                    path = HERE / pic["src"]
                    if not path.exists():
                        raise FileNotFoundError(path)
                    w, h = ImageReader(str(path)).getSize()
                    iw = WIDTH
                    ih = iw * h / w
                    if ih > 440:
                        iw *= 440 / ih
                        ih = 440
                    item = Image(str(path), width=iw, height=ih)
                    item.hAlign = "CENTER"
                    caption = pic.get("alt", "")
                    if block_index + 1 < len(blocks):
                        following = blocks[block_index + 1]
                        if following.name == "p" and following.get_text().strip().startswith("Figure "):
                            caption = inline(following)
                            consumed.add(block_index + 1)
                    flows.append(KeepTogether([Spacer(1, 8), item, Paragraph(caption, styles["caption"])]))
            else:
                flows.append(Paragraph(inline(tag), styles["body"]))
        elif tag.name == "blockquote":
            flows.append(Paragraph(inline(tag).strip(), styles["quote"]))
        elif tag.name in {"ul", "ol"}:
            for i, li in enumerate(tag.find_all("li", recursive=False)):
                prefix = f"{i + 1}. " if tag.name == "ol" else "• "
                s = ParagraphStyle(
                    "list", parent=styles["body"], leftIndent=13, firstLineIndent=-11, spaceAfter=3 if compact else 5
                )
                flows.append(Paragraph(prefix + inline(li), s))
            flows.append(Spacer(1, 4))
        elif tag.name == "table":
            trs = tag.find_all("tr")
            data = []
            for i, row in enumerate(trs):
                data.append(
                    [
                        Paragraph(inline(cell), styles["cellhead"] if i == 0 else styles["cell"])
                        for cell in row.find_all(["td", "th"], recursive=False)
                    ]
                )
            n = max(len(row) for row in data)
            if n == 2:
                second_header = trs[0].find_all(["td", "th"], recursive=False)[1].get_text().lower()
                numerical = any(
                    term in second_header
                    for term in ["central result", "central modeled result", "mean modeled", "records", "mean annual"]
                )
                widths = [WIDTH * 0.62, WIDTH * 0.38] if numerical else [WIDTH * 0.32, WIDTH * 0.68]
            elif n == 3:
                widths = [WIDTH * 0.38, WIDTH * 0.28, WIDTH * 0.34]
            elif n == 4:
                widths = [WIDTH * 0.34] + [WIDTH * 0.22] * 3
            else:
                widths = [WIDTH / n] * n
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PURPLE)),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(LIGHT), colors.white]),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#d7c8e9")),
                    ]
                )
            )
            flows.extend([Spacer(1, 4), table, Spacer(1, 12)])
        elif tag.name == "pre":
            raw = tag.get_text()
            lines = []
            for line in raw.splitlines():
                while len(line) > 90:
                    lines.append(line[:90])
                    line = line[90:]
                lines.append(line)
            flows.append(
                Paragraph("<br/>".join(html.escape(line).replace(" ", "&#160;") for line in lines), styles["code"])
            )
        elif tag.name == "hr":
            flows.append(Spacer(1, 14))
    return flows


def render_pdf(source: Path, target: Path, brief=False):
    doc = BaseDocTemplate(
        str(target),
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=51,
        bottomMargin=55,
        title=TITLE + (" — Executive Brief" if brief else ""),
        author=AUTHOR,
        subject=SUBTITLE,
        creator="MONTREAL.AI · Reproducible research publication",
    )
    cover = Frame(
        MARGIN, 55, WIDTH, PAGE_H - 109, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
    )
    normal = Frame(
        MARGIN, 55, WIDTH, PAGE_H - 108, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="Cover", frames=[cover], onPage=cover_background),
            PageTemplate(id="Body", frames=[normal], onPage=regular_background),
        ]
    )
    if brief:
        first = Paragraph("EXECUTIVE BRIEF", STYLES["h1"])
        doc.addPageTemplates([])
        flows = [NextPageTemplate("Body"), Cover(brief=True), PageBreak(), first] + content_flows(
            source.read_text(), compact=True
        )
    else:
        flows = [NextPageTemplate("Body"), Cover(), PageBreak()] + content_flows(source.read_text())
    doc.build(flows)


def render_html(source: Path, target: Path):
    body = markdown.markdown(source.read_text(), extensions=["tables", "fenced_code", "sane_lists"])
    soup = BeautifulSoup(body, "html.parser")
    if soup.h1:
        soup.h1.decompose()
    toc = []
    for i, h in enumerate(soup.find_all("h2")):
        h["id"] = f"section-{i + 1}"
        toc.append(f'<a href="#section-{i + 1}">{html.escape(h.get_text())}</a>')
    for pic in soup.find_all("img"):
        path = HERE / pic["src"]
        pic["src"] = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
        pic["loading"] = "lazy"
    css = """
:root{color-scheme:light;--ink:#211335;--purple:#622dc7;--muted:#6d6479}*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:#faf8fd;color:var(--ink);font:17px/1.75 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
a{color:#5923b5;text-decoration-thickness:1px;text-underline-offset:3px}a:focus-visible{outline:3px solid #06a995;outline-offset:3px}
.skip{position:absolute;left:12px;top:-80px;background:white;padding:10px}.skip:focus{top:12px;z-index:5}
.hero{position:relative;overflow:hidden;background:radial-gradient(ellipse at 82% 5%,#44226b 0%,#1e0d34 42%,#11081e 82%);color:#fff;padding:74px max(7vw,24px) 58px}
.hero:after{content:'';position:absolute;right:-170px;top:-250px;width:650px;height:650px;border:1px solid #80649755;border-radius:50%;box-shadow:0 0 0 85px #80649716,0 0 0 170px #80649712;pointer-events:none}
.hero-inner{position:relative;z-index:1;max-width:1100px;margin:auto}.brand{font-size:13px;letter-spacing:.16em;color:#c5adeb;font-weight:700}.hero h1{font-size:clamp(32px,4.5vw,64px);line-height:1.13;max-width:1000px;margin:25px 0}
.subtitle{font-size:20px;color:#ded0f0;max-width:780px;line-height:1.6}.tagline{color:#77e3d3;font-weight:700;margin:28px 0 13px}.author{color:#ece3f9}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin:25px 0}.actions a{background:#fff;color:#391660;padding:10px 18px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:650}
.actions .secondary{background:#ffffff14;color:#e9dcfb;border:1px solid #ffffff35}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;max-width:920px;margin-top:35px}
.metric{background:#ffffff0b;border:1px solid #ffffff21;border-radius:10px;padding:18px 21px}.metric b{font-size:29px;display:block}.metric span{color:#d7c8e8;font-size:13px}.qualifier{color:#d1c2e1;font-size:13px;max-width:880px;margin-top:18px}
.layout{display:grid;grid-template-columns:245px minmax(0,850px);gap:48px;max-width:1210px;margin:45px auto;padding:0 25px}nav{position:sticky;top:20px;align-self:start;max-height:92vh;overflow:auto;font-size:12px;line-height:1.5;padding-bottom:20px}nav strong{display:block;margin:0 0 15px;color:#593086;letter-spacing:.12em}nav a{display:block;padding:7px 10px;border-left:2px solid #e5d9f3;text-decoration:none;color:#51445f}nav a:hover{border-color:#622dc7;background:#f0e9f8}
main{min-width:0;background:#fff;border:1px solid #ece5f4;border-radius:12px;padding:36px 44px;box-shadow:0 10px 55px #30134a06}h2{color:#54229c;font-size:28px;line-height:1.25;margin:48px 0 18px;scroll-margin-top:24px}h2:first-child{margin-top:0}h3{font-size:20px;line-height:1.35;margin-top:30px}p{margin:0 0 19px}strong{font-weight:700}blockquote{margin:23px 0;padding:16px 23px;background:#f6f1fc;border-left:4px solid #7b4bbb;color:#48276c}blockquote p:last-child{margin-bottom:0}
img{display:block;width:100%;height:auto;border-radius:8px;margin:22px 0}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.55;margin:24px 0;overflow-wrap:anywhere}th{background:#622dc7;color:white;text-align:left;padding:11px}td{border-bottom:1px solid #ded5e8;padding:11px;vertical-align:top}tr:nth-child(even){background:#f7f3fc}code{font-size:.84em;background:#f4eff9;padding:2px 4px;border-radius:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:17px;background:#f4eff9;border-radius:8px;font-size:13px;line-height:1.6}pre code{padding:0}ul,ol{padding-left:24px}li{margin-bottom:7px}footer{max-width:1100px;margin:25px auto 50px;padding:0 24px;color:#74647f;font-size:12px}
@media(max-width:900px){.layout{grid-template-columns:1fr;gap:22px;max-width:830px}nav{position:static;max-height:none;display:none}main{padding:25px}.hero{padding-top:48px}.metrics{gap:8px}.metric{padding:14px}.metric b{font-size:23px}}@media(max-width:540px){body{font-size:16px}.metrics{grid-template-columns:1fr}.metric{display:flex;align-items:center;justify-content:space-between}.metric b{font-size:24px}main{padding:20px 16px}.layout{padding:0 12px}.hero h1{font-size:36px}.subtitle{font-size:17px}table{font-size:11px}td,th{padding:7px}h2{font-size:25px}}
@media print{nav,.actions,.skip{display:none}.layout{display:block;margin:0;padding:0}main{border:none;box-shadow:none;padding:0}.hero{background:white;color:black;padding:20px}.hero:after{display:none}.hero *{color:black}.metrics{display:none}a{color:black}h2{break-after:avoid}table,img{break-inside:avoid}}
"""
    title_icons = '<span class="title-icons" aria-hidden="true"><svg viewBox="0 0 88 48" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="galaxy"><stop stop-color="#eee3ff"/><stop offset=".4" stop-color="#9b76df"/><stop offset="1" stop-color="#4b256d"/></radialGradient></defs><rect x="1" y="4" width="38" height="38" rx="7" fill="#381b59"/><ellipse cx="20" cy="23" rx="18" ry="7" transform="rotate(-40 20 23)" fill="url(#galaxy)"/><circle cx="20" cy="23" r="3" fill="#fff"/><circle cx="8" cy="11" r="1" fill="#e2cfff"/><circle cx="31" cy="34" r="1" fill="#e2cfff"/><path d="M64 24 C52 4 39 17 48 27 C58 39 69 8 79 19 C90 31 76 43 64 24" fill="none" stroke="#fff" stroke-width="2.7"/></svg></span><span class="sr-only">🌌♾️ </span>'
    display_title = title_icons + html.escape(TITLE.removeprefix("🌌♾️ "))
    css += "\n.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.title-icons{display:inline-block;width:1.5em;height:.83em;vertical-align:-.04em;margin-right:.13em}.title-icons svg{width:100%;height:100%}"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="A complete Montréal geospatial data delivery and reproducible commercial simulation, with separate operational and retained Alpha evidence."><title>{html.escape(TITLE)}</title><style>{css}</style></head><body><a class="skip" href="#paper">Skip to paper</a><header class="hero"><div class="hero-inner"><div class="brand">MONTREAL.AI / RESEARCH EDITION 1.0</div><h1>{display_title}</h1><p class="subtitle">{html.escape(SUBTITLE)}</p><p class="author">{html.escape(AUTHOR)}</p><p class="tagline">TRANSFORMATIONAL INTELLIGENCE: LEARNING TO CHANGE THE GAME</p><p>FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.</p><div class="actions"><a href="AGI_ALPHA_FLYWHEEL.pdf">Download paper PDF</a><a class="secondary" href="EXECUTIVE_BRIEF.pdf">Executive brief</a><a class="secondary" href="../README.md">Reproduce the study</a></div><div class="metrics"><div class="metric"><b>3,476</b><span>actual facility records</span></div><div class="metric"><b>CAD 874</b><span>modeled service price</span></div><div class="metric"><b>CAD 40,917</b><span>modeled annual operating profit</span></div></div><p class="qualifier">Executed public-data delivery + conditional commercial simulation. Actual service collections: CAD 0. Demand, buyer behavior and mission reliability are assumptions; broader uncertainty includes losses.</p></div></header><div class="layout"><nav aria-label="Paper contents"><strong>IN THIS PAPER</strong>{"".join(toc)}</nav><main id="paper">{soup}</main></div><footer>27 October 2026 · MONTREAL.AI · Source code Apache 2.0; Montréal source data CC BY 4.0. Research review edition; canonical repository publication follows its existing qualification process.</footer></body></html>"""
    target.write_text(page)


if __name__ == "__main__":
    render_pdf(HERE / "PAPER.md", HERE / "AGI_ALPHA_FLYWHEEL.pdf")
    render_pdf(HERE / "EXECUTIVE_BRIEF.md", HERE / "EXECUTIVE_BRIEF.pdf", brief=True)
    render_html(HERE / "PAPER.md", HERE / "AGI_ALPHA_FLYWHEEL.html")
    (HERE / "Browser_Edition.md").write_text((HERE / "PAPER.md").read_text())
    print(
        json.dumps(
            {
                "outputs": [
                    "AGI_ALPHA_FLYWHEEL.pdf",
                    "EXECUTIVE_BRIEF.pdf",
                    "AGI_ALPHA_FLYWHEEL.html",
                    "Browser_Edition.md",
                ]
            }
        )
    )
