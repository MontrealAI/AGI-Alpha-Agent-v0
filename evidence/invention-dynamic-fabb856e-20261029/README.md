# Executed invention dynamic qualification — 29 October 2026

The seven exposed software controls passed on exact source commit
[`fabb856e361fabda8ab2c4a34d0dcd375395018c`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/fabb856e361fabda8ab2c4a34d0dcd375395018c),
in [PR #5018](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/5018).
[Run 40891861055, attempt 1](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40891861055)
and job `123510519278` both completed successfully. The workflow checked out and
checked that exact PR head. This separate evidence ref preserves the result
without changing the qualified source head or extending qualification to a later
source revision.

Two actual ASTs ran through `specification_run.isolated` and the existing
`secure_run` Docker boundary. The separate output oracle ran under its own
read-only seccomp filter and actually tested candidate-write and socket denial.
No generated program was executed on the host.

| Actual control | Checked result |
| --- | --- |
| Generated valid AST | Separate oracle accepted all 7 records and the 55-operation trace. |
| Deliberately invalid AST | An actual output artifact was produced; its wrong record consequences were rejected. A crash cannot satisfy this control. |
| Permissions, network and execution | All 16 required subchecks passed, including nonroot UID/GID, dropped capabilities, seccomp, no-new-privileges, root/input write denial, denied external connection, no default route, no Docker socket and denied scratch execution. |
| Resource exhaustion | Scratch writes reached 16,777,216 bytes; thread creation stopped at 63 under the PID cap. |
| Verifier tampering | Candidate writes to separately held verifier state and source failed; original host hashes remained unchanged. Neither target was mounted into the candidate. |
| Excessive output | Actual combined-output termination enforced the 1,048,576-byte cap and left no candidate container. |
| Timeout | Actual `SandboxTimeout` occurred after 120.081356201 seconds; cleanup left no candidate container. |

The kernel reported `cpu.max = 200000 100000`, `memory.max = 2147483648` and
`pids.max = 64` inside the container. The writable scratch was a bounded noexec
tmpfs; necessary staged inputs and the container root were read-only. Source,
case, candidate, probe, freeze and image identities were checked before and
after each operation and before the final verdict. All seven controls entered
actual execution; none was skipped or substituted with a mock.

The GitHub-hosted runner used Ubuntu 24.04.5, image `ubuntu-24.04` version
`20261025.353.1`, host Python 3.12.15 and Docker 28.0.4. Candidate execution used:

```text
python@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159
```

The public `python:3.12-slim` tag was provisioned before evaluation and resolved
to this immutable digest. The harness and candidate path never pulled an image.
Reproduce this result with the recorded digest; a later tag resolution may
select different image bytes. The complete qualification took 122.219722244
measured wall seconds, including the timeout control.

## Evidence and integrity

- `qualification-receipt.json` records the exact run, observed outcomes,
  environment, scope, artifact identity and publication inspection.
- `SOURCE_BINDINGS.json` records nine source-file SHA256 and Git blob identities
  independently read at the exact public source commit, the frozen inputs and
  candidates, and all 19 original artifact-member identities.
- `artifact.zip` is the byte-identical original Actions artifact, not a rebuilt
  or sanitized replacement. It contains the freeze, protocol, generated ASTs,
  exposed cases, actual results, separate verifier receipts, contained probe
  sources, attempt ledger and summary. Download SHA256, ZIP CRC, freeze/summary
  binding and ten case/candidate/probe/result identity checks passed.

`construction.json` preserves the pre-execution constructor snapshot, including
its `NOT_EXECUTED` stage label. Actual native result receipts use
`EXECUTED_UNVERIFIED`; the separate oracle receipts and final summary carry the
later verification verdicts. These original stage records are retained intact.

Original artifact SHA256:

```text
5df68c9bfdda19228d7adc468bc222770421a4caa369d0ff01994e7239faeb48
```

The original [Actions artifact](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40891861055/artifacts/12904294518)
is 12,187 bytes and expires on **28 November 2026 at 14:32:06 UTC**. The copy in
this evidence ref retains the exact original bytes beyond that retention window.
Do not execute artifact members merely to inspect them.

All 19 members were inspected as UTF-8 text; no encrypted, opaque, symlink or
binary member was admitted. No credentials, private keys, signed download URLs,
personal contact data or private task paths were found. One contained tampering
fixture retains generic GitHub-hosted runner paths as execution provenance;
other absolute paths refer to the container filesystem. No member was redacted.
Full checkout/setup logs and tool transport metadata are omitted from this
minimum public record. Raw originals remain preserved. Generated test code and
evidence follow the repository's [Apache-2.0 license](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/fabb856e361fabda8ab2c4a34d0dcd375395018c/LICENSE).

## Qualification scope

This result qualifies the native isolated function and these finite, exposed
software controls. The legacy dimensional constructor was used mechanically;
its criticism was not admitted as a source-claim truth gate. The cases are
development controls, not hidden scientific confirmation or independent
invention episodes.

The verifier has procedural separation on shared authors, model family, host
and standard-library infrastructure. It is not external certification. Memory
and CPU limits were observed through the kernel; memory OOM and sustained CPU
exhaustion were not induced. Forbidden execution is scoped to privilege
escalation and noexec scratch; constrained in-container Python and ordinary
subprocesses remain available.

End-to-end Alpha CLI/service qualification, full repository checks, legitimate
reviews, merge-commit acceptance, releases, physical validation, profitable
operation and successor-learning benefit remain separate claims and gates.
