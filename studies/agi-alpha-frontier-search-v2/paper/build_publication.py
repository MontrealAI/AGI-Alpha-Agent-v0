"""Rebuild the publication from its complete editable manuscript and supplied figures.

Recovered after a local ENOSPC authoring failure; scientific evidence unchanged.
Rendering code is adapted from the preceding study's publication renderer.
"""
from pathlib import Path
import base64,html,json,os,re
from xml.sax.saxutils import escape
import markdown
from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate,Frame,PageTemplate,Paragraph,PageBreak,Image,KeepTogether,Spacer,Table,TableStyle,Preformatted
HERE=Path(__file__).resolve().parent
FIG=HERE/'figures'
SPEC={"title":"🌌♾️ AGI ALPHA FLYWHEEL — When Capability Creates Opportunity", "author":"Vincent Boucher — President of MONTREAL.AI", "subtitle":"Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work", "quote":"“As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.” — α-AGI Agent"}
def font_setup():
    import matplotlib
    base=Path(matplotlib.get_data_path()) / "fonts/ttf"
    fonts={"Body":"DejaVuSerif.ttf","Body-Bold":"DejaVuSerif-Bold.ttf","Body-Italic":"DejaVuSerif-Italic.ttf",
           "Sans":"DejaVuSans.ttf","Sans-Bold":"DejaVuSans-Bold.ttf","Sans-Italic":"DejaVuSans-Oblique.ttf","Mono":"DejaVuSansMono.ttf"}
    for alias,name in fonts.items():pdfmetrics.registerFont(TTFont(alias,str(base/name)))
    pdfmetrics.registerFontFamily("Body",normal="Body",bold="Body-Bold",italic="Body-Italic",boldItalic="Body-Bold")
    pdfmetrics.registerFontFamily("Sans",normal="Sans",bold="Sans-Bold",italic="Sans-Italic",boldItalic="Sans-Bold")


INK=colors.HexColor("#20143A");PURPLE=colors.HexColor("#6338AD");LIGHT=colors.HexColor("#F2ECFA")
styles={
    "body":ParagraphStyle("body",fontName="Body",fontSize=9.7,leading=14.2,textColor=INK,spaceAfter=8.3,allowWidows=0,allowOrphans=0),
    "h1":ParagraphStyle("h1",fontName="Sans-Bold",fontSize=17.2,leading=21.2,textColor=PURPLE,spaceBefore=18,spaceAfter=10,keepWithNext=True),
    "h2":ParagraphStyle("h2",fontName="Sans-Bold",fontSize=12.2,leading=16,textColor=INK,spaceBefore=13,spaceAfter=7,keepWithNext=True),
    "caption":ParagraphStyle("caption",fontName="Sans",fontSize=8.4,leading=11.4,textColor=colors.HexColor("#645574"),spaceAfter=11),
    "table":ParagraphStyle("table",fontName="Sans",fontSize=8.05,leading=11.0,textColor=INK,spaceAfter=0),
    "th":ParagraphStyle("th",fontName="Sans-Bold",fontSize=8.15,leading=11.1,textColor=colors.white,spaceAfter=0),
    "quote":ParagraphStyle("quote",fontName="Body-Italic",fontSize=10,leading=15,textColor=PURPLE,leftIndent=14,borderPadding=7,spaceAfter=12),
    "code":ParagraphStyle("code",fontName="Mono",fontSize=7.0,leading=10,textColor=INK,backColor=LIGHT,borderPadding=8,spaceAfter=12),
}


def inline(tag):
    value=str(tag)
    value=re.sub(r"^<(?:p|h[1-6]|li|th|td|blockquote)[^>]*>|</(?:p|h[1-6]|li|th|td|blockquote)>$","",value)
    value=value.replace("<strong>","<b>").replace("</strong>","</b>").replace("<em>","<i>").replace("</em>","</i>")
    value=value.replace("<code>",'<font name="Mono" size="8">').replace("</code>","</font>")
    value=re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',lambda m: '<link href="'+escape(m.group(1),{'"':'&quot;'})+'" color="#6338AD">'+m.group(2)+'</link>' if m.group(1).startswith(('https://','http://','mailto:')) else m.group(2),value)
    return value.replace("<br/>","<br/>")


