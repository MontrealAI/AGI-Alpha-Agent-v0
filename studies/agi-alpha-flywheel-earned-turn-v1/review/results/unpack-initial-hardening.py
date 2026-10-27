#!/usr/bin/env python3
"""Verify or restore the exact recorded evidence. No experiment is executed."""
# SPDX-License-Identifier: Apache-2.0
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import stat
import tarfile

ARCHIVE_NAME = 'AGI_ALPHA_Earned_Turn_Raw_Evidence.tar.xz'
ARCHIVE_SHA256 = '8d746fe1ea57fc62bc22213d11bdd8044f9fbf9bd96d69d877cd9c7bf53e8821'
MANIFEST_PATH = 'publication/RAW_EVIDENCE_MANIFEST.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def parent_descriptor(root, parts):
    """Walk beneath root using directory descriptors; never follow symlink parents."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.open(root, flags)
    try:
        for part in parts:
            try:
                os.mkdir(part, mode=0o755, dir_fd=current)
            except FileExistsError:
                pass
            try:
                child = os.open(part, flags, dir_fd=current)
            except OSError as error:
                raise SystemExit(f'Refusing non-directory or symlink evidence parent: {part}') from error
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def already_exact(parent, name, spec):
    """Recognize an existing regular file without following even a dangling symlink."""
    try:
        existing = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise SystemExit(f'Refusing unsafe existing evidence: {name}') from error
    with os.fdopen(existing, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != spec['bytes']:
            raise SystemExit(f'Refusing to overwrite different existing evidence: {name}')
        if hashlib.file_digest(stream, 'sha256').hexdigest() != spec['sha256']:
            raise SystemExit(f'Refusing to overwrite different existing evidence: {name}')
    return True


def restore_member(root, pure, data, spec):
    """Install verified bytes atomically without replacing an existing destination."""
    parent = parent_descriptor(root, pure.parts[:-1])
    temporary = None
    try:
        name = pure.name
        if already_exact(parent, name, spec):
            return False
        for _ in range(16):
            proposed = '.evidence-' + secrets.token_hex(12)
            try:
                descriptor = os.open(proposed, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=parent)
                temporary = proposed
                break
            except FileExistsError:
                continue
        else:
            raise SystemExit('Could not allocate a unique evidence staging file.')
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        except FileExistsError:
            # Another writer may have created the destination after the first check.
            # A matching file is preserved; a different file is never replaced.
            if already_exact(parent, name, spec):
                return False
            raise SystemExit(f'Evidence destination changed during restoration: {name}')
        os.fsync(parent)
        return True
    finally:
        if temporary is not None:
            os.unlink(temporary, dir_fd=parent)
        os.close(parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--verify-only', action='store_true', help='Read and hash all members without extracting.')
    args = parser.parse_args()
    if not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise SystemExit('Exact safe restoration requires the documented Linux/POSIX environment.')
    if args.root.is_symlink():
        raise SystemExit('Refusing a symlink evidence root.')
    root = args.root.resolve()
    archive = args.archive or root / 'evidence' / ARCHIVE_NAME
    if not archive.is_file():
        raise SystemExit('Raw evidence archive missing. Use the complete companion or pass --archive PATH.')
    if digest(archive) != ARCHIVE_SHA256:
        raise SystemExit('Raw evidence archive SHA-256 mismatch; no files were restored.')
    manifest_file = root / MANIFEST_PATH
    manifest_bytes = manifest_file.read_bytes()
    manifest = json.loads(manifest_bytes)
    expected = dict(manifest['files'])
    expected[MANIFEST_PATH] = {'bytes': len(manifest_bytes), 'sha256': hashlib.sha256(manifest_bytes).hexdigest()}
    seen = set()
    restored = skipped = 0
    with tarfile.open(archive, 'r|xz') as packed:
        for member in packed:
            name = member.name
            pure = PurePosixPath(name)
            if not member.isfile() or pure.is_absolute() or '..' in pure.parts or name != pure.as_posix() or name not in expected or name in seen:
                raise SystemExit(f'Unexpected or unsafe archive member: {name}')
            seen.add(name)
            target = root.joinpath(*pure.parts)
            if not target.resolve().is_relative_to(root):
                raise SystemExit(f'Escaping destination: {name}')
            spec = expected[name]
            if member.size != spec['bytes']:
                raise SystemExit(f'Member size mismatch: {name}')
            data = packed.extractfile(member).read()
            if len(data) != spec['bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
                raise SystemExit(f'Member identity mismatch: {name}')
            if args.verify_only:
                continue
            if restore_member(root, pure, data, spec):
                restored += 1
            else:
                skipped += 1
    if seen != set(expected):
        raise SystemExit(f'Missing members: {sorted(set(expected) - seen)}')
    print(json.dumps({'status': 'PASS', 'archive_sha256': ARCHIVE_SHA256,
                      'verified_members': len(seen), 'restored': restored, 'already_exact': skipped,
                      'mode': 'VERIFY_ONLY' if args.verify_only else 'RESTORE_EXACT_EVIDENCE'}))


if __name__ == '__main__':
    main()
