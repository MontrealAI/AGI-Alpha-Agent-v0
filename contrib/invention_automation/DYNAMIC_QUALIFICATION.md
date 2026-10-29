# Dynamic qualification

`python -B -m contrib.invention_automation.qualify_dynamic --output NEW_DIRECTORY`
runs the recovered constructor and the actual `specification_run.isolated` path.
It never interprets a candidate AST or generated Python on the host. A missing
Docker daemon, missing digest-pinned image, skipped control, failed control or
empty selection exits nonzero and cannot produce a dynamic PASS.

The companion workflow runs every PR, main push and merge-group event on a
standard GitHub-hosted Ubuntu runner, with read-only repository permissions and
no service credentials. It provisions the public Python image outside candidate
execution, records its resolved immutable digest, then freezes source, verifier,
protocol, input, candidate, probe and image identities before evaluation. The
mutable provisioning tag is disclosed; reruns may resolve a different digest.
To reproduce an earlier execution, provision the digest retained in its freeze.
The harness itself never pulls an image. The runtime's existing limits and
isolation implementation are unchanged.

Seven required controls execute two native ASTs and five contained fixtures:

1. An actually constructed valid AST must agree with a separately implemented
   record-outcome oracle on the complete exposed specification cohort.
2. An actually executed invalid AST must be rejected for its wrong outcomes.
3. Actual root/input write, privilege escalation, scratch execution and external
   network attempts must fail; nonroot identity, dropped capabilities, seccomp,
   no-new-privileges, denied default routing and kernel cgroup limits are read
   inside the container. The scratch directory must also be usable.
4. Bounded scratch and thread creation must hit their actual tmpfs/PID limits.
   Memory and CPU limits are observed through the kernel cgroup interface;
   memory-OOM and sustained CPU saturation are deliberately not induced.
5. Candidate attempts to overwrite separately held verifier source/state must
   fail; their host hashes must remain identical. Neither is mounted.
6. Excessive output must trigger the actual 1 MiB combined-output termination.
7. The actual 120-second native wall limit must terminate a sleeping fixture.
   Output/timeout termination must leave no candidate container behind.

The oracle runs in its own existing read-only seccomp process, imports no
candidate runtime, and actually tests candidate write/socket denial. It checks
consequences for every input, exact image identity, record coverage, trace
identities and operation bounds. It cannot modify the candidate. The exposed
cases, shared authors/model family, host and standard library provide procedural
independence, not external certification or protected scientific confirmation.

This is finite software qualification. It does not establish a general hostile
native-code boundary, blanket denial of in-container process execution, physical
suitability, invention novelty, profitability or successor-learning benefit.
Forbidden execution is scoped to privilege escalation and executable scratch.
Python and ordinary child processes inside the constrained container remain
available to the runtime. Source-preservation, repository review, full CI,
merge-commit acceptance and release gates remain separately mandatory. Adding
this workflow does not change branch protection or declare itself required by
GitHub settings; release qualification must explicitly require its exact-SHA
seven-control PASS and immutable run/artifact evidence.