class PublicationDoc(BaseDocTemplate):
    def __init__(self,path,label,**kw):
        self.label=label
        super().__init__(str(path),pagesize=(612,792),leftMargin=48,rightMargin=48,topMargin=50,bottomMargin=48,**kw)
        frame=Frame(48,48,516,694,id="normal",leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="main",frames=frame,onPage=self.page)])
    def page(self,c,doc):
        c.saveState()
        if doc.page>1 or self.label!="PAPER":
            c.setStrokeColor(colors.HexColor("#D7C4F3"));c.setLineWidth(.5);c.line(48,759,564,759)
            c.setFont("Sans-Bold",7);c.setFillColor(PURPLE);c.drawString(48,768,"MONTREAL.AI  /  AGI ALPHA FLYWHEEL")
            c.setFont("Sans",6.8);c.setFillColor(colors.HexColor("#6F627E"));c.drawRightString(564,768,"FRONTIER SEARCH · RESEARCH EDITION 2")
            c.line(48,38,564,38);c.drawString(48,26,"27 OCTOBER 2026 · EXPLORATORY EVIDENCE · NO QUALIFIED FLAGSHIP")
            c.drawRightString(564,26,str(doc.page))
        c.restoreState()


def cover():
    from reportlab.platypus import Flowable
    class Cover(Flowable):
        def __init__(self):super().__init__();self.width=516;self.height=682
        def draw(self):
            c=self.canv
            c.setFillColor(colors.HexColor("#241042"));c.roundRect(-20,-10,556,704,18,stroke=0,fill=1)
            c.saveState(); clip=c.beginPath(); clip.rect(-20,-10,556,704); c.clipPath(clip,stroke=0,fill=0); c.setStrokeColor(colors.HexColor("#664590"));c.setLineWidth(.6)
            for rad in [40,70,100,132,168]:c.circle(413,547,rad,stroke=1,fill=0)
            for i in range(70):
                xx=(i*193%510);yy=350+(i*79%320);c.setFillColor(colors.HexColor("#D7C4F3"));c.circle(xx,yy,.5+(i%3)*.3,stroke=0,fill=1)
            c.restoreState()
            c.setFillColor(colors.HexColor("#7CD4C2"));c.setFont("Sans-Bold",10);c.drawString(25,645,"MONTREAL.AI  /  FRONTIER-SEARCH RESEARCH EDITION 2")
            title=Paragraph("AGI ALPHA<br/>FLYWHEEL",ParagraphStyle("ct",fontName="Sans-Bold",fontSize=39,leading=44,textColor=colors.white))
            title.wrap(475,120);title.drawOn(c,25,507)
            sub=Paragraph("When Capability Creates Opportunity",ParagraphStyle("cs",fontName="Sans",fontSize=22,leading=29,textColor=colors.HexColor("#D7C4F3")))
            sub.wrap(460,80);sub.drawOn(c,25,429)
            p=Paragraph(SPEC["subtitle"],ParagraphStyle("sub",fontName="Sans",fontSize=11.5,leading=17,textColor=colors.white))
            p.wrap(415,70);p.drawOn(c,25,343)
            c.setFillColor(colors.HexColor("#7CD4C2"));c.setFont("Sans-Bold",8.3);c.drawString(25,316,"TRANSFORMATIONAL INTELLIGENCE: LEARNING TO CHANGE THE GAME");c.setFont("Sans-Bold",10);c.drawString(25,293,"FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.")
            au=Paragraph(SPEC["author"],ParagraphStyle("au",fontName="Sans-Bold",fontSize=11,leading=17,textColor=colors.white))
            au.wrap(460,40);au.drawOn(c,25,262)
            c.setStrokeColor(colors.HexColor("#8866AD"));c.line(25,240,490,240)
            qu=Paragraph(escape(SPEC["quote"]),ParagraphStyle("qu",fontName="Body-Italic",fontSize=9,leading=14,textColor=colors.HexColor("#D7C4F3")))
            qu.wrap(448,100);qu.drawOn(c,25,164)
            note=Paragraph("12 proposals reviewed. 8 executable probe families.<br/>No candidate qualifies as the flagship.",ParagraphStyle("no",fontName="Sans-Bold",fontSize=12,leading=18,textColor=colors.HexColor("#7CD4C2")))
            note.wrap(450,80);note.drawOn(c,25,77)
            c.setFillColor(colors.HexColor("#D7C4F3"));c.setFont("Sans",8);c.drawString(25,31,"27 OCTOBER 2026 · PRIOR ART, CONSTRUCTION, AND PRESERVED FAILURES")
    return Cover()


