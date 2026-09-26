[See project notice](DISCLAIMER_SNIPPET.md)

# Live badges and verification

The README's five CI badges report actual GitHub checks for `main`. A green CI badge means
the selected check passed. Pending, unavailable and failed results must remain visible.
The release badge follows the latest stable published release; it is independent of later
documentation changes on `main`.

| Badge | What it reports | Evidence |
| --- | --- | --- |
| PR CI | Latest push to main: Ruff and focused smoke tests | [PR CI runs](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/pr-ci.yml?query=branch%3Amain+event%3Apush) |
| Integration CI | Current main commit: every required validation job, including Python and browser tests, docs and Docker | [Integration runs](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/ci.yml?query=branch%3Amain) |
| Smoke Test | Current main commit: all nine Linux, macOS and Windows / Python 3.11–3.13 runs | [Smoke runs](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/smoke.yml?query=branch%3Amain) |
| CI Health | The `CI watchdog` check runs attached to the current main commit | [Watchdog runs](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/ci-health.yml?query=branch%3Amain) |
| Release acceptance | Latest push to main: bounded runtime, real inference, browser, contract, recovery, preservation and packaging checks | [Acceptance runs](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/agent-release.yml?query=branch%3Amain+event%3Apush) |
| Release | Latest published stable version | [Release assets, checksums and evidence](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/latest) |

PR CI and acceptance use GitHub's branch and push-event selectors.
Health, Smoke and Integration use Shields' live check-runs endpoint with the exact `CI watchdog`,
`Smoke matrix` and `Integration matrix` names and main branch. The matrix results run even after
a failure and reject failure, cancellation or skipped required jobs. Integration includes every
validation job and all its matrix variants; tag-only deployment is outside this main-branch check.
None of these badges sets a status color or manufactures a passing
result. They read check records directly instead of relying on workflow badge images that served
stale results during the 1.3.0 release. Health also watches PRs; these watchdog jobs execute on the default branch even
when their evaluated source branch is a PR. A watchdog failure can therefore indicate a PR
requiring attention, not just a broken main build.

Health runs from distinct events, upstream workflows and source branches use separate concurrency
groups. An unrelated PR check can no longer cancel an active scheduled/main health check.
The watchdog retains its existing rerun, missing-run detection and branch-protection checks.
It requires the intended upstream commit (or current scheduled-run commit), checks the returned SHA
and branch, and rejects stale results. A pending run is never a pass, including when a grace or waiting
period expires. Automatic reruns do not extend the bounded wait indefinitely. Remediation rechecks the current
branch commit before acting, and each run permits at most one automatic retry. An event known to be
superseded is left read-only so it cannot restart an older workflow and cancel the current build.
Branch-protection verification requires the configured admin token; its absence is reported as
a warning, not evidence that repository protection has been verified.

## If an image disagrees with a run

1. Open the badge and check the branch, event, commit and newest run attempt.
2. Inspect cancelled and pending jobs as well as failures. Diagnose the cause before retrying.
3. Compare the workflow page with the commit's checks. Badge providers and GitHub's image proxy
   can cache results, so an image can lag a completed run.
4. Allow the image cache to refresh. Do not turn a status green by hard-coding its result,
   forcing its color, choosing an old passing commit, deleting failures or disabling a check.

The Business and Marketplace demo badges now link to repository integration checks and identify
their research scope. The Marketplace's former static “100% coverage” badge links to the
[validation report](agent/VALIDATION.md) instead of claiming an unmeasured percentage.
These are repository-level checks; they do not certify a demo as production-ready.
License and launch badges are informational links and are not test results.

See [capability boundaries](agent/CAPABILITIES.md) and the versioned validation archive in each
release for tested behavior, skips and expected failures. Badges are a navigation aid; the
commit-specific evidence is the basis for assessing a release.
