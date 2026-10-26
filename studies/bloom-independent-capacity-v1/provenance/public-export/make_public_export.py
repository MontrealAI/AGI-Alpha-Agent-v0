#!/usr/bin/env python3
"""Create explicit public archive variants without publishing credential files.

Only the supplied study tree and its nested ZIPs are inspected. Values of
credential files are used internally for retained-content scans, never logged.
Original files, scientific records, receipts and frozen source remain unchanged.
"""
import argparse, ast, base64, datetime, gzip, hashlib, io, json, pathlib, re, sqlite3, stat, urllib.parse, zipfile

SECRET_NAMES = {'identity.key', 'api.token', '.env', '.env.local', '.env.production', 'credentials.json', 'service-account.json'}
SECRET_SUFFIXES = ('.key', '.token', '.pem', '.p12', '.pfx')
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_DEPTH = 8
FROZEN_PUBLIC_SOURCE = 'integration/native_workflow.py'
FROZEN_MANIFEST_SHA = 'ecd3df2706d034d17a1441c62fd4dba0c7c92f5ea4d22327011bf5e1116bcfbe'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2).encode('utf8') + b'\n'

def secret_name(name):
    base = pathlib.PurePosixPath(name).name.lower()
    return base in SECRET_NAMES or base.endswith(SECRET_SUFFIXES)

def variant_name(name):
    p = pathlib.PurePosixPath(name)
    return str(p.with_name(p.stem + '_PUBLIC_EXPORT.zip'))

def walk_files(root):
    visited = set()
    pending = [root]
    output = []
    while pending:
        item = pending.pop()
        if item.name in {'__pycache__', 'node_modules'}:
            continue
        resolved = item.resolve()
        if resolved in visited:
            continue
        visited.add(resolved)
        if item.is_dir():
            pending.extend(item.iterdir())
        elif item.is_file():
            output.append(item)
    return sorted(output, key=lambda p: p.relative_to(root).as_posix())

def archive_members(data):
    if len(data) > MAX_ARCHIVE_BYTES:
        raise RuntimeError('Archive exceeds public export inspection limit')
    z = zipfile.ZipFile(io.BytesIO(data))
    infos = z.infolist()
    if sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES:
        raise RuntimeError('Expanded archive exceeds public export inspection limit')
    names = set()
    for item in infos:
        p = pathlib.PurePosixPath(item.filename)
        if p.is_absolute() or '..' in p.parts or '\\' in item.filename:
            raise RuntimeError('Unsafe archive member path')
        if item.filename in names:
            raise RuntimeError('Duplicate archive member path')
        names.add(item.filename)
        if item.flag_bits & 1:
            raise RuntimeError('Encrypted archive is not eligible for automatic public export')
        if stat.S_ISLNK(item.external_attr >> 16):
            raise RuntimeError('Archive symlink is not eligible for automatic public export')
    return z, infos

