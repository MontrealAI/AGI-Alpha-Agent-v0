# Foundational architecture and identity audit

Audit date: 2026-10-26. Read-only investigation for the additive AGI ALPHA validated skills graph study. No wallet, signing request, credential creation, contract change, or transaction was performed. Live identity enforcement and exact deployed-byte comparison: **NOT RUN**.

## Verified paper identities

Both original PDFs were downloaded without modification. Their Git blob identities match the inspected repository inventory at `MontrealAI/goalos-agialpha-sovereign-machine-economy`, commit `1e9a5675b1662e98074fb1c71cf2c5b94c7d259f`, Git tree `6d8be1d70c6cd93015a7016a56bd82e3f1f2185c`. Printed page numbers exclude the cover, so PDF page number is printed page plus one.

| Paper | Bytes | SHA-256 | Git blob |
|---|---:|---|---|
| Merkle Roots for the Validated Skill Graph v114 | 508,050 | `3276b66b3aa84d1fadc51d2a398579a8b3108294fafea1a5e239e70dd0fed7de` | `57d9afe3292804ae4b5d604709226e5218e8d329` |
| PROOF LOOPS v2 author edition | 240,928 | `2c41599a893c4c5ac0eacdf9b4416f4420b3d47ee73c04ed868049b29a6055db` | `6997377486a1e41bfda8d07221a091f9e828223e` |

The local originals are `merkle.pdf` and `proof_loops.pdf`; full extracted text is retained. Selected pages were rendered and visually inspected to confirm the authority and reuse requirements.

## Architectural requirements actually stated

| Source | Location | Requirement relevant to this experiment |
|---|---|---|
| PROOF LOOPS | Sections 6-10, printed pp. 4-5 | Mission criteria and claim boundaries precede work; the dossier binds claim support, evidence, risks, replay, validator notes and rollback. Admission is a policy decision. |
| PROOF LOOPS | Section 11, printed p. 5 | A skill is scoped, evidenced, replayable, versioned and rollbackable; edges carry policy scope. |
| PROOF LOOPS | Section 12, printed p. 5 | Proof level is selected before work. A local demonstration must not be relabeled external review or durable institutional authority. |
| PROOF LOOPS | Section 14, printed p. 7 | Future influence requires admission, scope match, freshness and absence of a blocking condition. Failure creates repair work. |
| PROOF LOOPS | Sections 16-18, printed p. 9 | Evaluate useful effects on future work; graph size is not evidence of improvement. Baselines, complete costs and independent reproduction are required for stronger empirical claims. |
| Merkle Roots | Sections 1 and 5, printed pp. 2-3 and 5 | Capability, evidence, commitment and authority are distinct. Inclusion commits to bytes, not truth or permission to reuse. |
| Merkle Roots | Sections 6 and 9, printed pp. 6-7 and 10 | Explicit canonicalization, typed domains, schema identity, empty and odd-leaf rules; typed class roots; previous-root-bound graph epoch. |
| Merkle Roots | Sections 10-11, printed p. 11 | Candidate/rejected leaves cannot gain future influence from a root. Show inclusion, tamper failure and root comparisons. |
| Merkle Roots | Section 12, printed p. 12 | Root writing is restricted to the current controller, wrapped owner, approved operator or registry-approved delegate of a direct `label.agent.agi.eth` node. Deeper names do not inherit root-writing authority. |
| Merkle Roots | Sections 15-17, printed pp. 13-15 | Bind expected root, epoch, previous root, policy, schema and evidence; preserve revocation/supersession history; test unauthorized writes, replay, stale roots and serialization drift. |
| Merkle Roots | Sections 18-23, printed pp. 15-18 | M0-M9 are distinct conformance levels. V107 is described as an implementation surface. The paper explicitly does not claim a deployed mainnet registry or completed security audit. |
| Merkle Roots | Appendix D, printed p. 20 | Cross-implementation vectors; typed inclusion for every class; rejection of nested-name inheritance; revocation blocks future influence; inclusion is not authority. |

The new exclusive agent attestation policy is an additional policy from the current assignment. It must not be attributed to the Merkle paper's root-writer rule. Neither paper changes existing Jobs validator roles.

## Observed implementation and operating status

The inspected complete source inventory has no separately tracked Solidity source or named V107 graph-epoch registry. The actual `src/goalos_ascension/kernel.py` is a local reference loop. Its proof bundle contains the literal `local-reference-signature`; its minimum gate checks artifact structure, and it emits simulated settlement and a candidate capability. That surface cannot be treated as live ENS authentication or proof of economic return. The Chronicle Lab documentation describes an architectural public-alpha interface.

The repository also contains a **different, historical mainnet contract atlas** (`content/goalos/mainnet-contracts-v4.4.0.json`). It records 48 GoalOS-created contracts plus an external canonical token from `MontrealAI/goalos-agialpha-ascension`, tag `v4.4.0-mainnet-2026-06-21`. It contains `AEPAttestationRegistry`, `AEPChronicleRegistry` and `AGIEthNamespaceRegistry`, but no VSG/Merkle graph-epoch registry entry. This audit does not erase or deny those recorded deployments.

Read-only inspection of the atlas's source tag, resolving to `51bacf4fe58e4eb425240e74eef7e8461832767f`, found:

- `AEPAttestationRegistry.attest` and revocation use `onlyOperator`.
- `AEPChronicleRegistry.recordEntry` preserves a previous-entry hash and uses `onlyOperator`.
- `AGIEthNamespaceRegistry` records namespace/policy hashes through `onlyOperator`; that is not a proof of ENS control by an attesting signer.
- `GoalOSAccessControl.onlyOperator` accepts `DEFAULT_ADMIN_ROLE` or `OPERATOR_ROLE`. It contains no exclusive `*.agent.agi.eth` attestation predicate.

