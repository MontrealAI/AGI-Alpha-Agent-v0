# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parents[1]/'agi-alpha-capability-opportunity-v1'/'integration'
spec=importlib.util.spec_from_file_location('preserved_bridge',PREVIOUS/'bridge.py')
if spec is None or spec.loader is None:
    raise RuntimeError('Missing preserved bridge')
bridge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
sources=bridge.verify_sources()
artifact=ROOT.parent/'instrument'/'capability-v1.zip'
request={'upstream':str(PREVIOUS/'vendor'/'beyond_beta'),'artifact':str(artifact),'out':str(ROOT/'results'),
         'expected_sha256':'32a9c193200f43c94b922c9b7f5460a60a57f44031f1b2c88c8a50b15766a930'}
result=subprocess.run(['node',str(ROOT/'modeled_transfer.mjs')],input=json.dumps(request),text=True,capture_output=True,check=True,timeout=60)
(ROOT/'source-verification.json').write_text(json.dumps({'files_verified':len(sources['files']),
    'source_manifest_sha256':hashlib.sha256((PREVIOUS/'source_manifest.json').read_bytes()).hexdigest(),
    'source_parent':'231834269599d85e49cfe1ca9917a1a874522d44','runtime_parent':'80b345828f34fd8a6e592977dd17ef37141305f4'},indent=2)+'\n')
print(result.stdout)
