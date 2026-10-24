# SPDX-License-Identifier: Apache-2.0
"""Run the exact pinned publication PDF inspector, without rewriting a file."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pypdf

if pypdf.__version__ != '6.21.1':
    raise SystemExit('Install the exact publication/requirements-papers.lock before validation.')
root=Path(__file__).resolve().parents[1]
module_path=root/'publication/vendor/research_papers.py'
source=json.loads((module_path.parent/'SOURCE.json').read_text())
assert hashlib.sha256(module_path.read_bytes()).hexdigest()==source['sha256']
spec=importlib.util.spec_from_file_location('pinned_paper_inspector',module_path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
target=Path(sys.argv[1]) if len(sys.argv)>1 else root/'paper/paper.pdf'
raw=target.read_bytes()
module.verify_pdf(raw,'Nova-Seeds: The Value That Survives Abundance')
report={'schema':'nova-seeds-passive-pdf-inspection/v1','pdfSha256':hashlib.sha256(raw).hexdigest(),
    'bytes':len(raw),'validatorSource':source,'pypdfVersion':pypdf.__version__,
    'passed':True,'scope':'Exact pinned verify_pdf only; not catalogue, CI, merge, deployment or browser acceptance.'}
print(json.dumps(report,indent=2))