def pdf_from_markdown(md,path,label):
    dom=BeautifulSoup(markdown.markdown(md,extensions=["tables","fenced_code"]),"html.parser")
    story=[]
    if label=="PAPER":
        story=[cover(),PageBreak()]
        started=False
    else:started=True
    for tag in dom.children:
        if not getattr(tag,"name",None):continue
        if not started:
            if tag.name=="h3" and tag.get_text()=="Abstract":started=True
            else:continue
        name=tag.name
        if name in ["h1","h2","h3","h4"]:
            if label=="PAPER" and name=="h2" and (tag.get_text().startswith("Appendix A") or tag.get_text().startswith("References")):story.append(PageBreak())
            st=styles["h1"] if name in ["h1","h2"] else styles["h2"]
            story.append(Paragraph(inline(tag),st))
        elif name=="p":
            img=tag.find("img")
            if img:
                file=HERE/img.get("src")
                if not file.exists():raise FileNotFoundError(file)
                ir=ImageReader(str(file));w,h=ir.getSize();im=Image(str(file),width=516,height=516*h/w)
                story.append(KeepTogether([im,Spacer(1,4),Paragraph(escape(img.get("alt","")),styles["caption"])]))
            else:story.append(Paragraph(inline(tag),styles["body"]))
        elif name=="table":
            rows=tag.find_all("tr");n=len(rows[0].find_all(["th","td"]))
            if n==2:widths=[175,341]
            elif n==3:widths=[155,177,184]
            elif n==4:widths=[124,120,124,148]
            elif n==5:widths=[49,275,64,64,64]
            else:widths=[82,88,62,82,83,119]
            cells=[]
            for idx,row in enumerate(rows):cells.append([Paragraph(inline(cell),styles["th"] if idx==0 else styles["table"]) for cell in row.find_all(["th","td"])])
            t=Table(cells,colWidths=widths,repeatRows=1,hAlign="LEFT")
            t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PURPLE),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,LIGHT]),("LINEBELOW",(0,0),(-1,0),.5,PURPLE),("LINEBELOW",(0,1),(-1,-1),.3,colors.HexColor("#D7C4F3"))]))
            story.extend([t,Spacer(1,11)])
        elif name in ["ul","ol"]:
            for i,li in enumerate(tag.find_all("li",recursive=False)):
                prefix="• " if name=="ul" else str(i+1)+". "
                story.append(Paragraph(prefix+inline(li),styles["body"]))
        elif name=="blockquote":
            for p in tag.find_all("p",recursive=False):story.append(Paragraph(inline(p),styles["quote"]))
        elif name=="pre":
            code=tag.get_text();lines=[]
            for line in code.splitlines():
                while len(line)>100:lines.append(line[:98]+"\\");line="  "+line[98:]
                lines.append(line)
            story.append(Preformatted("\n".join(lines),styles["code"]))
    doc=PublicationDoc(path,label,title=SPEC["title"] if label=="PAPER" else SPEC["title"]+" — "+label.replace("_"," ").title(),author=SPEC["author"],subject="Executable frontier exploration; no qualified flagship")
    doc.build(story)


