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
        self.assertEqual(re.findall(r"^  group: (.+)$", block, re.MULTILINE), [expression])
        self.assertEqual(re.findall(r"^  cancel-in-progress: (.+)$", block, re.MULTILINE), ["true"])

    def test_replacement_pr_uses_complete_base_history_and_full_job_gates(self) -> None:
        scope = (ROOT / ".github/workflows/paper-scope.yml").read_text(encoding="utf-8")
        self.assertIn("BASE: ${{ github.event.pull_request.base.sha || github.event.before }}", scope)
        self.assertIn("HEAD: ${{ github.sha }}", scope)
        self.assertIn('--base "$BASE" --head "$HEAD"', scope)
        source = (ROOT / ".github/workflows/pr-ci.yml").read_text(encoding="utf-8")
        for job in ("lint", "smoke"):
            # Inspect the full job separately; indentation delimits sibling jobs.
            block = re.split(r"\n  [a-z][a-z-]*:", source.split(f"\n  {job}:\n", 1)[1])[0]
            self.assertIn("needs.paper-scope.outputs.mode == 'full'", block)
            self.assertIn("needs: paper-scope", block)
        self.assertEqual(source.count("mode == 'full' and full != 'success'"), 2)

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
        self.assertEqual(
            group("pull_request", "refs/pull/7/merge", "a"), group("pull_request", "refs/pull/7/merge", "a")
        )
        for event, ref in (
            ("push", "refs/heads/main"),
            ("workflow_dispatch", "refs/heads/main"),
            ("merge_group", "refs/heads/gh-readonly-queue/main/pr-7"),
            ("release", "refs/tags/v1.47.0"),
        ):
            with self.subTest(event=event, ref=ref):
                self.assertNotEqual(group(event, ref, "a"), group(event, ref, "b"))
                self.assertEqual(group(event, ref, "a"), f"PR CI-{ref}-a")


if __name__ == "__main__":
    unittest.main()
