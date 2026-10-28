[Project notice](../../../docs/DISCLAIMER_SNIPPET.md)

# Current prototype acceptance at enterprise boundaries

The saved authorized stage, source digest and commercial forecast did not
revalidate the actual prototype acceptance. A still-trusted current operator
could consequently choose and dispatch production after the original acceptor or
prototype controller was revoked, or after the accepted prototype record changed.
Fresh commercial/authorized transitions had the same adjacent eligibility gap.

One guard now reuses `accepted_general_origin` and binds the exact completed
prototype launch to its offering specification, current source and execution
digest. It runs before both later qualification transitions, when considering
production, and before consuming a selected production decision. A rejected
production alternative stays visible with its reason; dispatch refusal leaves
Journal history, costs, reservations and the decision unchanged. The historical
offering stage and qualification record are preserved. Separately permitted new
internal prototypes remain available; old acceptance grants no new production
eligibility. No commercial role, permit rule or independent validator is changed.

## Reproduction and result

The sixteen directed cases use existing enterprise/executor/acceptance helpers
and an actual finite local prototype. Original prototype controller, acceptor,
commercial controller and current operator are separate fixture signers. The
current caller and commercial signer remain trusted when the original support is
withdrawn, so refusals are not explained by a revoked caller.

Exact original8b2 source: **12 failed,4 passed**. Corrected source: **42 passed**,
including all16 directed cases and the26 preserved enterprise cases. The new
cases check both decision and dispatch, both later qualification transitions,
exact changed-origin refusal, unchanged Journal head/event counts and accounting,
no consumption/reservation/I/O, current-authority controls and independent new
prototype work. All original source/diagnostics remain in this packet.

```bash
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/runtime/test_flywheel_enterprise_technical_authority.py tests/runtime/test_flywheel_enterprise.py --confcutdir=tests/runtime -q
python -m mypy --config-file mypy-runtime.ini alpha_factory_v1/core/runtime/successor/flywheel_enterprise.py
python -m ruff check alpha_factory_v1/core/runtime/successor/flywheel_enterprise.py tests/runtime/test_flywheel_enterprise_technical_authority.py
```

Native strict module typing and changed-file Ruff lint/format pass. Minimal
hash-locked operator dependencies and the agent/offline preflight pass; no complete
optional-development bootstrap is claimed. The full resulting-source release,
installed/public acceptance and canary remain the parent qualification scope.
No frozen canary is executed here. Models, billing, ENS and commercial authority
are explicit fixtures; paid model calls and actual collections are zero, while
complete actual cost remains unknown. These tests establish a bounded software
correction, not a new market, profit or retained Alpha.
