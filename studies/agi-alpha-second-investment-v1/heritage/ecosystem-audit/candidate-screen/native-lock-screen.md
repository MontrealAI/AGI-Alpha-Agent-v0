# Candidate screen: full pinned-dependency metadata closure

Status: screened, not selected or constructed. This is a read-only development screen, not a fresh confirmation outcome.

## Observed problem and useful outcome

The preceding dependency-decision paper explicitly limits its demonstrated runtime result to a minimal component route and requires the application's own tests before a version choice. A useful adjacent outcome is a complete, auditable statement that every active dependency constraint for a specific lock, extras selection and platform/Python environment is satisfied, or an exact list of missing/conflicting constraints. It must remain a metadata-consistency result, not whole-application compatibility, security or deployment qualification.

At Alpha commit b1d52a7d010da5e245f0cb3f54756d0153c94eec, requirements-agent.lock contains 41 exact pins. Its header records pip-compile on Python 3.12 with --extra=chain --strip-extras. pyproject.toml declares nine direct base dependencies, an optional chain dependency and Python >=3.11,<3.14. The repository's wheel directory contains only a README, so no complete local wheelhouse is present in this checkout.

## Incumbent and strongest practical alternatives

The real incumbent already verifies release wheel/lock hashes, installs hash-locked dependencies, installs the Alpha wheel without re-resolving, and runs pip check. Its release workflow repeats native dependency/runtime checks on Python 3.11, 3.12 and 3.13. The separate dependency-audit gate requires every exact locked package once and no skipped advisory results.

The strongest ordinary adoption path is pip install --dry-run --ignore-installed --report against the exact hash-locked wheel set, followed by the existing installation, pip check and application tests when installation is required. With a complete wheelhouse it can use --no-index --find-links and --only-binary=:all:. Preserve legitimate pip caches in all comparisons. pip inspect already emits installed-environment JSON metadata. packaging supplies requirement, version-specifier and marker parsing, including explicit environment overrides.

A new hand-written resolver is not justified by this screen. A thin evidence wrapper around ordinary pip could be a legitimate capability if its repeatable integration burden and savings are measured. Conventional C must receive the same adoption option.

## Construction, verification, integration and upkeep

Potential work includes capturing immutable wheel identities and their actual METADATA, binding the root wheel/pyproject and requested extras, recording complete target environment fields, retaining pip reports and errors, and producing an intelligible customer action with exact unsupported scope. If a custom edge certificate is produced, it must correctly propagate requested extras and environment markers, check Requires-Python separately, distinguish inactive constraints from missing dependencies, and check wheel/platform availability independently. Registry project JSON alone is not an exact substitute for each selected wheel's metadata.

Verification should compare results to ordinary pip's resolver/checker on the same exact wheels and declared environment. Do not use --no-deps in the resolver comparison, disable requirement constraints, or call a certificate complete after skipping unparseable metadata. Successful metadata validation must not remove the application's existing regression tests.

No engineering time, complete monetary construction price, upkeep rate or repeated customer effort saving has been measured for this candidate. Acquisition of a missing wheelhouse is a real setup cost. Maintaining a custom packaging interpretation introduces an additional burden; adopting pip minimizes it.

## Reuse and repayment hypothesis

Potential triggers are a changed dependency lock, changed requested extras, changed Python/platform target, or a changed root package requirement. A source-identical repeated request should reuse existing evidence or be a no-op, not be counted as new paid production. Current source demonstrates that these checks recur in engineering workflows; it does not establish external paid frequency or per-request customer value.

The most plausible benefit is earlier, cheaper rejection of inconsistent proposals before expensive installation or application tests, or avoiding repeated human assembly of evidence. Merely adding a metadata certificate to successful cases adds work. If eventual accepted output still requires installation and tests, earlier preflight completion is not additional eventual delivery. Baseline pip dry-run and existing caches may remove most purported saving.

## Disproof and screen decision

Reject custom construction if ordinary pip already supplies the required outcome at lower complete cost; if metadata preflight cannot remove repeated work from the accepted delivery path; if acquisition/integration costs exceed the finite available operating surplus; if cases are predominantly consistent so the extra stage does not prevent meaningful wasted work; or if any claimed payback requires unobserved demand/price increases or relaxed application acceptance.

Current decision: no complete-cost investment qualification yet. The narrow plausible next observation is a measured development comparison of the actual existing full workflow versus ordinary pip preflight adoption on existing exposed examples, including cached inputs, failed proposals, successful proposals and all evidence assembly. This screen did not perform that comparison and did not inspect new holdout outcomes. If that observation does not show a repeatable burden exceeding adoption costs, maintain the incumbent. Broader application qualification is a separate, larger outcome and cannot be claimed by this metadata-only candidate.

## Accounting and sources

The machine-readable companion records exact local source hashes and a bounded screen interval. Tool/model billing, total service CPU and human attention are unknown. Agent elapsed wall time is not a human-wage estimate. No paid action, new runtime, installation, experiment or lock modification occurred.

Primary documentation inspected:

- https://pip.pypa.io/en/stable/cli/pip_install/
- https://pip.pypa.io/en/stable/cli/pip_check/
- https://pip.pypa.io/en/stable/cli/pip_inspect/
- https://packaging.pypa.io/en/stable/markers.html

Repository evidence: scripts/install_agent.py, docs/agent/OPERATIONS.md, .github/workflows/agent-release.yml, scripts/audit_agent_dependencies.py, pyproject.toml, requirements-agent.lock, and docs/papers/the-next-upgrade.tex at the exact source pin above.
