# SPDX-License-Identifier: Apache-2.0
"""Render the frozen research narrative as figures, PDFs and a local HTML reader."""

from __future__ import annotations

import base64
import html
import importlib.metadata
import json
import os
import random
import re
import textwrap
from functools import partial
from datetime import datetime, timezone
from pathlib import Path

import markdown
import matplotlib
import matplotlib.pyplot as plt
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parent

PURPLE = "#281342"
VIOLET = "#7141AB"
TEAL = "#197C81"
LILAC = "#DACCEB"
GREY = "#D9DCE2"
INK = "#242032"
WIDTH, HEIGHT = A4
MARGIN = 52
BODY_WIDTH = WIDTH - 2 * MARGIN
TITLE = "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
AUTHOR = "Vincent Boucher — President of MONTREAL.AI"


def figures() -> None:
    target = ROOT / "figures"
    target.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.edgecolor": "#AEA5BB",
            "axes.labelcolor": INK,
            "xtick.color": "#554961",
            "ytick.color": INK,
            "savefig.facecolor": "white",
        }
    )
    fig, ax = plt.subplots(figsize=(7.5, 3.1))
    for y, lo, hi, colour in [(1, 0.375, 1.625, TEAL), (0, -0.425, 2.425, VIOLET)]:
        ax.plot([lo, hi], [y, y], linewidth=8, color=colour, solid_capstyle="round")
        ax.scatter([lo, hi], [y, y], s=38, color=colour, edgecolors="white", zorder=3)
        ax.text(lo, y - 0.17, str(lo), ha="center", va="top", color=colour, fontsize=10)
        ax.text(hi, y - 0.17, str(hi), ha="center", va="top", color=colour, fontsize=10)
    ax.axvline(0.35, linestyle="--", linewidth=1.5, color="#A36F22")
    ax.text(0.35, 1.52, "Fixed threshold 0.35", ha="center", fontsize=9, color="#875B18")
    ax.set_yticks([1, 0], ["Shared calibration\n13,056 histories · TRUE", "Independent periods\n39,168 histories · UNRESOLVED"])
    ax.tick_params(axis="y", length=0, pad=12)
    ax.set_xlim(-0.7, 2.7)
    ax.set_ylim(-0.55, 1.6)
    ax.set_xlabel("Exact late-minus-early contrast · authored units", labelpad=10)
    ax.grid(axis="x", alpha=0.16)
    fig.subplots_adjust(left=0.32, right=0.98, top=0.88, bottom=0.23)
    fig.savefig(target / "origin_intervals.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 3.15))
    labels = ["Exact instrument", "Conventional reference", "Independent calibration\nby row"]
    left = [0, 0, 0]
    for label, values, colour in [
        ("TRUE", [3, 3, 1], TEAL),
        ("FALSE", [9, 9, 5], VIOLET),
        ("UNRESOLVED", [24, 24, 30], GREY),
    ]:
        ax.barh([2, 1, 0], values, left=left, height=0.55, label=label, color=colour)
        for i, value in enumerate(values):
            ax.text(left[i] + value / 2, 2 - i, str(value), ha="center", va="center", fontsize=10,
                    color=INK if colour == GREY or value == 1 else "white", weight="bold")
            left[i] += value
    ax.set_yticks([2, 1, 0], labels)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_xlim(0, 36)
    ax.set_xticks([0, 6, 12, 18, 24, 30, 36])
    ax.set_xlabel("Fresh confirmation questions (n = 36)", labelpad=9)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.47, 1.25), ncol=3, fontsize=9)
    ax.grid(axis="x", alpha=0.1)
    ax.set_axisbelow(True)
    fig.subplots_adjust(left=0.30, right=0.98, top=0.80, bottom=0.22)
    fig.savefig(target / "confirmation_outcomes.png", dpi=180)
    plt.close(fig)

    current = json.loads((ROOT / "economics/results/confirmation.json").read_text())["rows"]
    lookup = {r["scenario"]: r for r in current}
    scenarios = ["low", "baseline", "high", "warm_inbound_acquisition_zero", "competent_human_fast"]
    display = ["Low", "Baseline", "High", "Zero cash acquisition", "Fast human alternative"]
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    for i, key in enumerate(scenarios):
        y = len(scenarios) - 1 - i
        r = lookup[key]
        colour = TEAL if key == "high" else VIOLET
        ax.plot([r["profit_p10"], r["profit_p90"]], [y, y], linewidth=7, color=LILAC, solid_capstyle="round")
        ax.plot([r["profit_mean_ci95_low"], r["profit_mean_ci95_high"]], [y, y], linewidth=3, color=colour)
        ax.scatter([r["operating_profit"]], [y], s=44, color=colour, zorder=3)
        ax.text(r["profit_p90"] + 240, y, f"${r['operating_profit']:,.0f}", va="center", fontsize=9, color=colour, weight="bold")
    ax.axvline(0, linestyle="--", color="#978D9D", linewidth=1)
    ax.set_yticks(list(range(4, -1, -1)), display)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_xlim(-4000, 11200)
    ax.set_xticks([-4000, 0, 4000, 8000], ["−4,000", "0", "4,000", "8,000"])
    ax.set_xlabel("Modeled 90-day operating profit · USD, before tax and sunk research", labelpad=11)
    ax.text(0.0, 1.05, "Dot: mean   ·   Thin range: 95% MC interval for mean   ·   Pale range: 10th–90th campaign percentiles",
            transform=ax.transAxes, fontsize=7.5, color="#655871")
    ax.grid(axis="x", alpha=0.12)
    fig.subplots_adjust(left=0.29, right=0.98, top=0.85, bottom=0.20)
    fig.savefig(target / "economics_results.png", dpi=180)
    plt.close(fig)