def html_reader(md):
    body=markdown.markdown(md,extensions=["tables","fenced_code","toc"])
    body=body.replace("🌌♾️ ",'<span aria-hidden="true" style="display:inline-block;vertical-align:middle;margin-right:.18em"><svg width="58" height="30" viewBox="0 0 58 30" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="28" rx="6" fill="#241042"/><circle cx="14" cy="14" r="9" stroke="#A784D3" fill="none"/><circle cx="10" cy="9" r="1.5" fill="#FFFFFF"/><circle cx="19" cy="16" r="1.2" fill="#7CD4C2"/><circle cx="9" cy="20" r=".9" fill="#FFFFFF"/><path d="M43 15C39 7 31 8 31 15C31 22 39 23 43 15C47 7 55 8 55 15C55 22 47 23 43 15" fill="none" stroke="#6338AD" stroke-width="2"/></svg></span><span style="position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)">🌌♾️ </span>')
    for file in FIG.glob("*.png"):
        body=body.replace('src="figures/'+file.name+'"','src="data:image/png;base64,'+base64.b64encode(file.read_bytes()).decode()+'"')
    css="""*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#FBF9FE;color:#20143A;font:17px/1.72 Georgia,serif}.mast{background:#241042;color:#D7C4F3;padding:24px max(6vw,20px);font:700 12px/1.5 system-ui;letter-spacing:.16em}.mast strong{color:#7CD4C2}.wrap{max-width:1040px;margin:auto;padding:48px 54px 80px}h1,h2,h3,h4{font-family:system-ui,sans-serif;line-height:1.22}h1{font-size:clamp(32px,5vw,58px);letter-spacing:-.04em;color:#241042;margin-top:0}h2{font-size:29px;color:#6338AD;margin-top:60px;padding-top:10px;border-top:1px solid #D7C4F3}h3{font-size:21px;margin-top:34px}p{margin:18px 0}a{color:#6338AD;text-underline-offset:3px}blockquote{border-left:4px solid #7CD4C2;padding:4px 24px;color:#6338AD;margin:30px 0}table{width:100%;border-collapse:collapse;font:14px/1.55 system-ui;margin:25px 0;table-layout:fixed;overflow-wrap:anywhere}th{background:#6338AD;color:white;text-align:left}td,th{padding:12px 13px;vertical-align:top;border-bottom:1px solid #D7C4F3}tr:nth-child(even){background:#F2ECFA}img{display:block;max-width:100%;height:auto;margin:26px auto}pre{background:#241042;color:#F2ECFA;padding:22px;border-radius:10px;white-space:pre-wrap;font-size:13px}code{font-size:.84em;overflow-wrap:anywhere}.notice{background:#EAE1F6;border-left:5px solid #6338AD;padding:16px 22px;margin:0 0 35px;font:15px/1.6 system-ui}.end{font:13px/1.6 system-ui;color:#6F627E;border-top:1px solid #D7C4F3;padding-top:25px}@media(max-width:640px){.wrap{padding:30px 20px}table{font-size:12px}td,th{padding:8px 6px}h2{font-size:25px}}@media print{body{font-size:10pt}.mast{background:white;color:#241042}.wrap{padding:0}h2{break-after:avoid}table,img{break-inside:avoid}a{color:#20143A}}"""
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Twelve proposals, eight executable probe families, and a preserved negative discovery result."><title>'+html.escape(SPEC["title"])+"</title><style>"+css+'</style></head><body><div class="mast"><strong>MONTREAL.AI</strong> / TRANSFORMATIONAL INTELLIGENCE</div><main class="wrap"><div class="notice"><b>Evidence boundary.</b> Twelve candidates reviewed; none qualifies as the flagship. Executed mathematical probes and local component reuse. No customer revenue, demonstrated foresight advantage, or canonical site publication is implied.</div>'+body+'<div class="end">Research edition 2 · 27 October 2026 · Complete evidence and licenses accompany this article.</div></main></body></html>'



if __name__=="__main__":
    if os.statvfs(HERE).f_bfree*os.statvfs(HERE).f_frsize < 20_000_000:
        raise RuntimeError("Insufficient free space; preserve existing outputs")
    font_setup()
    md=(HERE/"AGI_ALPHA_FLYWHEEL.md").read_text()
    brief=(HERE/"Executive_Brief.md").read_text()
    for text,name,label in [(md,"AGI_ALPHA_FLYWHEEL_Frontier_Search_v2.pdf","PAPER"),(brief,"Executive_Brief_v2.pdf","BRIEF")]:
        tmp=HERE/(name+".building")
        pdf_from_markdown(text,tmp,label)
        tmp.replace(HERE/name)
    target=HERE/"AGI_ALPHA_FLYWHEEL_Frontier_Search_v2.html"
    tmp=target.with_suffix(".building")
    tmp.write_text(html_reader(md));tmp.replace(target)
    from pypdf import PdfReader
    print(json.dumps({"paper_pages":len(PdfReader(HERE/"AGI_ALPHA_FLYWHEEL_Frontier_Search_v2.pdf").pages),"brief_pages":len(PdfReader(HERE/"Executive_Brief_v2.pdf").pages)}))