Source inspection is distinct from exact deployed-byte identity and current state. The latter were not verified here. Existing contracts remain untouched; the graph study must use its own explicitly bounded fixture adapter until a supported live authorization verifier is available.

## Proposed policy for the additive research layer

Use two independent operation names, `ISSUE_SKILL_ATTESTATION` and `COMMIT_GRAPH_ROOT`. A valid identity is necessary for both but is not itself a permission grant. A policy-approved attester grant must not authorize root writing, and a root-writer grant must not authorize attestation. Existing Jobs evidence can be referenced in a dossier but is never an admission credential.

For the research version, explicitly allow only a direct normalized ASCII single label under `agent.agi.eth`; reject every other name and deeper subname. This is a declared conservative supported subset, not a complete ENSIP-15 implementation. A future broader policy must normalize using ENSIP-15 and independently verify authority for the exact deeper node, rather than inherit authority from string suffixes.

An authority snapshot should bind chain, registry address/version/code identity, exact node, block number/hash, observed time, controller, wrapper status, wrapped owner, active full-control operators, explicit policy-scoped delegates, expiry and revocation state. Unrecognized ENSv2 or offchain/L2 authority models must fail closed until their own adapter is qualified. Do not use an address resolution record or reverse name as ownership proof.

For ENSv1, an unwrapped exact-node owner/controller or the corresponding registry `isApprovedForAll` operator may satisfy the ownership part of policy. If the registry owner is NameWrapper, verify the exact node through the wrapper and its current wrapped owner/full-control approval. A NameWrapper per-name `approve`/`getApproved` value is **only a subname renewal manager**, not general control and not attestation/root authority. A registry- or policy-approved delegation must name the exact operation, node, scope, validity interval and delegator authority epoch; transfer or revocation invalidates current use under this conservative policy.

Bind an attestation to the exact skill/version/implementation/dependencies, evidence dossier digest, tested scope, execution environment, validation policy/schema, graph namespace, authorization snapshot, issue time, validity interval, signer and unique nonce. Bind signatures to a typed operation domain and chain/registry context. A nonce should prevent repeated state-changing admission or conflicting duplicate use; it should not prohibit legitimate read-only reuse of the same admitted attestation. Signature validity, identity authority, technical admission and economic admission are separate predicates.

An append-only root packet must bind the nine typed roots, agent node, epoch, previous root, chain/registry context, policy/schema, snapshot identity, local/live mode and writer authorization snapshot. Refuse a stale expected predecessor, skipped/repeated epoch, missing admission or non-current writer authority. Revocation and supersession append records and remove current influence without modifying historical roots.

Historical validity is evaluated against the authenticated state at issuance/commit time. Current reuse additionally checks the latest policy/authority epoch, expiry, revocation, supersession, evidence availability, scope, dependency compatibility and composition evidence. A once-valid attestation remains an honest historical fact after expiration or ownership transfer but cannot be relabeled current permission.

## Signature and fixture boundary

An ENS-looking string and a caller-supplied `signature_valid=true` flag are not authentication. A production adapter needs recovered EOA signatures or ERC-1271 contract verification at the bound state, then independent authority verification. EIP-712 provides typed signing and domain separation, **not replay protection** by itself. ERC-1271 validity can depend on state and time.

A bounded research fixture can contain predetermined identity/authorization/signature verification outcomes and adversarial cases, but its type and report must say `FIXTURE_ONLY`, with `live_identity_enforcement: NOT_RUN`. It must never be accepted by the live adapter. No fixture address or signature should be represented as control of a real agent name. Alternatively, test-only public signature vectors may exercise cryptography while registry authority remains a separate fixture; report these two levels separately.

## Minimum adverse controls

Reject club identity, unrelated namespace, nested-name inheritance, signer/controller mismatch, expired wrapper state, renewal-only operator, wrong-operation delegate, revoked delegate, transfer-stale authority, unknown registry version, wrong skill/version/evidence/scope/environment/policy, altered signature, wrong chain/registry, stale epoch, repeated nonce, unauthorized root writer, tampered typed leaf/path, missing evidence, revoked skill, superseded skill and component-only composition claims. Preserve former valid history in all expiry/revocation/transfer cases.

For the economic comparison, give all arms the same skills, evidence and correctness policy. Graph structure must not receive exclusive access to freshness or identity checks and then claim their effect as topological advantage. Unsafe ablations can diagnose failures but are not sellable workflows.

## Primary external references inspected

- ENS Registry: https://docs.ens.domains/registry/ens/ (`owner`, `isApprovedForAll`).
- Name Wrapper overview: https://docs.ens.domains/wrapper/overview/ (owner/manager distinction).
- Name Wrapper contract details: https://docs.ens.domains/wrapper/contracts/ (full-control batch operators versus renewal-only per-name approval).
- Name Wrapper expiry: https://docs.ens.domains/wrapper/expiry/ (name/fuse expiry and ancestor bounds).
- ENS name processing: https://docs.ens.domains/resolution/names/ (ENSIP-15 and exact namehash).
- ENSv2 architecture: https://docs.ens.domains/ensv2/overview/ (different registry/permission model; no assumed deployment status).
- EIP-712: https://eips.ethereum.org/EIPS/eip-712 (typed messages; replay protection excluded from the standard).
- ERC-1271: https://eips.ethereum.org/EIPS/eip-1271 (contract signature verification and state-dependent validity).

All source files used for the repository conclusions and their hashes are retained in `source-manifest.json`. Official documentation was inspected online on the audit date; it is guidance for the policy design, not a live registry snapshot.
