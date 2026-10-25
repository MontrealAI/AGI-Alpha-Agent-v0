#!/usr/bin/env python3
"""Compile twice in fresh directories; verify byte identity and render all pages."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import shutil
import subprocess
import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
records = []
pdf_bytes = None
for number in (1, 2):
    with TemporaryDirectory(prefix='alpha-economics-clean-') as name:
        build = Path(name)
        (build/'paper').mkdir()
        (build/'figures').mkdir()
        for path in (ROOT/'paper').iterdir():
            if path.suffix in ('.tex', '.bib'):
                shutil.copyfile(path, build/'paper'/path.name)
        for path in (ROOT/'figures').glob('*.pdf'):
            shutil.copyfile(path, build/'figures'/path.name)
        env = dict(os.environ, SOURCE_DATE_EPOCH='1792926950', FORCE_SOURCE_DATE='1', TZ='UTC')
        result = subprocess.run(['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
                                cwd=build/'paper', env=env, capture_output=True, text=True)
        (ROOT/'verification'/f'clean-build-{number}.log').write_text(result.stdout+result.stderr)
        if result.returncode:
            raise SystemExit(f'Clean build {number} failed; see saved log')
        content = (build/'paper/main.pdf').read_bytes()
        log = (build/'paper/main.log').read_text()
        warnings = [line for line in log.splitlines() if any(s in line for s in ('Overfull','undefined','Warning','Error'))]
        records.append({'build':number,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'warnings':warnings})
        pdf_bytes = content
if records[0]['sha256'] != records[1]['sha256']:
    raise SystemExit('Clean builds differ; canonical PDF not replaced')
(ROOT/'paper/main.pdf').write_bytes(pdf_bytes)
pdf = fitz.open(stream=pdf_bytes, filetype='pdf')
images = ROOT/'paper/qa-final'
images.mkdir(exist_ok=True)
pages = []
for number, page in enumerate(pdf,1):
    path = images/f'page-{number:02d}.png'
    previous = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    page.get_pixmap(matrix=fitz.Matrix(1.7,1.7)).save(path)
    Image.open(path).verify()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pages.append({'physical_page':number,'sha256':digest,'unchanged_from_prior_render':digest==previous})
report = {'status':'PASS','clean_builds':records,'byte_identical':True,'source_date_epoch':1792926950,
          'pages':len(pdf),'tex_sha256':hashlib.sha256((ROOT/'paper/main.tex').read_bytes()).hexdigest(),
          'all_rendered_pngs_verified':True,'page_images':pages,
          'visual_review':'see separate page inspection records; image verification is not visual inspection',
          'build_scope':'compilation only; no confirmation rerun'}
(ROOT/'verification/CLEAN_BUILD.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'sha256':records[0]['sha256'],'pages':len(pdf),
                  'changed_page_images':[r['physical_page'] for r in pages if not r['unchanged_from_prior_render']],
                  'warnings':records[0]['warnings']},indent=2))
