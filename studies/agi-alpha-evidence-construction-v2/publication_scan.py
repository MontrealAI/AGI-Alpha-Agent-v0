# SPDX-License-Identifier: Apache-2.0
"""Bounded local publication scan; report locations and digests, never secret values."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parent
RULES = {
    'signed-cloud-query': rb'(?i)(?:X-Amz-(?:Signature|Credential|Security-Token)|X-Goog-(?:Signature|Credential))=[^\s\"<>]{12,}',
    'signed-azure-query': rb'(?i)[?&]sig=[A-Za-z0-9%+/=_-]{24,}',
    'pem-private-key': rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
    'github-token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b',
    'provider-secret-key': rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b',
    'aws-access-key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'bearer-value': rb'(?i)\bbearer\s+[A-Za-z0-9_.+/=-]{32,}',
    'jwt-shaped-value': rb'\beyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b',
    'assigned-secret-value': rb'(?i)[\"\'](?:api_key|access_token|refresh_token|client_secret)[\"\']\s*[:=]\s*[\"\'][A-Za-z0-9_.+/=-]{24,}[\"\']',
}


def scan(output: Path) -> dict:
    excluded = json.loads((ROOT / 'assay/source_packet/source_receipt.json').read_text())['excluded_from_redistribution']
    forbidden = {x['file'] for x in excluded} | {'source_packet.tar.gz'}
    findings = []
    records = []
    archive_entries = 0

    def inspect(label: str, data: bytes) -> None:
        for rule, expression in RULES.items():
            for match in re.finditer(expression, data):
                findings.append({'path': label, 'rule': rule,
                                 'byte_offset': match.start(),
                                 'line': data[:match.start()].count(b'\n') + 1,
                                 'match_sha256': hashlib.sha256(match.group()).hexdigest()})

    for path in sorted(ROOT.rglob('*')):
        if '__pycache__' in path.parts or path.suffix == '.pyc' or path == output:
            continue
        if path.is_symlink():
            findings.append({'path': str(path.relative_to(ROOT)), 'rule': 'unexpected-symlink'})
            continue
        if not path.is_file():
            continue
        label = str(path.relative_to(ROOT))
        if path.name in forbidden:
            findings.append({'path': label, 'rule': 'excluded-source-file-present'})
        data = path.read_bytes()
        records.append({'path': label, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        inspect(label, data)
        if zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for entry in archive.infolist():
                    if entry.is_dir():
                        continue
                    archive_entries += 1
                    member_label = label + '::' + entry.filename
                    if Path(entry.filename).name in forbidden:
                        findings.append({'path': member_label, 'rule': 'excluded-source-file-in-archive'})
                    if entry.file_size > 20_000_000 or entry.flag_bits & 1:
                        findings.append({'path': member_label, 'rule': 'archive-member-not-inspected'})
                        continue
                    inspect(member_label, archive.read(entry))
    result = {'schema': 'bounded-publication-scan/v1',
              'scanned_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'Only this new study directory; no predecessor or private workspace scan',
              'status': 'NO_PATTERN_FINDINGS' if not findings else 'REVIEW_REQUIRED',
              'file_count': len(records), 'zip_entries_inspected': archive_entries,
              'bytes_scanned_as_files': sum(x['bytes'] for x in records),
              'rules': list(RULES), 'forbidden_source_names_checked': sorted(forbidden),
              'findings': findings, 'files': records,
              'limits': ['A bounded pattern scan is not proof that no secret or restricted content exists.',
                         'Raw bytes and decompressed ZIP/DOCX members are scanned; compressed PDF streams are not decoded.',
                         'Published text companions cover the research PDFs; images, encodings and arbitrary encrypted content are not inspected.',
                         'OSF raw-data licenses remain unverified; excluded filenames must remain absent.',
                         'Historical absolute scratch paths are provenance, not required installed locations.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'validation/publication-scan.json')
    args = parser.parse_args()
    result = scan(args.out.resolve())
    print(json.dumps({k: result[k] for k in ['status', 'file_count', 'zip_entries_inspected', 'findings']}, indent=2))
    raise SystemExit(0 if not result['findings'] else 1)