def register_fonts() -> None:
    base = Path("/usr/share/fonts/truetype/dejavu")
    for name, file in [
        ("AlphaSans", "DejaVuSans.ttf"),
        ("AlphaSansBold", "DejaVuSans-Bold.ttf"),
        ("AlphaSerif", "DejaVuSerif.ttf"),
        ("AlphaSerifBold", "DejaVuSerif-Bold.ttf"),
        ("AlphaMono", "DejaVuSansMono.ttf"),
    ]:
        pdfmetrics.registerFont(TTFont(name, str(base / file)))
    pdfmetrics.registerFontFamily("AlphaSans", normal="AlphaSans", bold="AlphaSansBold", italic="AlphaSans", boldItalic="AlphaSansBold")
    pdfmetrics.registerFontFamily("AlphaSerif", normal="AlphaSerif", bold="AlphaSerifBold", italic="AlphaSerif", boldItalic="AlphaSerifBold")
    pdfmetrics.registerFontFamily("AlphaMono", normal="AlphaMono", bold="AlphaMono", italic="AlphaMono", boldItalic="AlphaMono")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["BodyText"]
    body = ParagraphStyle("AlphaBody", parent=base, fontName="AlphaSerif", fontSize=10.1, leading=15.0,
                          textColor=colors.HexColor(INK), spaceAfter=9, alignment=TA_LEFT,
                          allowWidows=0, allowOrphans=0, splitLongWords=True)
    return {
        "body": body,
        "h1": ParagraphStyle("AlphaH1", parent=body, fontName="AlphaSansBold", fontSize=25, leading=31,
                             textColor=colors.HexColor(PURPLE), spaceBefore=8, spaceAfter=18, keepWithNext=True),
        "h2": ParagraphStyle("AlphaH2", parent=body, fontName="AlphaSansBold", fontSize=17.5, leading=23,
                             textColor=colors.HexColor(PURPLE), spaceBefore=17, spaceAfter=12, keepWithNext=True),
        "h3": ParagraphStyle("AlphaH3", parent=body, fontName="AlphaSansBold", fontSize=12.1, leading=17,
                             textColor=colors.HexColor(VIOLET), spaceBefore=13, spaceAfter=7, keepWithNext=True),
        "table": ParagraphStyle("AlphaCell", parent=body, fontName="AlphaSans", fontSize=8.1, leading=11.6, spaceAfter=0),
        "thead": ParagraphStyle("AlphaHeadCell", parent=body, fontName="AlphaSansBold", fontSize=8.0, leading=11.2,
                                textColor=colors.white, spaceAfter=0),
        "caption": ParagraphStyle("AlphaCaption", parent=body, fontName="AlphaSans", fontSize=8.5, leading=12.2,
                                  textColor=colors.HexColor("#655871"), spaceAfter=13),
        "code": ParagraphStyle("AlphaCode", parent=body, fontName="AlphaMono", fontSize=7.7, leading=11.3,
                               backColor=colors.HexColor("#F3EFF8"), borderPadding=10, spaceAfter=12),
        "quote": ParagraphStyle("AlphaQuote", parent=body, fontName="AlphaSans", fontSize=10, leading=15.5,
                                textColor=colors.HexColor(VIOLET), leftIndent=14, rightIndent=10),
        "reference": ParagraphStyle("AlphaReference", parent=body, fontName="AlphaSans", fontSize=8.4, leading=12.5, spaceAfter=9),
    }


