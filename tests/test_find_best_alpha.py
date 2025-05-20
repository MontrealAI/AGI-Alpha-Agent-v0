import json
import subprocess
from pathlib import Path
import sys
import unittest

EXAMPLE_DIR = Path(__file__).parent / 'alpha_factory_v1/demos/alpha_agi_business_v1/examples'
SCRIPT = EXAMPLE_DIR / 'find_best_alpha.py'
DATA_FILE = EXAMPLE_DIR / 'alpha_opportunities.json'

class TestFindBestAlpha(unittest.TestCase):
    def test_output_highest_score(self) -> None:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        best = max(data, key=lambda x: x.get('score', 0))
        result = subprocess.check_output([sys.executable, str(SCRIPT)], text=True)
        self.assertIn(best['alpha'], result)
        self.assertIn(str(best['score']), result)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
