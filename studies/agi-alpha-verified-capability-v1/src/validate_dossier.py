# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from acceptance import ROOT, read_json, in_study, reverify, sha256

def validate(baseline: Path, job: Path) -> dict:
    started = time.perf_counter()
    baseline, job = in_study(baseline), in_study(job)
    packet = read_json(baseline / 'packet.json')
    captured = read_json(baseline / 'execution/verification.json')
    checked = reverify(job, baseline / 'execution/delivery/result.json')
    fields = ['status', 'verdict', 'job_id', 'job_sha256', 'result_sha256', 'evidence', 'dependency_edges', 'substantiated_witnesses']
    same = all(captured.get(k) == checked.get(k) for k in fields)
    accepted = same and checked.get('status') == 'COMPLETE' and packet.get('accepted') is True and packet.get('decision') == checked.get('verdict')
    return {'schema':'agi-alpha-independent-admission-reverification/v1','accepted':accepted,'same_semantics':same,
            'job_sha256':sha256(job),'packet_sha256':sha256(baseline / 'packet.json'),
            'original_certificate_sha256':sha256(baseline / 'execution/verification.json'),
            'independent_certificate':checked,'elapsed_seconds':time.perf_counter()-started,
            'claim':'Independent exact-wheel metadata replay, not merely a hash-linked accepted flag.'}

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path,required=True);parser.add_argument('--job',type=Path,required=True)
    args=parser.parse_args(); result=validate(args.baseline,args.job);print(json.dumps(result));raise SystemExit(0 if result['accepted'] else 2)
