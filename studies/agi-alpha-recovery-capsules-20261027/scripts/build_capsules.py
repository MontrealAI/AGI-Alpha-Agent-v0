# SPDX-License-Identifier: Apache-2.0
import difflib, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = [
    (".get_feature_names()", ".get_feature_names_out()", "Use the maintained feature-name API; feature order is checked."),
    ("from sklearn.preprocessing import Imputer", "from sklearn.impute import SimpleImputer as Imputer", "Preserve mean imputation while replacing removed estimator."),
    ("axis='col'", "axis=1", "Preserve horizontal concatenation."),
    ("pd.concat([df5, df6], join_axes=[df5.columns])", "pd.concat([df5, df6]).reindex(columns=df5.columns)", "Preserve left column projection; do not silently change to intersection."),
    ("df1.append(df2)", "pd.concat([df1, df2])", "Preserve row concatenation and original labels.")
]

def build(path):
    raw = path.read_bytes()
    notebook = json.loads(raw)
    changes = []
    for index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] != 'code':
            raise ValueError('Only MIT code-only inputs are admitted')
        before = ''.join(cell['source'])
        after = before
        for old, new, reason in RULES:
            if old in after:
                after = after.replace(old, new)
                changes.append({'cell': index, 'upstream_cell': cell['metadata'].get('upstream_cell_index'), 'old': old, 'new': new, 'reason': reason})
        cell['source'] = after.splitlines(keepends=True)
        cell['outputs'], cell['execution_count'] = [], None
    case = path.stem
    out = ROOT/'deliveries'/case
    out.mkdir(parents=True, exist_ok=True)
    target = out/'recovered.ipynb'
    target.write_text(json.dumps(notebook, indent=2)+'\n')
    (out/'changes.json').write_text(json.dumps(changes, indent=2)+'\n')
    original = [''.join(c['source']) for c in json.loads(raw)['cells']]
    repaired = [''.join(c['source']) for c in notebook['cells']]
    (out/'migration.diff').write_text(''.join(difflib.unified_diff('\n\n'.join(original).splitlines(True), '\n\n'.join(repaired).splitlines(True), fromfile='original code', tofile='recovered code')))
    identity = {'input': str(path.relative_to(ROOT)), 'input_sha256': hashlib.sha256(raw).hexdigest(), 'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'code_cells': len(notebook['cells']), 'phase': path.parent.name, 'source': notebook.get('metadata', {}), 'rules_revision': 'development-v2 preserves notebook inline plotting; original v1 retained in evidence'}
    (out/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    print(case, 'changes', len(changes))

if __name__ == '__main__':
    for path in sorted((ROOT/'inputs'/'development').glob('*.ipynb')):
        build(path)
