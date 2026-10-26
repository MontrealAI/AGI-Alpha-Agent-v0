// SPDX-License-Identifier: Apache-2.0
import {createWorkbench} from '../../../../examples/successor-workbench/engine.mjs';
import {assessReuse, createSelector} from './bridge.mjs';

export function createAdmittedWorkbench({adapter, admission, foundations, artifactRoot, requiredSkills,
  strategy = 'registry', context = {now: 150}}) {
  admission = structuredClone(admission);
  context = structuredClone(context);
  for (const key of Object.keys(context)) {
    if (!['now', 'currentSnapshotId', 'revokedSkills', 'supersededSkills', 'revokedRoots',
      'expectedGraphRoot', 'expectedEpoch', 'expectedAdmissionDigest'].includes(key)) throw Error('REUSE_CONTEXT_FIELD');
  }
  const expected = {expectedGraphRoot: admission.root.graphRoot, expectedEpoch: admission.root.epoch,
    expectedAdmissionDigest: admission.admissionDigest};
  const select = createSelector(admission, foundations, strategy);
  const selected = select(requiredSkills);
  const guarded = {manifest: adapter.manifest, validate: input => adapter.validate(input),
    async execute(input, checkpoint) {
      await checkpoint('checking-fixture-admission');
      const checked = await assessReuse({admission, foundations, artifactRoot, ...expected, ...context});
      if (!checked.ok) throw Error('CURRENT_FIXTURE_ADMISSION_REFUSED');
      const result = await adapter.execute(input, checkpoint, selected);
      return {...result, evidence: {...result.evidence, skillAdmission: {
        mode: 'FIXTURE_ONLY', liveIdentityEnforcement: 'NOT_RUN', cryptographicAuthentication: false,
        admissionDigest: admission.admissionDigest, graphRoot: admission.root.graphRoot,
        selection: selected, executionAuthority: [], settlement: 'NOT_CONNECTED'}},
      limits: [...result.limits, 'Skill admission uses labeled authority fixtures; live ENS enforcement was not run.']};
    }};
  return createWorkbench([guarded]);
}
