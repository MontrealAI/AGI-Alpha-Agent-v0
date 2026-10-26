# SPDX-License-Identifier: Apache-2.0
"""Replay the exact 47 shared candidate checks recorded before confirmation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest

EXCLUDED = {
    "test_griffe_broader_alerts_are_retained",
    "test_exact_content_reuse_and_mutation_isolation",
    "test_changed_source_invalidates_reuse",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path[:0] = [str(root / "src"), str(root / "tests")]
    import dossier
    import test_conventional

    test_conventional.compare_sources = lambda before, after, module, **kwargs: dossier.compare_sources(before, after, module)
    names = unittest.defaultTestLoader.getTestCaseNames(test_conventional.ConventionalDevelopmentTests)
    if len(names) != 50 or not EXCLUDED <= set(names):
        raise ValueError("FROZEN_TEST_SELECTION_CHANGED")
    selected = [name for name in names if name not in EXCLUDED]
    suite = unittest.TestSuite(test_conventional.ConventionalDevelopmentTests(name) for name in selected)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"schema": "value-compounds-candidate-crosscheck/v1", "tests_run": result.testsRun,
                      "failures": len(result.failures), "errors": len(result.errors),
                      "success": result.wasSuccessful(), "excluded_comparator_only_tests": sorted(EXCLUDED),
                      "seeded_signature_pairs_in_one_test": 150,
                      "role": "Replay of development validation; no new missions or confirmation cases"}))
    raise SystemExit(0 if result.wasSuccessful() and result.testsRun == 47 else 1)


if __name__ == "__main__":
    main()