def inline(source: str) -> str:
    source = html.escape(source, quote=False)
    source = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#62369A">\1</link>', source)
    source = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", source)
    source = re.sub(r"`([^`]+)`", r'<font name="AlphaMono" size="8.4">\1</font>', source)
    return source


def table_widths(headers: list[str]) -> list[float]:
    count = len(headers)
    ratios = {
        2: [0.27, 0.73],
        3: [0.25, 0.35, 0.40],
        4: [0.21, 0.28, 0.23, 0.28],
        5: [0.24, 0.09, 0.26, 0.20, 0.21],
        6: [0.16, 0.14, 0.19, 0.18, 0.18, 0.15],
        7: [0.14, 0.10, 0.12, 0.18, 0.17, 0.16, 0.13],
    }.get(count, [1 / count] * count)
    if count == 3 and "quantity" in headers[0].lower():
        ratios = [0.35, 0.16, 0.49]
    return [BODY_WIDTH * value for value in ratios]


def markdown_flow(source: str, sty: dict[str, ParagraphStyle], major_breaks: bool = False) -> list:
    lines = source.splitlines()
    story = []
    index = 0
    references = False
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line == "<!-- PAGEBREAK -->":
            story.append(PageBreak())
            index += 1
            continue
        if line.startswith("```"):
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.extend(textwrap.wrap(lines[index], 94, replace_whitespace=False, drop_whitespace=False) or [""])
                index += 1
            story.append(Paragraph("<br/>".join(html.escape(v).replace(" ", "&#160;") for v in code), sty["code"]))
            index += 1
            continue
        if line.startswith("|"):
            block = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [value.strip() for value in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", value) for value in cells):
                    block.append(cells)
                index += 1
            data = [[Paragraph(inline(value), sty["thead"] if row == 0 else sty["table"])
                     for value in cells] for row, cells in enumerate(block)]
            table = Table(data, colWidths=table_widths(block[0]), repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PURPLE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F5F1F9"), colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.HexColor("#D8CCE4")),
            ]))
            story.extend([Spacer(1, 3), table, Spacer(1, 13)])
            continue
        figure = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if figure:
            from PIL import Image as PILImage
            path = ROOT / figure.group(2)
            with PILImage.open(path) as bitmap:
                width, height = bitmap.size
            flow = Image(str(path), width=BODY_WIDTH, height=BODY_WIDTH * height / width)
            group = [Spacer(1, 7), flow, Spacer(1, 4)]
            following = index + 1
            while following < len(lines) and not lines[following].strip():
                following += 1
            if following < len(lines) and lines[following].startswith("**Figure"):
                group.append(Paragraph(inline(lines[following].strip()), sty["caption"]))
                index = following + 1
            else:
                index += 1
            story.append(KeepTogether(group))
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            heading = line[level:].strip()
            if heading == "References":
                references = True
            if major_breaks and level == 2 and story and (re.match(r"\d+\.", heading) or heading.startswith("Appendix") or heading == "References"):
                story.append(CondPageBreak(170))
            story.append(Paragraph(inline(heading), sty[f"h{min(level, 3)}"]))
            index += 1
            continue
        if line.startswith("- "):
            story.append(Paragraph(inline(line[2:]), sty["body"], bulletText="•"))
            index += 1
            continue
        if line.startswith("> "):
            story.append(Paragraph(inline(line[2:]), sty["quote"]))
            index += 1
            continue
        if re.match(r"^\d+\.\s", line):
            story.append(Paragraph(inline(line), sty["reference"] if references else sty["body"]))
            index += 1
            continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].startswith(("#", "|", "```", "![", "<!--", "- ", "> ")):
            paragraph.append(lines[index].strip())
            index += 1
        text = " ".join(paragraph)
        style = sty["reference"] if references else sty["caption"] if text.startswith("**Figure") else sty["body"]
        story.append(Paragraph(inline(text), style))
    return story


