import argparse
import base64
import hashlib
import html
import json
import mimetypes
import pathlib
import re
import subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
WEB=ROOT/'web'

def expand_latex(path,chain=()):
    path=path.resolve()
    if path in chain:
        raise ValueError('Recursive LaTeX input: '+str(path))
    content=path.read_text()
    def replace(match):
        name=match.group(1)
        child=path.parent/(name if pathlib.Path(name).suffix else name+'.tex')
        return expand_latex(child,chain+(path,))
    return re.sub(r'\\input\{([^}]+)\}',replace,content)

def prepare_latex(path):
    source=expand_latex(path)
    keys=re.findall(r'\\bibitem\{([^}]+)\}',source)
    if len(keys)!=len(set(keys)):
        raise ValueError('Duplicate bibliography keys')
    reference_numbers={key:i+1 for i,key in enumerate(keys)}
    counts={'tables':len(re.findall(r'\\begin\{(?:tabular|longtable)\}',source)),
            'figures':len(re.findall(r'\\begin\{figure\}',source)),
            'references':len(keys),
            'numbered_equations':len(re.findall(r'\\begin\{(?:equation|align)\}',source)),
            'expanded_latex_sha256':hashlib.sha256(source.encode()).hexdigest()}
    # Pandoc does not expand this manuscript's custom L column type. Its
    # equivalent standard paragraph column retains the cells and captions.
    source=re.sub(r'L\{([^{}]+)\}',r'p{\1}',source)
    # The manuscript uses an explicit bibliography rather than BibTeX.
    # Retain every entry in its exact order and supply stable HTML anchors.
    source=re.sub(r'\\begin\{thebibliography\}\{[^}]+\}',r'\\section*{References}\n\\begin{enumerate}',source)
    source=re.sub(r'\\bibitem\{([^}]+)\}',lambda m:r'\item \hypertarget{ref-'+m.group(1)+'}{}',source)
    source=source.replace(r'\end{thebibliography}',r'\end{enumerate}')
    return source,reference_numbers,counts

def restore_citations(body,numbers):
    def replace(match):
        keys=html.unescape(match.group(1)).split()
        unknown=[key for key in keys if key not in numbers]
        if unknown:
            raise ValueError('Unresolved bibliography citation: '+','.join(unknown))
        links=[f'<a href="#ref-{html.escape(key,quote=True)}" aria-label="Reference {numbers[key]}">{numbers[key]}</a>' for key in keys]
        return '<sup class="citation">['+', '.join(links)+']</sup>'
    return re.sub(r'<span class="citation" data-cites="([^"]+)"[^>]*>.*?</span>',replace,body,flags=re.S)

def normalize_figure_elements(body):
    # Pandoc emits PDF figures as embed elements; offline readers need
    # ordinary images, which embed_images rasterizes from the source PDF.
    body=re.sub(r'<embed\b([^>]*\bsrc=["\'][^"\']+["\'][^>]*)/?>',lambda m:'<img '+m.group(1).rstrip('/ ')+' />',body)
    def describe(match):
        figure=match.group(0)
        caption=re.search(r'<figcaption>(.*?)</figcaption>',figure,re.S)
        alt=html.escape(clean_text(caption.group(1)) if caption else 'Research figure',quote=True)
        return re.sub(r'<img\b(?![^>]*\balt=)',lambda _: '<img alt="'+alt+'"',figure)
    return re.sub(r'<figure\b[^>]*>.*?</figure>',describe,body,flags=re.S)

