# SPDX-License-Identifier: Apache-2.0
"""Structural/evidence checks only; this is not a browser rendering test."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.translations = []
        self.references = []
        self.external_assets = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if 'data-i18n' in a:
            self.translations.append(a['data-i18n'])
        for field in ['href', 'for', 'aria-labelledby', 'aria-describedby']:
            if field not in a:
                continue
            value = a[field]
            if field == 'href' and value.startswith('#'):
                self.references.append(value[1:])
            elif field != 'href':
                self.references.extend(value.split())
        if tag in ('script', 'img', 'iframe', 'audio', 'video', 'source', 'link'):
            for field in ('src', 'href'):
                if a.get(field, '').startswith(('http:', 'https:', '//')):
                    self.external_assets.append(a[field])


html = (HERE/'index.html').read_text()
doc = Document()
doc.feed(html)
data = json.loads(re.search(r'<script id="demo-data" type="application/json">(.*?)</script>', html, re.S).group(1))
copy = json.loads(re.search(r'<script id="demo-copy" type="application/json">(.*?)</script>', html, re.S).group(1))
binding = json.loads((HERE/'binding-record.json').read_text())
checks = []


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)


check('Unique element identifiers', len(doc.ids) == len(set(doc.ids)))
check('Internal links and accessible references resolve', set(doc.references) <= set(doc.ids))
check('No remote executable or visual asset dependencies', not doc.external_assets)
check('EN/FR translation keys are identical', set(copy['en']) == set(copy['fr']))
check('Every static principal label has both translations', set(doc.translations) <= set(copy['en']))
check('No empty translated principal text', all(isinstance(v, str) and v.strip() for c in copy.values() for v in c.values()))
check('Exact generated HTML hash', hashlib.sha256(html.encode()).hexdigest() == binding['outputSha256'])
check('Embedded data agrees with downloadable data', data == json.loads((HERE/'demo-data.json').read_text()))
check('Default example is prospectively selected', data['preselected'] == data['protocol']['experiment']['demonstrationPreselection'])
check('Known actual commercial receipts and jobs remain zero', data['actualEvidence']['collectedRevenueUsd'] == 0 and data['actualEvidence']['acceptedCommercialJobs'] == 0)
check('Actual complete cost remains unknown', data['actualEvidence']['completeStudyCostUsd'] is None)
def digest_file(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
check('Every bound file hash resolves', all(digest_file(ROOT/x['path']) == x['sha256'] for x in data['binding']))
check('No Library identifiers in downloadable source metadata', all('libraryFileId' not in s for s in data['sources']))
check('No unresolved template variables', '__DEMO_' not in html)
if data['status'] == 'PENDING_RESULTS':
    check('Pending panels have no economic worlds', data['results'] is None)
else:
    check('Registered panels carry their full source/result binding', bool(data['results']['boundFiles']))

result = {'schema': 'beyond-beta-demo-structural-qa/v1', 'basis': 'EXECUTED_STATIC_CHECKS_NOT_BROWSER_VISUAL_VERIFICATION', 'status': 'PASS', 'checks': checks, 'htmlSha256': binding['outputSha256'], 'economicWorldsExecuted': 0}
(HERE/'qa-static.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'status': result['status'], 'checks': len(checks), 'basis': result['basis']}))