def page(canvas: Canvas, document: SimpleDocTemplate, cover: bool = False, brief: bool = False) -> None:
    canvas.saveState()
    if cover and document.page == 1:
        canvas.setFillColor(colors.HexColor("#160B2D"))
        canvas.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
        canvas.setStrokeColor(colors.HexColor("#422261"))
        canvas.setLineWidth(0.7)
        for radius in [180, 245, 310, 375]:
            canvas.circle(WIDTH + 75, HEIGHT - 220, radius, stroke=1, fill=0)
        rng = random.Random(271027)
        for _ in range(70):
            x, y = rng.uniform(18, WIDTH - 18), rng.uniform(25, HEIGHT - 25)
            canvas.setFillColor(colors.HexColor(rng.choice(["#7D61A0", "#BC9CE1", "#EADBF7"])))
            canvas.circle(x, y, rng.choice([0.45, 0.65, 0.85]), stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#CDB1E6"))
        canvas.setFont("AlphaSans", 8.5)
        canvas.drawString(MARGIN, 32, "FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.")
    else:
        canvas.setFillColor(colors.HexColor(PURPLE))
        canvas.setFont("AlphaSansBold", 8)
        canvas.drawString(MARGIN, HEIGHT - 30, "MONTREAL.AI")
        canvas.setFont("AlphaSans", 7.5)
        canvas.setFillColor(colors.HexColor("#756681"))
        canvas.drawRightString(WIDTH - MARGIN, HEIGHT - 30, "EXECUTIVE BRIEF" if brief else "AGI ALPHA FLYWHEEL / RESEARCH EDITION")
        canvas.setStrokeColor(colors.HexColor("#E4DBED"))
        canvas.line(MARGIN, 44, WIDTH - MARGIN, 44)
        canvas.setFont("AlphaSans", 7.4)
        canvas.drawString(MARGIN, 29, "27 OCTOBER 2026  ·  AUTHORED-WORLD EVIDENCE / CONDITIONAL ECONOMICS")
        canvas.setFont("AlphaSansBold", 8)
        canvas.setFillColor(colors.HexColor(PURPLE))
        canvas.drawRightString(WIDTH - MARGIN, 29, f"{document.page:02d}")
    canvas.restoreState()


def cover_story() -> list:
    def cs(name: str, size: float, leading: float, colour: str = "#FFFFFF") -> ParagraphStyle:
        return ParagraphStyle(name, fontName="AlphaSans", fontSize=size, leading=leading,
                              textColor=colors.HexColor(colour), spaceAfter=0)
    brand = cs("CoverBrand", 17, 24, "#E9DAF7")
    main = cs("CoverMain", 34, 40)
    main.fontName = "AlphaSansBold"
    sub = cs("CoverSub", 24, 30, "#CDB1E6")
    subtitle = cs("CoverSubtitle", 13.4, 21, "#E6DCEF")
    small = cs("CoverSmall", 10, 15, "#DACBE6")
    metric = cs("CoverMetric", 24, 31)
    metric.fontName = "AlphaSansBold"
    metric_label = cs("CoverMetricLabel", 8.3, 12, "#DACBE6")
    metrics = [
        [Paragraph("50/50", metric), Paragraph("877,728", metric), Paragraph("12/36", metric)],
        [Paragraph("exact comparisons", metric_label), Paragraph("possible histories", metric_label), Paragraph("fresh queries resolved", metric_label)],
    ]
    table = Table(metrics, colWidths=[BODY_WIDTH / 3] * 3)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#302046")),
        ("TOPPADDING", (0, 0), (-1, 0), 13),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return [
        Paragraph("MONTREAL.AI", brand), Spacer(1, 39),
        Paragraph("AGI ALPHA<br/>FLYWHEEL", main), Spacer(1, 12),
        Paragraph("— When Capability<br/>Creates Opportunity", sub), Spacer(1, 24),
        Paragraph("Transformational Intelligence,<br/>Experience-Trained Specialists and the<br/>Expanding Frontier of Profitable Work", subtitle),
        Spacer(1, 23), Paragraph(AUTHOR, small), Spacer(1, 18),
        Paragraph("RESEARCH EDITION · 27 OCTOBER 2026", cs("CoverDate", 8.5, 13, "#BD99DE")),
        Spacer(1, 18), table, Spacer(1, 19),
        Paragraph("The exact construction works within its declared model.<br/>Prior-art review withholds flagship status. The baseline<br/>commercial model rejects launch. Actual collections: USD 0.", small),
        Spacer(1, 22),
        Paragraph("“As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.” — α-AGI Agent", cs("CoverQuote", 8.7, 13, "#B99ECE")),
        PageBreak(),
    ]


def pdfs() -> dict:
    # A fixed edition timestamp makes the rendered PDF reproducible. Actual build
    # and inspection times are recorded separately in the QA/publication receipts.
    os.environ.setdefault("SOURCE_DATE_EPOCH", str(int(datetime(2026, 10, 27, tzinfo=timezone.utc).timestamp())))
    target = ROOT / "paper"
    target.mkdir(exist_ok=True)
    register_fonts()
    sty = styles()
    source = (ROOT / "manuscript.md").read_text()
    body = source.split("<!-- PAGEBREAK -->", 1)[1]
    outputs = []
    for filename, content, cover, brief in [
        ("agi-alpha-flywheel.pdf", body, True, False),
        ("executive-brief.pdf", (ROOT / "executive_brief.md").read_text(), False, True),
    ]:
        path = target / filename
        local_styles = sty
        if brief:
            local_styles = styles()
            local_styles["body"].fontSize = 9.5
            local_styles["body"].leading = 13.4
            local_styles["body"].spaceAfter = 8
            local_styles["h2"].fontSize = 14.8
            local_styles["h2"].leading = 19
            local_styles["h2"].spaceBefore = 13
            local_styles["h2"].spaceAfter = 8
        document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN,
                                     topMargin=57, bottomMargin=60, title=TITLE if cover else "Executive brief — " + TITLE,
                                     author=AUTHOR, subject="Executed finite research; no flagship qualified; conditional commercial economics",
                                     invariant=1)
        story = cover_story() if cover else []
        story += markdown_flow(content, local_styles, major_breaks=cover)
        callback = partial(page, cover=cover, brief=brief)
        document.build(story, onFirstPage=callback, onLaterPages=callback,
                       canvasmaker=partial(Canvas, invariant=1, pageCompression=1))
        reader = PdfReader(path)
        outputs.append({"file": filename, "pages": len(reader.pages), "bytes": path.stat().st_size,
                        "text_characters": sum(len(p.extract_text() or "") for p in reader.pages)})
    return {"outputs": outputs}


