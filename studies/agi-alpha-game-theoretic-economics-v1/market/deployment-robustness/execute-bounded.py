#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Execute the one registered original campaign with hard CPU and wall caps."""
import argparse
import datetime
import json
from pathlib import Path
import resource
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--registration', required=True, help='Public pre-outcome registration URL; provenance only.')
args = parser.parse_args()
here = Path(__file__).resolve().parent
market = here.parent
command = ['node', 'deployment-robustness/run.mjs', '--output', 'deployment-robustness/results-01']
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
start = time.perf_counter_ns()
timed_out = False

def constrain_child():
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))

with (here / 'command-01.log').open('x') as log:
    try:
        result = subprocess.run(command, cwd=market, stdout=log, stderr=subprocess.STDOUT,
                                timeout=120, preexec_fn=constrain_child)
        code = result.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        code = -9

usage = resource.getrusage(resource.RUSAGE_CHILDREN)
receipt = {
    'schema': 'agi-alpha-bounded-deployment-run-resource/v1',
    'startedUTC': started, 'endedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': command, 'returnCode': code, 'wallNanoseconds': time.perf_counter_ns()-start,
    'childUserCPUSeconds': usage.ru_utime, 'childSystemCPUSeconds': usage.ru_stime,
    'childMaxRSSKiB': usage.ru_maxrss, 'hardWallLimitSeconds': 120, 'hardCPULimitSeconds': 120,
    'wallTimedOut': timed_out, 'scientificCutoffUTC': '2026-10-26T18:10:33Z',
    'completeMonetaryCostUSD': None, 'authoringInferenceUSD': None, 'activeHumanMinutes': None,
    'unpricedIncrementalSecondAssetDiscoveryCostUSD': None,
    'observedCustomerCollectionsUSD': 0, 'actualFinancialTransactions': 0,
    'actualSecondInvestments': 0, 'publicRegistration': args.registration,
}
with (here / 'command-01-receipt.json').open('x') as f:
    json.dump(receipt, f, indent=2); f.write('\n')
if code != 0:
    with (here / 'external-execution-failure.json').open('x') as f:
        json.dump({'complete': False, 'partialOutputsPreserved': True, 'returnCode': code,
                   'wallTimedOut': timed_out, 'receipt': 'command-01-receipt.json'}, f, indent=2); f.write('\n')
print(json.dumps(receipt, indent=2))
raise SystemExit(code if code >= 0 else 1)
