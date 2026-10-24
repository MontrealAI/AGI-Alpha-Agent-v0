#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Subprocess-control regressions only; these tests do not execute an EVM."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from typing import Any


RUNNER = Path(__file__).with_name('qualification-runner.py').resolve()
CHILD = r'''
import importlib.util, json, os, pathlib, sys
spec = importlib.util.spec_from_file_location('qualification_runner', sys.argv[1])
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
output = pathlib.Path(sys.argv[2])
try:
    runner.claim_output(output, kind='subprocess-regression-fixtures-NOT-EVM')
except FileExistsError:
    sys.exit(2)
commands = json.loads(sys.argv[3])
sys.exit(runner.run_commands(output, output.parent, dict(os.environ), commands[0], commands[1], float(sys.argv[4])))
'''


def fixture(exit_code: int = 0, timeout: bool = False) -> list[str]:
    """Return an explicit subprocess-control fixture, never an EVM command."""
    program = (
        "import sys,time; print('fixture-stdout',flush=True); "
        "print('fixture-stderr',file=sys.stderr,flush=True); "
        + ('time.sleep(10)' if timeout else 'sys.exit(' + str(exit_code) + ')')
    )
    return [sys.executable, '-c', program]


class QualificationRunnerTests(unittest.TestCase):
    """Check actual child-process exit behavior and retained evidence."""

    def setUp(self) -> None:
        """Allocate isolated disposable directories for each control case."""
        self.temporary = tempfile.TemporaryDirectory(prefix='qualification-regression-')
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / 'evidence'

    def run_pipeline(
        self, tests: list[str], separate_fixture: list[str], timeout: float = 2,
    ) -> subprocess.CompletedProcess[str]:
        """Execute the runner pipeline in a separate interpreter process."""
        return subprocess.run(
            [sys.executable, '-c', CHILD, str(RUNNER), str(self.output),
             json.dumps([tests, separate_fixture]), str(timeout)],
            capture_output=True, text=True, timeout=8,
        )

    def record(self, name: str) -> dict[str, Any]:
        """Read a retained result produced by the child interpreter."""
        return json.loads((self.output / name).read_text())

    def assert_stream_custody(self, label: str) -> None:
        """Verify both stream bytes and their independently recomputed hashes."""
        record = self.record(label + '-execution.json')
        self.assertIn('startedAtUtc', record)
        self.assertIn('endedAtUtc', record)
        self.assertGreaterEqual(record['elapsedSeconds'], 0)
        for stream in ['stdout', 'stderr']:
            data = (self.output / record[stream]['path']).read_bytes()
            self.assertEqual(record[stream]['bytes'], len(data))
            self.assertEqual(record[stream]['sha256'], hashlib.sha256(data).hexdigest())
            self.assertIn(('fixture-' + stream).encode(), data)

    def test_success_runs_both_stages_and_retains_streams(self) -> None:
        """Success runs both stages and retains each subprocess stream."""
        completed = self.run_pipeline(fixture(), fixture())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.record('qualification-summary.json')['wrapperExitCode'], 0)
        self.assertTrue(self.record('qualification-summary.json')['fixtureExecuted'])
        self.assert_stream_custody('tests')
        self.assert_stream_custody('separate-fixture')

    def test_test_failure_propagates_after_record_and_skips_fixture(self) -> None:
        """A failed test process cannot become a successful wrapper process."""
        completed = self.run_pipeline(fixture(17), fixture())
        self.assertEqual(completed.returncode, 17, completed.stderr)
        self.assertEqual(self.record('tests-execution.json')['exitCode'], 17)
        self.assertFalse(self.record('qualification-summary.json')['fixtureExecuted'])
        self.assertFalse((self.output / 'separate-fixture-execution.json').exists())
        self.assert_stream_custody('tests')

    def test_test_timeout_propagates_124_after_record_and_skips_fixture(self) -> None:
        """A test timeout keeps partial streams and prevents fixture execution."""
        completed = self.run_pipeline(fixture(timeout=True), fixture(), timeout=0.5)
        self.assertEqual(completed.returncode, 124, completed.stderr)
        self.assertTrue(self.record('tests-execution.json')['timedOut'])
        self.assertIsNone(self.record('tests-execution.json')['exitCode'])
        self.assertFalse(self.record('qualification-summary.json')['fixtureExecuted'])
        self.assert_stream_custody('tests')

    def test_fixture_failure_propagates_after_both_records(self) -> None:
        """A failing fixture propagates after the successful test receipt."""
        completed = self.run_pipeline(fixture(), fixture(19))
        self.assertEqual(completed.returncode, 19, completed.stderr)
        self.assertEqual(self.record('tests-execution.json')['exitCode'], 0)
        self.assertEqual(self.record('separate-fixture-execution.json')['exitCode'], 19)
        self.assert_stream_custody('tests')
        self.assert_stream_custody('separate-fixture')

    def test_fixture_timeout_propagates_124_after_both_records(self) -> None:
        """A fixture timeout keeps both stages' available evidence."""
        completed = self.run_pipeline(fixture(), fixture(timeout=True), timeout=0.5)
        self.assertEqual(completed.returncode, 124, completed.stderr)
        self.assertEqual(self.record('tests-execution.json')['exitCode'], 0)
        self.assertTrue(self.record('separate-fixture-execution.json')['timedOut'])
        self.assert_stream_custody('tests')
        self.assert_stream_custody('separate-fixture')

    def test_existing_output_is_refused_without_modifying_any_bytes(self) -> None:
        """A second qualification cannot overwrite a prior evidence directory."""
        self.output.mkdir()
        existing = self.output / 'prior-evidence.json'
        existing.write_bytes(b'{"preserved":true}\n')
        before = {path.name: path.read_bytes() for path in self.output.iterdir()}
        completed = self.run_pipeline(fixture(), fixture())
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.output.iterdir()})

    def test_public_cli_refuses_nonempty_output_before_source_access(self) -> None:
        """The public CLI applies the same refusal before touching source."""
        self.output.mkdir()
        (self.output / 'preserved.txt').write_bytes(b'original')
        completed = subprocess.run(
            [sys.executable, str(RUNNER), '--source', str(self.output / 'missing-source'),
             '--output', str(self.output)], capture_output=True, text=True, timeout=8,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertIn('Refusing nonempty', completed.stderr)
        self.assertEqual([path.name for path in self.output.iterdir()], ['preserved.txt'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
