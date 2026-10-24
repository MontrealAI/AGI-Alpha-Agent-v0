# SPDX-License-Identifier: Apache-2.0
"""Verify the vendored, unchanged Alpha source before importing its runtime."""

import hashlib
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def verify_vendor():
    manifest = json.loads((ROOT / 'vendor' / 'SOURCE.json').read_text())
    for row in manifest['files']:
        path = (ROOT / row['path']).resolve()
        if not path.is_relative_to(ROOT / 'vendor') or path.is_symlink():
            raise ValueError('Vendor path is outside the frozen source snapshot')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Vendored Alpha source changed: ' + row['path'])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != row['git_blob']:
            raise ValueError('Vendored Alpha source differs from the public Git object')
    return manifest


def native_modules():
    verify_vendor()
    prefix = __package__ + '.vendor.alpha_runtime'
    return {name: importlib.import_module(prefix + '.' + name) for name in (
        'models', 'store', 'successor.protocol', 'successor.state',
        'successor.trust', 'successor.jobs')}
