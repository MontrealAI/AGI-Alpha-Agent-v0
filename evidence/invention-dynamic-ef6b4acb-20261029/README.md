# Exact ef6b4acb qualification evidence

This archive records **partial qualification with an observed reader failure** for source commit `ef6b4acb26089888c6951467187c17286884d44f` (tree `d273a3aa0f36139060c90c825666c17933303df7`). It does not qualify the archival commit as a new software head.

[Actions run 40911121082](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40911121082) completed with green jobs. The real Docker controls and retained native acceptance passed. The anonymous browser capture **did not render the PDF**: visual inspection shows GitHub's “Unable to render code block” message. Capture exit status alone does not prove rendering. [Inspect the original failed PNG](anonymous-inline-not-rendered.png).

The legacy constructor's source-admission path remained blocked at this head pending a separately identified P2 repair. This run's exposed retained-AST and Docker-mechanics results do not establish acceptance of every construction path, source-claim truth, scientific confirmation, deployment suitability, or business value.

## Actual dynamic results

All seven controls actually executed through the native `specification_run.isolated` / `secure_run` Docker boundary:

1. A valid generated AST executed seven records (55 operations); the separate read-only output oracle passed it.
2. An invalid unconditional-accept AST executed successfully; its actual wrong outputs were rejected by the separate oracle.
3. Sixteen permission/network/execution checks passed, including nonroot execution, dropped capabilities, seccomp, no-new-privileges, denied root/input writes and privilege escalation, no host mounts or Docker socket, external network denial, and scratch noexec.
4. Scratch exhaustion stopped at 16,777,216 bytes and PID exhaustion at 63 started threads.
5. Verifier-state and oracle-source tampering attempts were denied; host hashes remained unchanged.
6. Excessive output triggered the 1,048,576-byte combined-output limit and container cleanup.
7. The real timeout raised `SandboxTimeout` after 120.088579497 seconds and container cleanup.

Observed cgroups: CPU quota `200000 100000` (two CPUs), memory 2,147,483,648 bytes, PIDs 64. Scratch is 16 MiB; wall limit is 120 seconds. CPU/memory saturation or OOM was not induced. In-container Python execution is allowed; this is not an all-exec-denial or universal escape-proof claim.

Docker server: 28.0.4. Image: `python@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159`. Image ID: `sha256:ae4e8b7c575fabea88a029b6cae757f342ca2525e07f7c22272d5105c346b35e`.

The retained proposal additionally passed frozen admission, actual native Docker execution, and canonical final `ACCEPTED` verification. Its actual unconditional-accept negative was rejected by the semantic oracle and native final verifier. The native negative verdict specifically rejected missing static dimensional dominance; that verdict's `candidate_executed=false` describes its static rejection route, while the separate negative execution receipt records the actual successful Docker run. Receipts trust the local orchestrator rather than cryptographic attestation.

All 12 dynamic source identities, all 19 native frozen paths, and the native DRIVER literal were independently read back from the exact source commit and hash-checked, including the actual canonical verifier, helper, read-only boundary, initializer, driver, tests, workflow and protocol v5. The workflow also passed all 11 receipt-double unit tests; those unit tests are plumbing checks, not generated execution.

## Anonymous paper readback and failure

The immutable paper commit is `3544aa804b26364236dcac3a585f29c45498e73d`. Anonymous HTTP returned both the GitHub blob page and exact PDF bytes: 622,931 bytes, SHA256 `8142fe2452162901cda732f7a8070572a033ed4f0cfe269c514e40e19b60457f`.

A fresh Chrome 156.0.8078.47 profile, without credential or cookie import, captured the public blob page. The 1440 × 1100 image visibly shows “Sign in” / “Sign up” and **“Unable to render code block”**, with no PDF page. Its original SHA256 is `9724241e604b89f868595f04631a6d97d909ad19388b3c42efcb0d7875a9f0aa` (136,709 bytes). HTTP retrieval passed; inline rendering did not.

## Preserved originals and durability

- `dynamic-artifact.zip`: original artifact 12914921061, 20,338 bytes, SHA256 `ff1c35ff22e732fba216679a0ccb605565dc52a53026b87174eba97fa6471fdd`; Actions expiry 2026-11-28T16:30:04Z.
- `public-reader.zip`: original artifact 12914886740, 114,585 bytes, SHA256 `3eda151c934d23d93066e00058f0aaecb267e1a3afd0422b98221f2ce82bb3e3`; Actions expiry 2026-11-28T16:37:30Z.
- `anonymous-inline-not-rendered.png`: byte-identical copy of the original PNG inside `public-reader.zip` for direct inspection.
- `qualification-receipt.json` and `SOURCE_BINDINGS.json`: outcome, limits, member hashes and exact source bindings.

The Git evidence commit preserves these bytes independently of Actions artifact expiry. Both original archives (24 + 4 members), their text/JSON contents and the PNG were inspected. No secrets or private task paths were found. Original generic GitHub-runner paths are preserved as runner provenance, not local workstation paths. No opaque or signed download/viewer URLs are included in these public records. Verifier independence is procedural on shared hosts/libraries/authorship; no external certification, confirmation, or commercial claim is made.