def restore_equation_references(body,expected_count):
    number=0
    labels={}
    def replace(match):
        nonlocal number
        number+=1
        equation=match.group(0)
        found=re.findall(r'\\label\{([^}]+)\}',equation)
        for label in found:
            labels[label]=number
        anchor=(' id="'+html.escape(found[0],quote=True)+'"') if found else ''
        return f'<span class="display-equation"{anchor} aria-label="Equation {number}"><span class="equation-scroll" tabindex="0" role="region" aria-label="Equation {number}; scroll horizontally if needed">{equation}</span><span class="equation-footer"><span class="equation-hint">Scroll horizontally to read the full equation.</span><span class="equation-number">({number})</span></span></span>'
    body=re.sub(r'<math display="block".*?</math>',replace,body,flags=re.S)
    if number!=expected_count:
        raise ValueError(f'Numbered equation conversion differs: source {expected_count}, HTML {number}')
    def reference(match):
        before,label,after=match.groups()
        if label not in labels:
            raise ValueError('Unresolved equation reference: '+label)
        return before+str(labels[label])+after
    body=re.sub(r'(<a href="#(eq:[^"]+)"[^>]*>).*?(</a>)',reference,body,flags=re.S)
    return body

def clean_text(markup):
    return html.unescape(re.sub('<[^>]+>','',markup)).strip()