class Export:
    def __init__(self, root, out):
        self.root, self.out = root, out
        self.files = walk_files(root)
        self.patterns = set()
        self.secret_origins = []
        self.schema_checks = []
        self.config_checks = []
        self.public_exceptions = []
        self.archive_mappings = []
        self.direct_omissions = []
        self.freeze = json.loads((root/'protocol/FREEZE.json').read_bytes())
        if sha((root/'protocol/FREEZE.json').read_bytes()) != FROZEN_MANIFEST_SHA:
            raise RuntimeError('Unexpected freeze manifest')
        self.frozen = {r['path']: r['sha256'] for r in self.freeze['files']}
        for rel, digest in self.frozen.items():
            if sha((root/rel).read_bytes()) != digest:
                raise RuntimeError('Frozen source changed: ' + rel)

    def add_secret(self, label, data):
        self.secret_origins.append({'path': label, 'bytes': len(data)})
        candidates = {data, data.strip()}
        for value in candidates:
            if len(value) < 16:
                continue
            self.patterns.update({
                value, value.hex().encode(), value.hex().upper().encode(),
                base64.b64encode(value), base64.urlsafe_b64encode(value),
                base64.urlsafe_b64encode(value).rstrip(b'=')})

    def discover_zip(self, label, data, depth=0):
        if depth > MAX_DEPTH:
            raise RuntimeError('Archive nesting exceeds limit')
        z, infos = archive_members(data)
        with z:
            for item in infos:
                if item.is_dir():
                    continue
                content = z.read(item)
                member = label + '!/' + item.filename
                if secret_name(item.filename):
                    self.add_secret(member, content)
                elif item.filename.lower().endswith('.zip'):
                    self.discover_zip(member, content, depth+1)

    def discover(self):
        for p in self.files:
            rel = p.relative_to(self.root).as_posix()
            data = p.read_bytes()
            if secret_name(rel):
                self.add_secret(rel, data)
                self.direct_omissions.append({
                    'path': rel, 'bytes': len(data),
                    'reason': 'Credential material omitted from public export; original preserved privately.'})
            elif rel.lower().endswith('.zip'):
                self.discover_zip(rel, data)

    def public_source_exception(self, label, data, matches):
        if label != FROZEN_PUBLIC_SOURCE or sha(data) != self.frozen.get(label):
            return False
        # Only literal source spans explicitly declaring PUBLIC TEST/FIXTURE
        # material may contain an internally matched test-token value.
        source = data.decode('utf8')
        lines = data.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        allowed = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
                upper = node.value.upper() if isinstance(node.value, str) else node.value.decode("ascii", "ignore").upper()
                if 'PUBLIC' in upper and ('TEST' in upper or 'FIXTURE' in upper):
                    start = offsets[node.lineno-1] + node.col_offset
                    end = offsets[node.end_lineno-1] + node.end_col_offset
                    allowed.append((start, end, node.lineno))
        matched_lines = set()
        for pattern in matches:
            pos = data.find(pattern)
            while pos >= 0:
                spans = [x for x in allowed if x[0] <= pos and pos+len(pattern) <= x[1]]
                if not spans:
                    return False
                matched_lines.add(spans[0][2])
                pos = data.find(pattern, pos+1)
        self.public_exceptions.append({
            'path': label, 'sha256': sha(data), 'literal_lines': sorted(matched_lines),
            'reason': 'Unchanged frozen source explicitly documents deterministic PUBLIC TEST/FIXTURE values. No private journal credential file is retained.'})
        return True

    def inspect_sqlite(self, label, data):
        # Metadata view only: deserialize WAL-header pages in memory under
        # rollback-journal header flags. Never write these bytes to the export.
        view = bytearray(data)
        view[18:20] = bytes([1, 1])
        db = sqlite3.connect(':memory:')
        db.deserialize(bytes(view))
        tables = []
        try:
            for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
                quoted = '"' + name.replace('"', '""') + '"'
                columns = [{'name': c[1], 'type': c[2]} for c in db.execute('PRAGMA table_info('+quoted+')')]
                count = db.execute('SELECT count(*) FROM '+quoted).fetchone()[0]
                tables.append({'name': name, 'columns': columns, 'rows': count})
        finally:
            db.close()
        self.schema_checks.append({
            'path': label, 'sha256': sha(data), 'credential_pattern_matches': 0,
            'tables': tables, 'original_bytes_preserved': True,
            'scope': 'Names/schema plus full-byte raw/hex/base64 match checks; no cell values printed.'})

    def inspect_config(self, label, data):
        value = json.loads(data)
        if not isinstance(value, dict):
            raise RuntimeError('Unexpected config schema: ' + label)
        u = urllib.parse.urlsplit(str(value.get('llm_url', '')))
        env = value.get('llm_key_env', '')
        flags = {
            'url_contains_no_userinfo': not bool(u.username or u.password),
            'key_env_is_variable_name': isinstance(env, str) and bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', env)),
            'remote_model_disabled': value.get('allow_remote_llm') is False,
            'chain_is_null': value.get('chain') is None}
        if not all(flags.values()):
            raise RuntimeError('Config requires explicit sanitized variant: ' + label)
        for key, field in value.items():
            if re.search(r'(password|private.?key|api.?token|access.?token|secret)', key, re.I):
                if field is not None and field is not False and field != '':
                    raise RuntimeError('Confidential config field requires omission: ' + label)
        self.config_checks.append({
            'path': label, 'sha256': sha(data), 'keys': sorted(value),
            'credential_pattern_matches': 0, 'checks': flags,
            'original_bytes_preserved': True})

    def scan_retained(self, label, data):
        matches = [pattern for pattern in self.patterns if pattern in data]
        if matches and not self.public_source_exception(label, data, matches):
            raise RuntimeError('Credential content in retained file requires an explicit variant/omission: ' + label)
        if data.startswith(b'SQLite format 3\x00'):
            self.inspect_sqlite(label, data)
        if pathlib.PurePosixPath(label).name == 'config.json':
            self.inspect_config(label, data)
        if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----', data):
            # Named key files are already excluded. An embedded credential in
            # another retained file is not silently excused.
            raise RuntimeError('Embedded private key block in retained file: ' + label)

    def scan_zip(self, label, data, depth=0):
        if depth > MAX_DEPTH:
            raise RuntimeError('Archive nesting exceeds limit')
        z, infos = archive_members(data)
        with z:
            for item in infos:
                if item.is_dir() or secret_name(item.filename):
                    continue
                content = z.read(item)
                member = label + '!/' + item.filename
                if item.filename.lower().endswith('.zip'):
                    self.scan_zip(member, content, depth+1)
                elif item.filename.lower().endswith('.gz'):
                    self.scan_retained(member+' [decompressed]', gzip.decompress(content))
                else:
                    self.scan_retained(member, content)

    def scan_all(self):
        for p in self.files:
            rel = p.relative_to(self.root).as_posix()
            if secret_name(rel):
                continue
            data = p.read_bytes()
            if rel.lower().endswith('.zip'):
                self.scan_zip(rel, data)
            elif rel.lower().endswith('.gz'):
                self.scan_retained(rel+' [decompressed]', gzip.decompress(data))
            else:
                self.scan_retained(rel, data)

    def make_zip_variant(self, label, data, public_label, depth=0):
        if depth > MAX_DEPTH:
            raise RuntimeError('Archive nesting exceeds limit')
        z, infos = archive_members(data)
        kept = []
        removed = []
        nested = []
        with z:
            for item in infos:
                if item.is_dir():
                    continue
                content = z.read(item)
                if secret_name(item.filename):
                    removed.append({'path': item.filename, 'bytes': len(content), 'reason': 'credential file omitted'})
                    continue
                new_name = item.filename
                if item.filename.lower().endswith('.zip'):
                    new_name = variant_name(item.filename)
                    child_label = label+'!/'+item.filename
                    child_public = public_label+'!/'+new_name
                    content, child = self.make_zip_variant(child_label, content, child_public, depth+1)
                    nested.append({'original_member': item.filename, 'public_member': new_name,
                                   'original_sha256': child['original_sha256'], 'public_sha256': child['public_sha256']})
                else:
                    self.scan_retained(label+'!/'+item.filename, content)
                kept.append((new_name, content))
        note = {
            'schema': 'bloom-public-archive-variant/v1',
            'original_archive_basename': pathlib.PurePosixPath(label.split('!/')[-1]).name,
            'original_archive_sha256': sha(data),
            'credential_files_removed': removed,
            'nested_archive_variants': nested,
            'original_receipts_unchanged': True,
            'restoration': {
                'historical_original_exact_bytes_included': False,
                'direct_Journal_restore_supported': False,
                'reason': 'Signing keys/API tokens omitted. This is an inspectable public history export, not the original authenticated recovery archive.',
                'recovery_path': 'Run unchanged frozen demo locally in a fresh directory; it regenerates local test identity, original-format backup and actual stopped restoration.'},
            'historical_hash_note': 'Unchanged receipts refer to original private archives. Use this mapping for explicit public variants; historical hashes are not redefined.'}
        kept.append(('PUBLIC_EXPORT_ARCHIVE_MANIFEST.json', canonical(note)))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
            for name, content in sorted(kept):
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = (stat.S_IFREG | 0o644) << 16
                output.writestr(entry, content)
        public_data = stream.getvalue()
        record = {
            'original_path': label, 'original_sha256': sha(data), 'original_bytes': len(data),
            'public_path': public_label, 'public_sha256': sha(public_data), 'public_bytes': len(public_data),
            'direct_removed_entries': removed, 'direct_removed_count': len(removed),
            'nested_archive_variants': nested, 'depth': depth,
            'exact_historical_restore_available': False}
        self.archive_mappings.append(record)
        return public_data, record

    def verify_variant(self, label, data):
        z, infos = archive_members(data)
        with z:
            for item in infos:
                if item.is_dir():
                    continue
                if secret_name(item.filename):
                    raise RuntimeError('Credential file survived public export: ' + label)
                content = z.read(item)
                if item.filename.lower().endswith('.zip'):
                    if not item.filename.endswith('_PUBLIC_EXPORT.zip'):
                        raise RuntimeError('Nested archive is not an explicit public variant: ' + label)
                    self.verify_variant(label+'!/'+item.filename, content)
                else:
                    if any(pattern in content for pattern in self.patterns):
                        raise RuntimeError('Credential pattern survived archive export: ' + label+'!/'+item.filename)

    def run(self):
        self.discover()
        self.scan_all()
        replacements = []
        for p in self.files:
            rel = p.relative_to(self.root).as_posix()
            if not rel.lower().endswith('.zip'):
                continue
            new_rel = variant_name(rel)
            content, mapping = self.make_zip_variant(rel, p.read_bytes(), new_rel)
            self.verify_variant(new_rel, content)
            destination = self.out/'variants'/new_rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            if sha(destination.read_bytes()) != mapping['public_sha256']:
                raise RuntimeError('Reopened public variant hash mismatch')
            replacements.append({
                'exclude_original_path': rel, 'include_public_path': new_rel,
                'variant_file': str(destination), 'original_sha256': mapping['original_sha256'],
                'public_sha256': mapping['public_sha256']})
        protected = []
        for p in self.files:
            rel = p.relative_to(self.root).as_posix()
            if rel in self.frozen or p.name == 'native_workflow_receipt.json' or p.name == 'records.jsonl.gz':
                protected.append({'path': rel, 'sha256': sha(p.read_bytes()), 'public_export_action': 'include unchanged'})
        # Original bytes are checked again after construction.
        for item in protected:
            if sha((self.root/item['path']).read_bytes()) != item['sha256']:
                raise RuntimeError('Protected input changed during export')
        for rel, digest in self.frozen.items():
            if sha((self.root/rel).read_bytes()) != digest:
                raise RuntimeError('Frozen input changed during export')
        report = {
            'schema': 'bloom-public-export/v1',
            'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_tree': 'bloom_study',
            'freeze_manifest_sha256': FROZEN_MANIFEST_SHA,
            'originals_preserved': True,
            'credential_values_printed': False,
            'direct_file_omissions': self.direct_omissions,
            'direct_file_omission_count': len(self.direct_omissions),
            'archive_credential_entry_count_including_nested_duplicates': sum('!/' in x['path'] for x in self.secret_origins),
            'archive_mappings': self.archive_mappings,
            'direct_archive_replacements': replacements,
            'sqlite_checks': self.schema_checks,
            'config_checks': self.config_checks,
            'retained_frozen_public_test_constant_exceptions': self.public_exceptions,
            'protected_unchanged_files': protected,
            'limits': [
                'Public archive variants are not the original authenticated recovery ZIPs.',
                'Without omitted keys/tokens, historical direct Journal.restore is not supported from public variants.',
                'Config and SQLite event records are preserved unchanged after internal raw/hex/base64 pattern and schema checks.',
                'Scientific raw records, original native receipts and all 23 frozen source files remain unchanged.',
                'Original native receipts keep their historical archive names/hashes; they do not attest to public-variant bytes.',
                'The unchanged frozen demo creates new local fixture identity material and executes its actual backup/restore path.']}
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out/'PUBLIC_EXPORT_MANIFEST.json').write_bytes(canonical(report))
        plan = {
            'schema': 'bloom-public-export-plan/v1',
            'source_root': str(self.root),
            'exclude_exact_paths': sorted([x['path'] for x in self.direct_omissions]+[x['exclude_original_path'] for x in replacements]),
            'include_variant_files': replacements,
            'add_documentation': ['PUBLIC_EXPORT.md', 'PUBLIC_EXPORT_MANIFEST.json'],
            'preserve_other_selected_source_files_unchanged': True,
            'never_publish_original_credential_archives': True}
        (self.out/'PUBLIC_EXPORT_PLAN.json').write_bytes(canonical(plan))
        readme = [
            '# BLOOM public evidence export', '',
            'This publication contains a credential-free public evidence export. Original local files and authenticated backup archives are preserved privately. The scientific observations, native execution receipts, source freeze and analysis are unchanged.', '',
            '## What is omitted and what is renamed', '',
            str(len(self.direct_omissions))+' direct identity.key/api.token files are omitted. Five native recovery archives and the all-attempts archive have new filenames ending in _PUBLIC_EXPORT.zip. Nested recovery archives are recursively sanitized and renamed as explicit public variants. '+str(sum('!/' in x['path'] for x in self.secret_origins))+' credential archive entries are removed, counting duplicated nested copies.', '',
            'PUBLIC_EXPORT_MANIFEST.json maps each original archive path and SHA-256 to its public variant path and SHA-256, records removed entry names and counts, and documents config/SQLite inspection. No credential value or digest of a standalone secret is printed in the manifest.', '',
            'The preserved native receipts still describe the original historical runs, original backup names and original backup hashes. Those receipts have not been edited to describe a different archive. Use the export mapping to locate the public history variant. A historical backup hash must not be claimed as the hash of the public variant.', '',
            '## SQLite and configuration', '',
            'Retained SQLite databases have an events table with seq, mission, body, hash and signature columns. Internal scans found no removed credential bytes or their hexadecimal/base64 encodings in retained databases/configs. Configuration contains an environment-variable reference rather than a model credential, has no URL userinfo, disables remote-model calls and has no chain configuration. Original database/config bytes are retained unchanged. Public signatures and identity identifiers are evidence, not secret signing keys.', '',
            'The sole permitted source match is an explicitly documented deterministic PUBLIC TEST/FIXTURE token literal in unchanged frozen integration/native_workflow.py. This is a source-defined local test value, not an operational credential. Private journal identity.key/api.token files are still omitted even when a run used deterministic fixture material.', '',
            '## Restoration and a working recovery path', '',
            '**The sanitized historical archives cannot be supplied as complete authenticated inputs to Journal.restore.** They omit signing keys and local API tokens. They retain inspectable history, configuration and provenance; they do not confer identity, active proof or authority.', '',
            'To exercise actual local backup and stopped restoration, run the unchanged frozen demonstration in a fresh directory after installing its documented prerequisites:', '',
            '    python3 demo.py --case public_case/case.json --method expert --output runs/public-demo', '',
            'The demo regenerates local test-only identity material and produces a new original-format backup that it actually restores in stopped/paused form. Keep newly generated identity.key/api.token files and complete backup ZIPs local. To share its history, apply the public-export rule again. Source/package environment, policy, artifact conditions and current authority must be revalidated; historical proof is not inherited.', '',
            '## Packaging rule', '',
            'Apply PUBLIC_EXPORT_PLAN.json to the study root: omit all exclude_exact_paths; add each variant_file under include_public_path; copy remaining selected scientific/source files without alteration. Add this document and the export manifest. Do not copy a private original ZIP under its old filename, do not silently replace original archive bytes, and do not retain credential files in a second nested archive.', '',
            'No remote publication, transaction, credential rotation or security configuration change is performed by this export. It changes only newly created public copies.', '']
        (self.out/'PUBLIC_EXPORT.md').write_text('\n'.join(readme))
        result = {
            'direct_credential_files_omitted': len(self.direct_omissions),
            'credential_archive_entries_removed_including_duplicates': sum('!/' in x['path'] for x in self.secret_origins),
            'direct_archive_variants': len(replacements), 'archive_variants_including_nested': len(self.archive_mappings),
            'frozen_files_unchanged': len(self.frozen), 'protected_files_unchanged': len(protected),
            'sqlite_checks': len(self.schema_checks), 'config_checks': len(self.config_checks),
            'retained_private_pattern_matches': 0,
            'public_test_source_exceptions': len(self.public_exceptions),
            'manifest_sha256': sha((self.out/'PUBLIC_EXPORT_MANIFEST.json').read_bytes()),
            'plan_path': str(self.out/'PUBLIC_EXPORT_PLAN.json'),
            'documentation_path': str(self.out/'PUBLIC_EXPORT.md')}
        (self.out/'PUBLIC_EXPORT_VERIFICATION.json').write_bytes(canonical(result))
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args=parser.parse_args()
    root=pathlib.Path(args.source).resolve()
    out=pathlib.Path(args.output).resolve()
    if out==root or root in out.parents:
        raise RuntimeError('Public export output must be separate from the original study')
    out.mkdir(parents=True, exist_ok=True)
    Export(root,out).run()
