"""Small packaging fixtures only: no study solver, old confirmation or raw trial replay."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('earned_unpack', ROOT / 'unpack_evidence.py')
unpack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(unpack)

def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

class ExactRestorationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='earned-extractor-')
        self.base = Path(self.temporary.name)
        self.root = self.base / 'root'
        self.root.mkdir()
        self.data = b'{"record":"checked synthetic fixture"}\n'
        self.relative = PurePosixPath('records/output.json')

    def tearDown(self):
        self.temporary.cleanup()

    def restore(self):
        return unpack.restore_member(self.root, self.relative, self.data, identity(self.data))

    def destination(self):
        return self.root / self.relative

    def fixture(self, entries=None, expected=None):
        entries = entries if entries is not None else [(str(self.relative), self.data, tarfile.REGTYPE)]
        expected = expected if expected is not None else {str(self.relative): identity(self.data)}
        manifest = json.dumps({'schema': 'fixture/v1', 'files': expected}).encode()
        manifest_path = self.root / unpack.MANIFEST_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(manifest)
        archive = self.base / 'fixture.tar.xz'
        with tarfile.open(archive, 'w:xz') as out:
            for name, data, kind in [(unpack.MANIFEST_PATH, manifest, tarfile.REGTYPE)] + entries:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.size = len(data) if kind == tarfile.REGTYPE else 0
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    info.linkname = '../outside'
                out.addfile(info, io.BytesIO(data) if info.size else None)
        return archive

    def main(self, archive, verify=False, root=None, expected_digest=None):
        # Explicit fixture pin in memory; the delivered extractor's literal pin is unchanged.
        pin = expected_digest or unpack.digest(archive)
        argv = ['unpack_evidence.py', '--root', str(root or self.root), '--archive', str(archive)]
        if verify:
            argv.append('--verify-only')
        output = io.StringIO()
        with patch.object(unpack, 'ARCHIVE_SHA256', pin), patch.object(sys, 'argv', argv), contextlib.redirect_stdout(output):
            unpack.main()
        return json.loads(output.getvalue())

    def test_exact_install_then_idempotent_skip(self):
        self.assertTrue(self.restore())
        self.assertFalse(self.restore())
        self.assertEqual(self.destination().read_bytes(), self.data)
        self.assertEqual(list(self.destination().parent.glob('.evidence-*')), [])

    def test_different_existing_file_preserved(self):
        self.destination().parent.mkdir()
        self.destination().write_bytes(b'prior evidence')
        with self.assertRaises(SystemExit): self.restore()
        self.assertEqual(self.destination().read_bytes(), b'prior evidence')

    def test_dangling_destination_symlink_refused(self):
        self.destination().parent.mkdir()
        self.destination().symlink_to(self.root / 'missing')
        with self.assertRaises(SystemExit): self.restore()
        self.assertTrue(self.destination().is_symlink())
        self.assertFalse((self.root / 'missing').exists())

    def test_live_destination_symlink_refused(self):
        self.destination().parent.mkdir()
        other = self.root / 'other'
        other.write_bytes(self.data)
        self.destination().symlink_to(other)
        with self.assertRaises(SystemExit): self.restore()
        self.assertTrue(self.destination().is_symlink())
        self.assertEqual(other.read_bytes(), self.data)

    def test_inside_symlink_parent_refused(self):
        other = self.root / 'other'
        other.mkdir()
        (self.root / 'records').symlink_to(other, target_is_directory=True)
        with self.assertRaises(SystemExit): self.restore()
        self.assertEqual(list(other.iterdir()), [])

    def test_outside_symlink_parent_refused(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (self.root / 'records').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(SystemExit): self.restore()
        self.assertEqual(list(outside.iterdir()), [])

    def test_non_directory_parent_refused(self):
        (self.root / 'records').write_bytes(b'existing file')
        with self.assertRaises(SystemExit): self.restore()
        self.assertEqual((self.root / 'records').read_bytes(), b'existing file')

    def test_directory_destination_preserved(self):
        self.destination().mkdir(parents=True)
        with self.assertRaises(SystemExit): self.restore()
        self.assertTrue(self.destination().is_dir())

    def test_concurrent_different_destination_never_clobbered(self):
        original_link = os.link
        def race(src, dst, **kwargs):
            descriptor = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=kwargs['dst_dir_fd'])
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(b'concurrently created evidence')
            return original_link(src, dst, **kwargs)
        with patch.object(unpack.os, 'link', side_effect=race), self.assertRaises(SystemExit): self.restore()
        self.assertEqual(self.destination().read_bytes(), b'concurrently created evidence')
        self.assertEqual(list(self.destination().parent.glob('.evidence-*')), [])

    def test_concurrent_identical_destination_preserved(self):
        original_link = os.link
        def race(src, dst, **kwargs):
            descriptor = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=kwargs['dst_dir_fd'])
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(self.data)
            return original_link(src, dst, **kwargs)
        with patch.object(unpack.os, 'link', side_effect=race): self.assertFalse(self.restore())
        self.assertEqual(self.destination().read_bytes(), self.data)

    def test_fixture_restore_and_verify(self):
        archive = self.fixture()
        verified = self.main(archive, verify=True)
        self.assertEqual(verified['verified_members'], 2)
        self.assertFalse(self.destination().exists())
        restored = self.main(archive)
        self.assertEqual(restored['restored'], 1)
        self.assertEqual(restored['already_exact'], 1)
        self.assertEqual(self.main(archive)['already_exact'], 2)

    def test_archive_digest_mismatch_writes_nothing(self):
        archive = self.fixture()
        with self.assertRaises(SystemExit): self.main(archive, expected_digest='0' * 64)
        self.assertFalse(self.destination().exists())

    def test_payload_identity_mismatch_refused(self):
        archive = self.fixture(entries=[(str(self.relative), b'x' * len(self.data), tarfile.REGTYPE)])
        with self.assertRaises(SystemExit): self.main(archive)
        self.assertFalse(self.destination().exists())

    def test_payload_size_mismatch_refused(self):
        archive = self.fixture(entries=[(str(self.relative), b'x', tarfile.REGTYPE)])
        with self.assertRaises(SystemExit): self.main(archive)
        self.assertFalse(self.destination().exists())

    def test_traversal_member_refused(self):
        archive = self.fixture(entries=[('../escape', self.data, tarfile.REGTYPE)], expected={'../escape': identity(self.data)})
        with self.assertRaises(SystemExit): self.main(archive)
        self.assertFalse((self.base / 'escape').exists())

    def test_noncanonical_alias_refused(self):
        archive = self.fixture(entries=[('records//output.json', self.data, tarfile.REGTYPE)], expected={'records//output.json': identity(self.data)})
        with self.assertRaises(SystemExit): self.main(archive)
        self.assertFalse(self.destination().exists())

    def test_archive_link_members_refused(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            archive = self.fixture(entries=[(str(self.relative), b'', kind)])
            with self.assertRaises(SystemExit): self.main(archive)
            self.assertFalse(self.destination().exists())

    def test_duplicate_member_refused_with_exact_prefix_preserved(self):
        archive = self.fixture(entries=[(str(self.relative), self.data, tarfile.REGTYPE)] * 2)
        with self.assertRaises(SystemExit): self.main(archive)
        self.assertEqual(self.destination().read_bytes(), self.data)

    def test_missing_member_refused(self):
        archive = self.fixture(entries=[])
        with self.assertRaises(SystemExit): self.main(archive)
        self.assertFalse(self.destination().exists())

    def test_symlink_root_refused(self):
        archive = self.fixture()
        alias = self.base / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(SystemExit): self.main(archive, root=alias)

if __name__ == '__main__':
    unittest.main(verbosity=2)
