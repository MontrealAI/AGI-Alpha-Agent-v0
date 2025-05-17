import unittest
import alpha_factory_v1 as af

class VersionTest(unittest.TestCase):
    def test_version_string(self):
        version = af.get_version()
        self.assertIsInstance(version, str)
        self.assertTrue(version)

if __name__ == '__main__':
    unittest.main()
