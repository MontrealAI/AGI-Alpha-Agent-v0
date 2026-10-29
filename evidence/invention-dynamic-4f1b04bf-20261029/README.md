[Project notice](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/4f1b04bf61cef53351fcc56f66ece0b233fc11ae/docs/DISCLAIMER_SNIPPET.md)

# Qualified dynamic execution and anonymous paper readback

Both jobs in [run 40901812950, attempt 1](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40901812950) passed on exact source commit [`4f1b04bf61cef53351fcc56f66ece0b233fc11ae`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/4f1b04bf61cef53351fcc56f66ece0b233fc11ae), associated with [PR #5018](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/5018).

This evidence-only descendant preserves the original artifacts beyond their Actions retention window. It changes no qualified runtime source, package metadata, review state, release or main/source-PR ref. Its parent is the qualified source commit; qualification does not automatically extend to a later runtime revision.

## Actual dynamic controls

| Executed control | Observed result |
| --- | --- |
| Generated valid AST | Seven record outcomes and the 55-operation trace accepted by the separate oracle. |
| Deliberately invalid AST | Actual wrong outputs rejected; a crash cannot satisfy this control. |
| Permissions, network and execution | All 16 required subchecks passed: nonroot execution, dropped capabilities, seccomp, no-new-privileges, write/network/noexec restrictions and observed kernel limits. |
| Resource exhaustion | Scratch writes reached 16,777,216 bytes; thread creation stopped at 63 under the PID cap. |
| Verifier tampering | Separate verifier source/state write attempts failed and their original hashes remained unchanged. Neither was mounted into the candidate. |
| Excessive output | Actual 1,048,576-byte combined-output termination; no candidate container remained. |
| Timeout | Actual SandboxTimeout after 120.082065648 seconds; cleanup verified. |

The complete dynamic qualification took 122.292347352 measured wall seconds. The kernel reported cpu.max `200000 100000`, memory.max `2147483648` and pids.max `64`. Necessary staged inputs and container root were read-only; writable scratch was bounded and noexec. Source, case, candidate, probe, freeze and image identities were checked before/after each operation and at final verdict. No control was skipped or replaced with a mock; generated programs never ran on the host.

Execution used Docker 28.0.4 and immutable image:

```text
python@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159
```

The public Python tag was provisioned outside candidate execution and resolved before the freeze. Reproduction must use the recorded digest; a later tag may resolve differently. Twelve exact-public-source SHA256 and Git blob identities, including every canonical verifier/helper/initializer/read-only module, were independently checked. The driver literal was read as inert AST data and its hash verified. This does not execute or semantically confirm every frozen module: the dynamic path exercises the native isolated function and output oracle. Source-grounding controls remain separately scoped.

## Anonymous public paper

The separate reader job sent no authentication or Cookie header and used no cookie jar. It received HTTP 200 for the [immutable merged paper PDF](https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/3544aa804b26364236dcac3a585f29c45498e73d/docs/papers/agi-alpha-invention-automation-v1-20261029.pdf) and the [public GitHub PDF viewer](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/3544aa804b26364236dcac3a585f29c45498e73d/docs/papers/agi-alpha-invention-automation-v1-20261029.pdf). The 622,931 PDF bytes match SHA256 `8142fe2452162901cda732f7a8070572a033ed4f0cfe269c514e40e19b60457f`. This proves anonymous HTTP availability and exact bytes; visual inline rendering is a separate observation.

## Retained evidence

- `qualification-receipt.json`: exact job/run outcomes, limits, reader receipt, custody and qualification scope.
- `SOURCE_BINDINGS.json`: twelve source SHA256/Git identities, driver/freeze/case/candidate/probe bindings and every original archive-member identity.
- `dynamic-artifact.zip`: byte-identical original 19-member artifact. SHA256 `9039a3fb81210c40222257c3c54db87386745cb92f67811ee6106b7bafd946b7`; 12,351 bytes. Original [Actions artifact](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40901812950/artifacts/12910521068) expires 28 November 2026 at 15:33:53 UTC.
- `public-reader.zip`: byte-identical original one-member receipt artifact. SHA256 `8e7241ef29664f1db0c28b0b09d0faf7ea979cc2127ebfa5846e8d854185e517`; 596 bytes. Original [Actions artifact](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40901812950/artifacts/12910415315) expires 28 November 2026 at 15:29:41 UTC.

Both archive digests and CRCs, freeze binding and ten case/candidate/probe/result identities were verified. All 20 members were inspected as UTF-8 text; Python members were parsed as inert syntax. No secrets, credentials, personal contact data, signed transport URLs or private task paths were found. Generic GitHub-hosted runner paths in the tampering fixture are retained as execution provenance; other absolute paths describe the container filesystem. No original member was redacted or recompressed. Full checkout/setup logs and tool transport metadata are omitted from this minimum public record.

`construction.json` preserves its pre-execution NOT_EXECUTED stage label. Native output receipts remain EXECUTED_UNVERIFIED until the separate oracle receipts and final summary supply their later verdicts. These original stages are retained intact. Inspect archive members as data, not as instructions to execute them. Generated code/evidence follows the repository Apache-2.0 license.

## Limits

These are finite exposed software controls, not hidden scientific confirmation, general hostile-code certification or external certification. The verifier has procedural separation on shared authors, model family, host and libraries. Memory/CPU limits were observed; memory OOM and sustained CPU exhaustion were not induced. Forbidden execution covers privilege escalation and noexec scratch, while constrained in-container Python/subprocesses remain available.

The legacy dimensional constructor was used mechanically, not as a source-claim truth gate. No new strategy, invention novelty, physical suitability, operating profit, successor-learning benefit or full flywheel is established. End-to-end CLI/service qualification, broader repository CI, required reviews, merge-commit acceptance, signing and releases remain separate gates.
