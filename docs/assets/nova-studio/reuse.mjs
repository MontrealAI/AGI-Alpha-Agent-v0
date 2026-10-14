// SPDX-License-Identifier: Apache-2.0
import {canonical,digest} from '../successor/engine.mjs?nova-cycle=38c4f38978bf9fc29f207bae3adee0755bc6530d04502a36c491cc430787e488';
import {address} from '../ascension-wallet/protocol.mjs';
import {hashBytes,strictJSON,deploymentIdentityStatus} from './package.mjs';
import {validateProject,registerAsset,verifyReuseRights,deploymentAddress} from './cycle.mjs';
import {verifyRuntimeResult} from './runtime.mjs';

const encoder = new TextEncoder(), selections = new WeakMap();
const copy = value => strictJSON(JSON.stringify(value));
const same = (a,b) => canonical(a) === canonical(b);
function exact(value,keys,label) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join() !== [...keys].sort().join()) throw Error(`Invalid ${label} fields.`);
}
function text(value,label,maximum = 4000) {
  if (typeof value !== 'string' || !value.trim() || encoder.encode(value).length > maximum)
    throw Error(`Provide ${label} within ${maximum} UTF-8 bytes.`);
  return value;
}
function numericalInput(input) {
  exact(input,['coefficients','lower','upper','steps','tolerancePpm'],'numerical source input');
  if (!Array.isArray(input.coefficients) || !input.coefficients.length || input.coefficients.length > 7 ||
      input.coefficients.some(value => !Number.isSafeInteger(value) || value < -1000 || value > 1000))
    throw Error('Use 1–7 bounded integer polynomial coefficients.');
  if (!Number.isSafeInteger(input.lower) || input.lower < -100 || input.lower > 99 ||
      !Number.isSafeInteger(input.upper) || input.upper <= input.lower || input.upper > 100 ||
      !Number.isSafeInteger(input.steps) || input.steps < 2 || input.steps > 1000 || input.steps%2 ||
      !Number.isSafeInteger(input.tolerancePpm) || input.tolerancePpm < 0 || input.tolerancePpm > 1000000)
    throw Error('Numerical bounds, even steps or absolute tolerance differ from the supported adapter.');
  return copy(input);
}
function absoluteTolerance(ppm) {
  let numerator = BigInt(ppm), denominator = 1000000n, a = numerator, b = denominator;
  while (b) [a,b] = [b,a%b];
  numerator /= a; denominator /= a;
  return `${numerator}/${denominator}`;
}
async function checkedSource(project,cycleId,artifactName,verifyCurrent) {
  if (typeof verifyCurrent !== 'function') throw Error('Refresh the signed result and finalized accepted settlement before selecting reuse.');
  if (artifactName !== 'calculation-input.json') throw Error('This adapter reuses the exact calculation-input.json numerical recipe.');
  const cycle = project.cycles.find(item => item.cycleId === cycleId);
  if (!cycle?.package || !cycle.seedId) throw Error('Recover the source cycle’s original package and seed first.');
  // This callback belongs to the existing workflow: recheck the pinned signer,
  // assignment, canonical/finalized receipt, accepted state and exact payouts.
  const current = await verifyCurrent();
  if (!current?.request || !current.result || !current.settlement || !current.observerKey || !current.profile)
    throw Error('The current verification did not return its exact request, result, settlement, deployment profile and pinned source.');
  const deploymentIdentity = deploymentIdentityStatus(cycle.package,current.profile);
  const {request,result,settlement,observerKey} = current;
  if (request.project_id !== project.projectId || request.cycle_id !== cycleId ||
      !same(request.plan,cycle.package.plan) ||
      !cycle.missions.some(mission => same(mission.request,request))) throw Error('Reuse source is not the original registered mission.');
  const checked = await verifyRuntimeResult(request,result,observerKey), binding = checked.binding;
  const deployment = cycle.package.deployment, context = binding.market_context;
  if (String(context.chain_id) !== String(deployment.chainId) || address(context.market) !== deploymentAddress(deployment,'Jobs') ||
      address(context.seed) !== deploymentAddress(deployment,'Seed') || String(context.seed_id) !== cycle.seedId ||
      settlement.job_acceptance !== 'accepted' || settlement.settlement_status !== 'paid' ||
      settlement.execution_binding_digest !== result.execution_binding.digest || settlement.delivery_digest !== result.delivery.digest ||
      settlement.candidate_verdict !== result.candidate_verdict || settlement.authority_status !== 'not_granted' ||
      String(settlement.chain?.chain) !== String(deployment.chainId) ||
      address(settlement.chain?.market) !== deploymentAddress(deployment,'Jobs') ||
      String(settlement.chain?.job) !== String(binding.market_job_id))
    throw Error('Reuse requires this exact execution’s accepted finalized settlement and source deployment.');
  const report = checked.artifact.report;
  if (report?.spec?.family !== 'numerical' || request.work_spec.family !== 'numerical' || !same(report.spec,request.work_spec))
    throw Error('Only the verified fixed numerical adapter can supply this reusable recipe.');
  const {integrityDigest,...body} = report;
  if (integrityDigest !== await digest('workbench-pack',body)) throw Error('The retained workbench report was altered.');
  if (!Array.isArray(report.result?.artifacts) || report.result.artifacts.length > 12) throw Error('Invalid result artifact list.');
  const matches = report.result.artifacts.filter(item => item.name === artifactName);
  if (matches.length !== 1) throw Error('Select one unambiguous original calculation-input artifact.');
  const artifact = matches[0];
  exact(artifact,['name','type','content','digest'],'selected artifact');
  if (artifact.type !== 'application/json' || typeof artifact.content !== 'string' || encoder.encode(artifact.content).length > 200000)
    throw Error('Selected recipe must be bounded exact JSON bytes.');
  const {digest:artifactDigest,...original} = artifact;
  if (artifactDigest !== await digest('workbench-artifact',original)) throw Error('Selected artifact digest differs from its original bytes.');
  const sourceBytes = encoder.encode(artifact.content), inputs = numericalInput(strictJSON(artifact.content,200000));
  if (!same(inputs,report.spec.inputs) || report.result.evidence?.absoluteTolerance !== absoluteTolerance(inputs.tolerancePpm))
    throw Error('Selected recipe differs from the executed inputs or exact absolute tolerance.');
  return {request,result,settlement,observerKey,deploymentIdentity,report,artifact,sourceBytes,inputs,sha256:await hashBytes(sourceBytes)};
}

