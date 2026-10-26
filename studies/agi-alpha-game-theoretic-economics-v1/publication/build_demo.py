# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import base64
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def wrap_module(path, name, dependencies=''):
    source = path.read_text()
    exports = re.findall(r'export\s+(?:function|const|class)\s+([A-Za-z0-9_]+)', source)
    source = re.sub(r'^import .*?;\n', '', source, flags=re.MULTILINE)
    source = re.sub(r'\bexport\s+', '', source)
    return 'const '+name+'=(()=>{\n'+dependencies+'\n'+source+'\nreturn {'+','.join(exports)+'};})();'


def main():
    canonical = wrap_module(ROOT/'market/canonical/shadow-ledger.mjs', 'Canonical')
    core = wrap_module(ROOT/'market/src/market.mjs', 'Market',
                       'const {planMission,calculateInvestment}=Canonical;')
    funding = wrap_module(ROOT/'market/deployment-robustness/funding.mjs', 'Funding')
    production_path = ROOT/'production/joint-summary.json'
    if not production_path.is_file():
        raise RuntimeError('Actual completed new production summary is required')
    evidence = {'production': json.loads(production_path.read_text()),
                'sources': json.loads((ROOT/'calibration/source-manifest.json').read_text())}
    evidence['packets'] = []
    for row in evidence['production'].get('packets', []):
        packet_path = ROOT/'production/packets'/row['packet']
        evidence['packets'].append({**row, 'base64': base64.b64encode(packet_path.read_bytes()).decode()})
    packet = ROOT/'production/export-001/AGI_ALPHA_Upgrade_Decision_Packet.zip'
    html = (ROOT/'publication/demo.template.html').read_text()
    values = {'__CANONICAL_BUNDLE__':canonical, '__MARKET_BUNDLE__':core,
              '__FUNDING_BUNDLE__':funding,
              '__EVIDENCE_JSON__':json.dumps(evidence).replace('</','<\\/'),
              '__PACKET_BASE64__':json.dumps(base64.b64encode(packet.read_bytes()).decode()),
              '__PACKET_NAME__':json.dumps(packet.name)}
    for key,value in values.items():
        html=html.replace(key,value)
    output=ROOT/'deliverables/AGI_ALPHA_Game_Theoretic_Laboratory.html'
    output.write_text(html)
    print(json.dumps({'file':str(output),'bytes':output.stat().st_size}))


if __name__ == '__main__':
    main()
