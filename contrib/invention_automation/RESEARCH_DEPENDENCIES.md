# Research dependencies and installed verification

The canonical verifiers are installed within
`alpha_factory_v1.core.runtime.invention_verification`. This sibling package
contains only the separate critic, static helper, read-only restriction and
dynamic output oracle. Its initializer imports no candidate implementation.
The verifiers use Python's standard library and the existing Linux libseccomp
runtime; they do not need an installed `contrib` namespace or optional research
libraries. Missing Linux restrictions, source drift or an incomplete freeze fail
closed. Native verification and freezes bind these actual installed modules.
Native verifier subprocesses also disable unsafe working-directory insertion
and `site` initialization (`-P -S`), preventing implicit editable or `.pth`
startup hooks from supplying a missing verifier. Their explicit `PYTHONPATH`
contains only the frozen source/install root. No candidate dependency is loaded
to bootstrap a verifier.

The old `contrib.invention_automation` verifier imports remain compatibility
forwarders for research-source users. Their bytes cannot substitute for the
installed verifier, helper, initializer or read-only implementation in a freeze.
Archived source snapshots and their historical pins remain original evidence;
they are not a new qualified run after relocation.

Research-only paths additionally use these optional libraries:

| Research component | Library range used by the recovered source |
| --- | --- |
| Compounding discovery and meta discovery | `scipy>=1.17,<1.18` |
| Flood readiness and meter data analysis | `pandas>=2.2,<4` |
| Symbolic claim probes | `sympy>=1.13,<1.15` |

Use an explicitly recorded research environment when reproducing those paths.
These ranges document recovered requirements; they are not a new locked runtime
profile, a dependency installation, or a guarantee that every version passes.
The existing project's package discovery, dependency metadata and release locks
remain unchanged. No new extras or `contrib` package finder are required for
the installed verifier.

Run the native verifier with its actual module name, for example:

```sh
python -B -m alpha_factory_v1.core.runtime.invention_verification.critic_verify --help
```

Dynamic software qualification remains a separate real-Docker test. Packaging
and static verifier smoke checks execute no generated candidate program and
cannot inherit an earlier exact-head Docker PASS onto changed source.