/** Explicit local rights review; payment and candidate verdict confer no reuse or execution authority. */
export async function authorizeArtifactReuse(project,cycleId,{artifactName = 'calculation-input.json',review,verifyCurrent,now = Date.now()}) {
  const checkedProject = await validateProject(project), source = await checkedSource(checkedProject,cycleId,artifactName,verifyCurrent);
  exact(review,['reviewer','rationale','license','validUntil'],'local rights review');
  text(review.reviewer,'the reviewing operator',160); text(review.rationale,'the source/rights review rationale');
  text(review.license,'the exact declared source license',1000);
  if (review.license !== source.report.spec.rights.license) throw Error('Reuse must preserve the verified source’s exact declared license.');
  if (new Date(review.validUntil).toISOString() !== review.validUntil || Date.parse(review.validUntil) <= now ||
      Date.parse(review.validUntil)-now > 86400000)
    throw Error('Use a rights review expiry within the next 24 hours.');
  const declaration = {schema:'agialpha.nova-studio.local-rights-review.v1',projectId:project.projectId,cycleId,
    artifactName,artifactSha256:source.sha256,sourceResultSha256:source.result.artifact_sha256,
    sourceJob:copy(source.settlement.chain),declaredSource:copy(source.report.spec.rights),...copy(review),
    scope:'Explicit local operator attestation; no independent license audit or candidate adoption.'};
  const rightsEvidence = await hashBytes(encoder.encode(canonical(declaration)));
  const asset = {assetId:`numerical-recipe-${source.sha256.slice(2,18)}-${rightsEvidence.slice(2,18)}`,digest:source.sha256,
    kind:'numerical-calculation-input',source:canonical(declaration),license:review.license,permittedUses:['successor-input'],
    rightsEvidence,review:{decision:'accepted',reviewer:review.reviewer,evidenceDigest:rightsEvidence},validUntil:review.validUntil,
    revoked:false,scope:'Reuse the fixed recipe’s steps, absolute tolerance and integration bounds with fresh coefficients. No candidate adoption or operational authority.'};
  const cycle = checkedProject.cycles.find(item => item.cycleId === cycleId), existing = cycle.assets.find(item => item.assetId === asset.assetId);
  let next = checkedProject;
  if (existing) {
    if (!same(existing,asset)) throw Error('The existing artifact review differs from this exact local declaration.');
  } else next = await registerAsset(checkedProject,cycleId,asset);
  const token = await verifyReuseRights(next,cycleId,asset.assetId,async()=>({valid:true,digest:asset.digest,rightsEvidence,
    licenseCompatible:true,source:'Fresh workflow result/settlement verification and explicit local operator rights declaration.'}),{now});
  const selection = Object.freeze({assetId:asset.assetId,sourceProjectId:project.projectId,sourceCycleId:cycleId,
    deploymentIdentity:source.deploymentIdentity,
    artifactName,artifactSha256:source.sha256,sourceResultSha256:source.result.artifact_sha256,license:review.license,
    inherited:Object.freeze({steps:source.inputs.steps,absoluteTolerance:absoluteTolerance(source.inputs.tolerancePpm),
      tolerancePpm:source.inputs.tolerancePpm,lower:source.inputs.lower,upper:source.inputs.upper}),
    scope:'fixed-numerical-recipe; no candidate adoption',validUntil:review.validUntil});
  selections.set(selection,{projectId:project.projectId,cycleId,inputs:copy(source.inputs),assetId:asset.assetId,
    license:asset.license,reviewUntil:Date.parse(review.validUntil),verifiedAt:now});
  return {project:next,asset,token,sourceBytes:source.sourceBytes.slice(),selection,deploymentIdentity:source.deploymentIdentity};
}

/** Return the exact new work spec with inherited inputs reconstructed from the reviewed source bytes. */
export function assertNumericalReuse(selection,nextWorkSpec,{projectId,cycleId,now = Date.now()} = {}) {
  const known = selections.get(selection);
  if (!known || known.projectId !== projectId || typeof cycleId !== 'string' || cycleId === known.cycleId ||
      now < known.verifiedAt || now-known.verifiedAt > 300000 || now >= known.reviewUntil)
    throw Error('Refresh the original artifact and local rights review; imported selections grant no reuse authority.');
  if (nextWorkSpec?.schema !== 'successor-workbench/v1' || nextWorkSpec.family !== 'numerical' ||
      nextWorkSpec.rights?.license !== known.license) throw Error('Reuse requires the same fixed adapter and declared source license.');
  const input = numericalInput(nextWorkSpec.inputs);
  for (const key of ['steps','tolerancePpm','lower','upper']) if (input[key] !== known.inputs[key])
    throw Error(`Inherited ${key} must match the selected calculation-input.json bytes.`);
  if (same(input.coefficients,known.inputs.coefficients)) throw Error('The successor must use distinct polynomial coefficients, not renamed or cached work.');
  return {...copy(nextWorkSpec),inputs:{...copy(known.inputs),coefficients:[...input.coefficients]}};
}
