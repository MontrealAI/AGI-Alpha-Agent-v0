# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    ('ledger', 'market/inherited/market/canonical/shadow-ledger.mjs', None),
    ('market', 'market/market-transfer-core.mjs',
     ("import {planMission, calculateInvestment} from './inherited/market/canonical/shadow-ledger.mjs';",
      'const {planMission, calculateInvestment} = ledger;')),
    ('adapter', 'market/transfer-adapter.mjs',
     ("import {simulate,defaultConfig} from './market-transfer-core.mjs';",
      'const {simulate,defaultConfig} = market;')),
    ('acceptedAB', 'market/accepted-ab-diagnostic/accepted-ab.mjs',
     ("import {simulate,defaultConfig} from '../market-transfer-core.mjs';",
      'const {simulate,defaultConfig} = market;')),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bundle(root: Path = ROOT) -> tuple[str, list[dict]]:
    parts, records = [], []
    for name, relative, replacement in MODULES:
        raw = (root / relative).read_bytes()
        source = raw.decode('utf-8')
        exports = re.findall(r'^export (?:const|function) ([A-Za-z_$][\w$]*)', source, re.M)
        if not exports or len(exports) != len(set(exports)):
            raise ValueError(f'Unexpected export surface: {relative}')
        transformed = source
        if replacement:
            if transformed.count(replacement[0]) != 1:
                raise ValueError(f'Unexpected import identity: {relative}')
            transformed = transformed.replace(replacement[0], replacement[1], 1)
        transformed = re.sub(r'^export (?=(?:const|function) )', '', transformed, flags=re.M)
        if re.search(r'^\s*(?:import|export)\b', transformed, re.M):
            raise ValueError(f'Unrecognized module syntax: {relative}')
        if '</script' in transformed.lower():
            raise ValueError(f'Unexpected HTML script boundary: {relative}')
        parts.append(f'const {name} = (() => {{\n{transformed}\nreturn {{{", ".join(exports)}}};\n}})();')
        records.append({'path': relative, 'bytes': len(raw), 'sha256': sha(raw),
                        'exports': exports, 'transformedSha256': sha(transformed.encode()),
                        'transformation': 'Exact known import binding substitution; remove declaration export prefixes; isolated closure.'})
    code = 'const TransferEngine = (() => {\n' + '\n'.join(parts)
    code += '\nreturn Object.freeze({...adapter, ...acceptedAB, defaultConfig: market.defaultConfig, sourceHashes: '
    code += json.dumps({r['path']: r['sha256'] for r in records}, sort_keys=True) + '});\n})();'
    return code, records


def build(data_path: Path, output: Path, template: Path | None = None) -> dict:
    data_bytes = data_path.read_bytes()
    data = json.loads(data_bytes)
    if data.get('schema') != 'agi-alpha-transfer-demo/v1':
        raise ValueError('Explicit demo data schema required')
    text = (template or ROOT / 'publication/demo_template.html').read_text()
    if text.count('__STUDY_DATA__') != 1 or text.count('__ENGINE_BUNDLE__') != 1:
        raise ValueError('Exactly one data marker and one engine marker required')
    engine, records = bundle()
    embedded = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    embedded = embedded.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    replacements = {'__STUDY_DATA__': embedded, '__ENGINE_BUNDLE__': engine}
    rendered = re.sub(r'__(?:STUDY_DATA|ENGINE_BUNDLE)__', lambda m: replacements[m.group()], text)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered)
    result = {'schema': 'agi-alpha-transfer-demo-build/v1', 'output': output.name,
              'outputBytes': len(rendered.encode()), 'outputSha256': sha(rendered.encode()),
              'dataSha256': sha(data_bytes), 'templateSha256': sha(text.encode()),
              'bundleSha256': sha(engine.encode()), 'modules': records,
              'boundary': 'UI presentation only. Market arithmetic is the exact versioned market engine and separate accepted-A/B adapter, adapted solely for closure loading.'}
    output.with_suffix('.build.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.data, args.out), indent=2))
