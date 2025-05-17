import unittest
import alpha_factory_v1 as af


class PackageTest(unittest.TestCase):
    def test_get_version_consistency(self):
        self.assertEqual(af.get_version(), af.__version__)
        self.assertIsInstance(af.__version__, str)


if __name__ == "__main__":
    unittest.main()