def embed_images(body,base):
    images=[]
    def replace(match):
        prefix,src,suffix=match.groups()
        if src.startswith('data:'):
            return match.group(0)
        if re.match(r'https?://',src):
            raise ValueError('External image cannot be included in a self-contained edition: '+src)
        path=(base/html.unescape(src)).resolve()
        if not path.exists():
            path=(ROOT/html.unescape(src)).resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        original=path
        if path.suffix.lower()=='.pdf':
            cache=ROOT/'.cache/browser_figures'
            cache.mkdir(parents=True,exist_ok=True)
            target=cache/(path.stem+'_'+hashlib.sha256(path.read_bytes()).hexdigest()[:10])
            subprocess.run(['pdftoppm','-f','1','-singlefile','-r','150','-png',str(path),str(target)],check=True,capture_output=True)
            path=target.with_suffix('.png')
        mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        content=path.read_bytes()
        images.append({'path':str(original.relative_to(ROOT)) if original.is_relative_to(ROOT) else original.name,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
        return prefix+'data:'+mime+';base64,'+base64.b64encode(content).decode()+suffix
    return re.sub(r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'][^>]*>)',replace,body),images

def add_toc(body):
    entries=[]
    used=set(re.findall(r'\bid=["\']([^"\']+)',body))
    def replace(match):
        level,attrs,content=match.groups()
        text=clean_text(content)
        if not text:return match.group(0)
        found=re.search(r'\bid=["\']([^"\']+)',attrs)
        if found:
            anchor=found.group(1)
        else:
            base='paper-'+re.sub('[^a-z0-9]+','-',text.lower()).strip('-')[:65]
            anchor=base or 'paper-section'
            n=2
            while anchor in used:
                anchor=base+'-'+str(n);n+=1
            used.add(anchor)
            attrs+=' id="'+anchor+'"'
        if int(level)<=2:
            entries.append({'level':int(level),'text':text,'id':anchor})
        return f'<h{level}{attrs}>{content}</h{level}>'
    body=re.sub(r'<h([1-3])([^>]*)>(.*?)</h\1>',replace,body,flags=re.S)
    toc=''.join(f'<a class="depth-{e["level"]}" href="#{html.escape(e["id"],quote=True)}">{html.escape(e["text"])}</a>' for e in entries)
    return body,toc,entries

def main():
    parser=argparse.ArgumentParser(description='Build the complete offline browser edition from the final paper')
    parser.add_argument('--tex',type=pathlib.Path,default=ROOT/'paper/AGI_Alpha_Possibility_Engine.tex')
    parser.add_argument('--body',type=pathlib.Path)
    parser.add_argument('--output',type=pathlib.Path,default=WEB/'index.html')
    parser.add_argument('--allow-draft',action='store_true')
    parser.add_argument('--edition',default='Research edition / 28 October 2026')
    parser.add_argument('--version',default='EventWeaver · research edition v1 · 28 October 2026')
    parser.add_argument('--pdf-link',default='../paper/AGI_Alpha_Possibility_Engine.pdf')
    parser.add_argument('--tex-link',default='../release/AGI_Alpha_Possibility_Engine_LaTeX.zip')
    parser.add_argument('--brief-link',default='../paper/Executive_Brief.pdf')
    parser.add_argument('--archive-link',default='../release/files_manifest.json',help='Companion manifest link; the complete archive is delivered alongside this edition')
    args=parser.parse_args()
    warnings='';draft=False;source_counts={};reference_numbers={}
    if args.body:
        body=args.body.read_text();base=args.body.resolve().parent
        match=re.search(r'<body[^>]*>(.*)</body>',body,re.S)
        if match:body=match.group(1)
    elif args.tex.exists():
        source,reference_numbers,source_counts=prepare_latex(args.tex)
        completed=subprocess.run(['pandoc','--from=latex','--to=html5','--mathml','--section-divs','--wrap=none'],input=source,cwd=args.tex.resolve().parent,capture_output=True,text=True,check=True)
        body,warnings,base=completed.stdout,completed.stderr,args.tex.resolve().parent
    elif args.allow_draft:
        draft=True;base=ROOT
        body='<div class="draft-banner">Development preview. The complete paper will be integrated before release.</div><section><h1>Research edition in preparation</h1><p>This page is a development preview of the reader and executed demonstration. It must not be delivered as the complete research edition.</p></section>'
    else:
        raise FileNotFoundError('Final paper is required. Pass --allow-draft only for local development QA.')
    body=re.sub(r'<script\b.*?</script>','',body,flags=re.S|re.I)
    if reference_numbers:
        body=restore_citations(body,reference_numbers)
    if 'numbered_equations' in source_counts:
        body=restore_equation_references(body,source_counts['numbered_equations'])
    body=normalize_figure_elements(body)
    actual_counts={'tables':len(re.findall(r'<table\b',body)),
                   'figures':len(re.findall(r'<figure\b',body)),
                   'references':len(re.findall(r'id="ref-[^"]+"',body))}
    for key in actual_counts:
        if key in source_counts and actual_counts[key]!=source_counts[key]:
            raise ValueError(f'Incomplete {key} conversion: source {source_counts[key]}, HTML {actual_counts[key]}')
    text=clean_text(body)
    if not args.allow_draft and len(text.split())<500:
        raise ValueError('Complete paper conversion is unexpectedly short; refusing a teaser-only edition')
    body,images=embed_images(body,base)
    body,toc,entries=add_toc(body)
    spec=json.loads((ROOT/'data/demo/spec.json').read_text())
    trace=json.loads((ROOT/'data/demo/trace.json').read_text())
    payload=json.dumps({'spec':spec,'trace':trace},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    substitutions={'CSS':(WEB/'reader.css').read_text(),'JS':(WEB/'demo.js').read_text(),'BODY':body,'TOC':toc,'DATA':payload,'EDITION':html.escape(args.edition),'VERSION':html.escape(args.version),'PDF':html.escape(args.pdf_link,quote=True),'TEX':html.escape(args.tex_link,quote=True),'BRIEF':html.escape(args.brief_link,quote=True),'ARCHIVE':html.escape(args.archive_link,quote=True),'PROTOCOL':'../protocol/technical_v1.json'}
    document=(WEB/'reader_template.html').read_text()
    for key,value in substitutions.items():document=document.replace('@@'+key+'@@',value)
    if re.search(r'@@[A-Z]+@@',document):raise ValueError('Unresolved template placeholder')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(document)
    report={'artifact':str(args.output.resolve()),'draft':draft,'paper_word_count':len(text.split()),'headings':entries,'embedded_images':images,'content_counts':actual_counts,'source_counts':source_counts,'html_bytes':args.output.stat().st_size,'html_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'external_asset_requests':0,'math_rendering':'native MathML; no CDN or online dependency','pandoc_warnings':warnings,'source':str(args.body or args.tex)}
    (ROOT/'results/browser_build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['headings','embedded_images','pandoc_warnings']},indent=2))
    if warnings:print(warnings)

if __name__=='__main__':main()
