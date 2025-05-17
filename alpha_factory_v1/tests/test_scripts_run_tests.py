import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from alpha_factory_v1.scripts import run_tests


class RunTestsScriptTest(unittest.TestCase):
    def test_path_must_exist(self):
        with self.assertRaises(SystemExit):
            with mock.patch.object(sys, 'argv', ['run_tests.py', '/nope']):
                run_tests.main()

    def test_uses_pytest_when_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            with mock.patch('importlib.util.find_spec', return_value=object()):
                with mock.patch('subprocess.call', return_value=0) as call:
                    with mock.patch.object(sys, 'argv', ['run_tests.py', str(target)]):
                        with self.assertRaises(SystemExit):
                            run_tests.main()
                    call.assert_called_once()
                    self.assertIn('pytest', call.call_args[0][0])

    def test_falls_back_to_unittest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            with mock.patch('importlib.util.find_spec', return_value=None):
                with mock.patch('subprocess.call', return_value=0) as call:
                    with mock.patch.object(sys, 'argv', ['run_tests.py', str(target)]):
                        with self.assertRaises(SystemExit):
                            run_tests.main()
                    call.assert_called_once()
                    self.assertIn('unittest', call.call_args[0][0])

    def test_defaults_to_tests_directory(self):
        with mock.patch('importlib.util.find_spec', return_value=object()):
            with mock.patch('subprocess.call', return_value=0) as call:
                with mock.patch.object(sys, 'argv', ['run_tests.py']):
                    with self.assertRaises(SystemExit):
                        run_tests.main()
                call.assert_called_once()
                self.assertTrue(str(call.call_args[0][0][-1]).endswith('tests'))


if __name__ == '__main__':
    unittest.main()
