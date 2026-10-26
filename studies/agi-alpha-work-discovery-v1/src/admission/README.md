# Additive fixture admission bridge

This source reuses unchanged generic authority and Merkle modules from verified-capability PR #4942,
commit `c9f2892c06e173cb0f9d5ae710cffc4a6f1fa723`. The caller supplies a trusted directory containing
the exact `src/authority.mjs`, `src/commitments.mjs` and `fixtures/authority.json`; `loadFoundations`
checks pinned SHA-256 identities before and after import. Keep that directory exclusively controlled
during loading. JSON records cannot choose executable module paths. Original modules remain verbatim.

`admitCatalogue` accepts a catalogue, artifact directory and installed evidence verifier. A catalogue
has schema `agi-alpha.work-discovery-catalogue.v1`, mode `FIXTURE_ONLY`, graphId, policy, environment,
rights, skills and edges. Each skill supplies id, decimal-string version, `fixture:` creator label,
scope, implementationFiles, evidenceFiles, compositionEvidenceFiles, dependencies and expiresAt.
Every file descriptor is `{path,sha256,bytes}`. Paths are relative, regular, bounded and without
symlink components. Dependencies refer to exact `id@version` values. Edges exactly reproduce the
dependency list as `{from,to,kind:'requires'}`. Dependencies must be acyclic.

The installed evidence callback receives `{skill,binding,files}`. It must actually inspect the
appropriate acceptance evidence and return accepted=true, validatorId, matching scopeDigest and
implementationDigest. Dependent compositions additionally require separate composition evidence
files and compositionAccepted=true. A supplied ACCEPTED string by itself is not evidence validation.

The inherited fixture attestation delegate and root delegate remain separate. The creator label is
recorded separately. No new live key, account, permission or grant is created. Fixture clock values
100/150/500 are test coordinates and not wall-clock timestamps; package provenance records real time
separately. Every output says liveIdentityEnforcement NOT_RUN and cryptographicAuthentication false.

`assessReuse` rechecks supplied bytes, exact bindings, Merkle inclusion, attestation lifetime,
current fixture identity state, revocation and supersession. It reports no execution authority.
`createSelector` gives indexed registry and graph the same complete catalogue, skills, evidence
and dependency rows. Both may index and traverse prerequisites. Selection itself does not admit
or execute a skill, or imply graph superiority. Recipient capability gaps require separate tests.

`createAdmittedWorkbench` installs a guarded adapter through the existing pure JavaScript
`createWorkbench` extension. The adapter receives the same selected skill plan in either arm.
It performs its actual computation, with existing Workbench planning, checkpoints, 60-second bound,
hashes, artifact exports and inspection. Workbench admission remains HOLD, authority empty and
settlement NOT_CONNECTED. This source does not extend native Python dispatch or clear held operations.

The bridge adds structural checks and calls a study-specific technical verifier. Neither a fixture
signature nor Merkle inclusion proves correctness, independent validation, customer demand or value.