def reader_html() -> None:
    source = (ROOT / "manuscript.md").read_text()
    source = source.replace("<!-- PAGEBREAK -->", "")
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"], extension_configs={"toc": {"toc_depth": "2-3"}})
    body = md.convert(source)
    for path in (ROOT / "figures").glob("*.png"):
        encoded = base64.b64encode(path.read_bytes()).decode()
        body = body.replace(f'src="figures/{path.name}"', f'src="data:image/png;base64,{encoded}"')
    css = """
    :root{--ink:#282032;--purple:#281342;--violet:#7141ab;--pale:#f4eff9}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);font:17px/1.72 Georgia,serif;background:#faf8fc}
    .top{background:#180c2e;color:#eee2fa;padding:17px max(5vw,24px);font:13px/1.5 system-ui,sans-serif;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}
    .top strong{letter-spacing:.15em}.top a{color:#dfc4fa;margin-left:18px}.hero{background:radial-gradient(ellipse at 80% 20%,#593277 0,#211039 55%,#160a2a 100%);color:white;padding:54px max(7vw,24px)}
    .hero h1{font:700 clamp(30px,4.5vw,57px)/1.14 system-ui,sans-serif;max-width:1000px;margin:0 0 20px}.hero p{font:18px/1.6 system-ui,sans-serif;max-width:870px;color:#e0ccea}.tag{font:12px/1.5 system-ui,sans-serif;letter-spacing:.13em;color:#bd98df}
    .layout{display:grid;grid-template-columns:240px minmax(0,870px);gap:42px;max-width:1240px;margin:auto;padding:44px 28px}aside{font:12px/1.5 system-ui,sans-serif;position:sticky;top:20px;height:88vh;overflow:auto;padding-right:12px}aside ul{list-style:none;padding-left:10px}aside li{margin:7px 0}aside a{color:#6b557f;text-decoration:none}aside a:hover{color:#281342;text-decoration:underline}
    article{min-width:0}article>h1,article>h2:first-of-type{display:none}h2{font:700 29px/1.3 system-ui,sans-serif;color:var(--purple);margin:48px 0 20px;border-top:1px solid #e1d5eb;padding-top:26px}h3{font:650 20px/1.4 system-ui,sans-serif;color:var(--violet);margin:32px 0 12px}p{margin:0 0 19px}a{color:#673697;overflow-wrap:anywhere}strong{color:#312040}img{max-width:100%;height:auto;background:white;border-radius:9px}table{width:100%;border-collapse:collapse;font:13px/1.55 system-ui,sans-serif;margin:24px 0 30px;display:block;overflow-x:auto}thead{background:var(--purple);color:white}th,td{text-align:left;padding:12px 13px;vertical-align:top;border-bottom:1px solid #e4daec;min-width:95px}th strong{color:white}tbody tr:nth-child(odd){background:var(--pale)}code{font:13px/1.55 ui-monospace,monospace;overflow-wrap:anywhere;background:#f1eaf7;border-radius:3px;padding:2px 4px}pre{background:#f1eaf7;padding:18px;overflow-x:auto;border-radius:8px}pre code{padding:0}blockquote{border-left:3px solid #a981cb;padding:5px 20px;color:#786087;margin:24px 0}.foot{background:#211238;color:#d3bde6;font:13px/1.6 system-ui,sans-serif;padding:30px;text-align:center}
    @media(max-width:900px){.layout{display:block;padding:25px 20px}aside{position:relative;height:auto;max-height:260px;margin-bottom:30px;background:#f1eaf7;padding:15px;border-radius:8px}article h2{font-size:25px}.hero{padding:38px 22px}}
    @media print{aside,.top,.hero,.foot{display:none}.layout{display:block;padding:0}body{background:white;font-size:11pt}h2{break-before:page}a{color:inherit}}
    """
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(TITLE)}</title><meta name="author" content="{html.escape(AUTHOR)}"><style>{css}</style></head><body><div class="top"><strong>MONTREAL.AI</strong><div><a href="agi-alpha-flywheel.pdf">Paper PDF</a><a href="executive-brief.pdf">Executive brief</a></div></div><header class="hero"><div class="tag">RESEARCH EDITION · 27 OCTOBER 2026</div><h1>{html.escape(TITLE)}</h1><p>Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work</p><p>{html.escape(AUTHOR)}</p><div class="tag">50 EXACT COMPARISONS · 877,728 HISTORIES · NO FLAGSHIP QUALIFIED</div></header><div class="layout"><aside aria-label="Contents"><strong>CONTENTS</strong>{md.toc}</aside><article>{body}</article></div><footer class="foot">Executed finite construction · Conditional pre-tax economics · Zero actual customer collections<br>Full source, failed explorations and reproducibility receipt accompany this edition.</footer></body></html>"""
    (ROOT / "paper/index.html").write_text(doc)


def main() -> None:
    assert "@@" not in (ROOT / "manuscript.md").read_text()
    figures()
    result = pdfs()
    reader_html()
    result["dependencies"] = {name: importlib.metadata.version(name) for name in ["reportlab", "matplotlib", "pypdf", "Markdown", "Pillow"]}
    result["scope"] = "Presentation rendering only; no experiment, model policy or source freeze changed."
    (ROOT / "paper/build_receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
