# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREDECESSOR = ROOT.parents[1] / 'agi-alpha-capability-opportunity-v1' / 'integration'

def run(artifact: Path, out: Path) -> dict:
    sys.path.insert(0, str(PREDECESSOR))
    from run_integration import run as previous_run
    result = previous_run(artifact.resolve(), out)
    receipt = {
        'schema': 'opportunity-discovery-inherited-controls/v1',
        'source_parent': '231834269599d85e49cfe1ca9917a1a874522d44',
        'runtime_parent': '80b345828f34fd8a6e592977dd17ef37141305f4',
        'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
        'inherited_control_summary': 'summary.json',
        'passed': result['passed'], 'total': result['total'],
        'scope': 'Existing unchanged research lifecycle and native Journal/trust/A-B-C accounting conformance.',
        'new_registry_created': False,
        'production_scope_changed': False,
        'empirical_alpha_admission': False,
        'authority': 'SIMULATED_ENS_IDENTITIES_AND_EPHEMERAL_LOCAL_KEYS',
        'actual_customer_collections_usd': 0,
        'actual_frontier_evaluation': False,
        'recipient_execution': 'Separate recipient process must execute recovered bytes on fresh mission inputs.',
        'limitation': 'Artificial positive monetary evidence reaches access branches only; it is not earned Alpha.'
    }
    (out / 'inherited-controls.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args.artifact, args.out)
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt['passed'] == receipt['total'] else 1)
