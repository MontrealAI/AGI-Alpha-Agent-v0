# SPDX-License-Identifier: Apache-2.0
"""Static policy regression: supersede PR heads, never collapse other events."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PullRequestConcurrencyTests(unittest.TestCase):
    def test_pr_only_suffix_expression_and_cancellation(self) -> None:
        source = (ROOT / ".github/workflows/pr-ci.yml").read_text(encoding="utf-8")
        block = source.split("\nconcurrency:\n", 1)[1].split("\ndefaults:\n", 1)[0]
        expression = (
            "${{ github.workflow }}-${{ github.ref }}-"
            "${{ github.event_name == 'pull_request' && 'latest-pr' || github.sha }}"
        )
        self.assertEqual(re.findall(r"^  group: (.+)$", block, re.M), [expression])
        self.assertEqual(re.findall(r"^  cancel-in-progress: (.+)$", block, re.M), ["true"])

    def test_group_policy_keeps_event_and_ref_boundaries(self) -> None:
        # The exact expression is checked above. These examples document its
        # truth table; they are not a replacement for GitHub expression parsing.
        def group(event: str, ref: str, sha: str, workflow: str = "PR CI") -> str:
            suffix = "latest-pr" if event == "pull_request" else sha
            return f"{workflow}-{ref}-{suffix}"

        self.assertEqual(
            group("pull_request", "refs/pull/7/merge", "a"), group("pull_request", "refs/pull/7/merge", "b")
        )
        self.assertNotEqual(
            group("pull_request", "refs/pull/7/merge", "a"), group("pull_request", "refs/pull/8/merge", "a")
        )
        for event in ("push", "workflow_dispatch", "merge_group", "release"):
            with self.subTest(event=event):
                self.assertNotEqual(group(event, "refs/heads/main", "a"), group(event, "refs/heads/main", "b"))
                self.assertEqual(group(event, "refs/heads/main", "a"), "PR CI-refs/heads/main-a")


if __name__ == "__main__":
    unittest.main()
