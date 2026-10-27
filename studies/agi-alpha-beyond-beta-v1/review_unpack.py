#!/usr/bin/env python3
"""Verify and restore this compact repository edition at original relative paths."""
from pathlib import Path, PurePosixPath
import argparse,gzip,hashlib,json,stat,zipfile
ROOT=Path(__file__).resolve().parent
LIMIT=256*1024*1024
sha=lambda b:hashlib.sha256(b).hexdigest()

def safe_target(name):
    path=PurePosixPath(name)
    if not name or '\\' in name or ':' in name or path.is_absolute() or any(x in {'.','..',''} for x in path.parts):
        raise ValueError('Unsafe archive path: '+name)
    target=ROOT.joinpath(*path.parts)
    if not target.resolve().is_relative_to(ROOT):raise ValueError('Archive path leaves project: '+name)
    current=ROOT
    for part in path.parts:
        current=current/part
        if current.is_symlink():raise ValueError('Refusing a symlink target: '+name)
    return target

def main(check_only=False):
    manifest=json.loads((ROOT/'review_bundle_manifest.json').read_text())
    archive=safe_target(manifest['archive'])
    if sha(archive.read_bytes())!=manifest['archive_sha256']:raise ValueError('Changed review archive')
    expected={x['path']:x for x in manifest['members']}
    if len(expected)!=len(manifest['members']):raise ValueError('Duplicate manifest path')
    if manifest['uncompressed_bytes']>LIMIT:raise ValueError('Declared payload exceeds limit')
    plans=[]
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(expected):raise ValueError('Unexpected archive members')
        if sum(x.file_size for x in z.infolist())!=manifest['uncompressed_bytes']:raise ValueError('Unexpected total length')
        for info in z.infolist():
            if stat.S_ISLNK(info.external_attr>>16) or info.is_dir():raise ValueError('Nonregular archive entry')
            target=safe_target(info.filename);entry=expected[info.filename]
            if info.file_size!=entry['bytes'] or info.file_size>LIMIT:raise ValueError('Unexpected member length')
            data=z.read(info)
            if sha(data)!=entry['sha256']:raise ValueError('Changed payload: '+info.filename)
            plans.append((target,data))
    demo=manifest.get('demo_gzip')
    if demo:
        packed=safe_target(demo['archive_path'])
        if sha(packed.read_bytes())!=demo['compressed_sha256']:raise ValueError('Changed demo gzip')
        with gzip.open(packed,'rb') as f:data=f.read(LIMIT+1)
        if len(data)!=demo['bytes'] or sha(data)!=demo['sha256']:raise ValueError('Changed expanded demo')
        plans.append((safe_target(demo['destination']),data))
    # Validate every destination before performing any write. Existing identical
    # bytes are harmless; differing files are never overwritten automatically.
    for target,data in plans:
        if target.exists() and (not target.is_file() or sha(target.read_bytes())!=sha(data)):
            raise ValueError('Refusing to overwrite differing existing file: '+str(target.relative_to(ROOT)))
    if not check_only:
        for target,data in plans:
            if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps({'status':'PASS','checked_files':len(plans),'uncompressed_bytes':sum(len(data) for _,data in plans),'restored':not check_only}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');main(parser.parse_args().check_only)
