// SPDX-License-Identifier: Apache-2.0
// Convert complete, already-executed production records. No selection or market outcomes are evaluated here.

const sum = values => values.reduce((total, value) => total + value, 0);
const average = (rows, key) => rows.length ? sum(rows.map(row => row[key])) / rows.length : 0;
const finite = (value, label) => {
  if (!Number.isFinite(value) || value < 0) throw Error(`Invalid recorded ${label}`);
  return value;
};

export function normalizeExecutedCampaign({campaign, productionProtocol, acquisitionManifest,
  evidence, acceptanceSpecificationSha256}) {
  if (campaign.schema !== 'api-production-campaign/v1' || campaign.phase !== 'primary' ||
      campaign.sourceQualification !== 'PASS' || campaign.finalSourceCheck?.accepted !== true) {
    throw Error('A complete source-qualified primary campaign is required');
  }
  const armIds = ['A', 'B', 'C', 'D'];
  const expectedPairs = productionProtocol.primary_pairs;
  if (!Array.isArray(expectedPairs) || !expectedPairs.length || !Array.isArray(campaign.records) ||
      campaign.records.length !== expectedPairs.length * armIds.length) throw Error('Planned denominator must be complete');
  const arms = {}, recordGroups = {};
  for (const id of armIds) {
    const rows = campaign.records.filter(record => record.arm === id);
    const actualPairs = rows.map(row => JSON.stringify(row.pair)).sort();
    if (actualPairs.join('|') !== expectedPairs.map(pair => JSON.stringify(pair)).sort().join('|')) {
      throw Error(`Missing, duplicated or substituted planned cases for ${id}`);
    }
    for (const row of rows) {
      for (const key of ['cpuSeconds', 'wallSeconds', 'sharedAcquisitionCpuSeconds', 'sharedAcquisitionWallSeconds']) {
        finite(row[key], key);
      }
      if (typeof row.accepted !== 'boolean' || (row.status === 'INPUT_ACQUISITION_FAILED' && row.accepted)) {
        throw Error('Invalid recorded source or acceptance disposition');
      }
    }
    const blocked = rows.filter(row => row.status === 'INPUT_ACQUISITION_FAILED');
    const available = rows.filter(row => row.status !== 'INPUT_ACQUISITION_FAILED');
    recordGroups[id] = {rows, blocked, available};
    arms[id] = {
      attempts: rows.length, accepted: rows.filter(row => row.accepted).length, inputBlocked: blocked.length,
      cpuSecondsMean: average(rows, 'cpuSeconds'), wallSecondsMean: average(rows, 'wallSeconds'),
      cpuSecondsAvailableMean: average(available, 'cpuSeconds'), wallSecondsAvailableMean: average(available, 'wallSeconds'),
      cpuSecondsBlockedMean: average(blocked, 'cpuSeconds'), wallSecondsBlockedMean: average(blocked, 'wallSeconds'),
    };
  }
  const blockedPairs = recordGroups.A.blocked.map(row => JSON.stringify(row.pair)).sort().join('|');
  for (const id of armIds) {
    if (recordGroups[id].blocked.map(row => JSON.stringify(row.pair)).sort().join('|') !== blockedPairs) {
      throw Error('Paired source availability differs between arms');
    }
  }
  const plannedQuestions = expectedPairs.length + productionProtocol.transfer_pairs.length;
  const sessionCPU = sum(acquisitionManifest.sessions.map(session => finite(session.cpuSeconds, 'acquisition session CPU')));
  const sessionWall = sum(acquisitionManifest.sessions.map(session => finite(session.wallSeconds, 'acquisition session wall')));
  const entryCPU = sum(Object.values(acquisitionManifest.entries).map(entry => finite(entry.cpuSeconds, 'acquisition entry CPU')));
  const entryWall = sum(Object.values(acquisitionManifest.entries).map(entry => finite(entry.wallSeconds, 'acquisition entry wall')));
  const sessionOverheadCPU = Math.max(0, sessionCPU - entryCPU) / plannedQuestions;
  const sessionOverheadWall = Math.max(0, sessionWall - entryWall) / plannedQuestions;
  const sharedCPU = average(recordGroups.A.rows, 'sharedAcquisitionCpuSeconds');
  const sharedWall = average(recordGroups.A.rows, 'sharedAcquisitionWallSeconds');
  for (const id of armIds) {
    if (Math.abs(average(recordGroups[id].rows, 'sharedAcquisitionCpuSeconds') - sharedCPU) > 1e-9 ||
        Math.abs(average(recordGroups[id].rows, 'sharedAcquisitionWallSeconds') - sharedWall) > 1e-9) {
      throw Error('Common acquisition allocation must be identical in all policies');
    }
  }
  const driverCPU = finite(campaign.driverOverheadCpuSeconds, 'driver overhead CPU') / campaign.records.length;
  const driverWall = Math.max(0, finite(campaign.wallSeconds, 'campaign wall') -
    sum(campaign.records.map(record => record.wallSeconds))) / campaign.records.length;
  const sourceAvailability = {
    planned: arms.A.attempts, inputBlocked: arms.A.inputBlocked,
    available: arms.A.attempts - arms.A.inputBlocked,
    scenarioProbability: (arms.A.attempts - arms.A.inputBlocked) / arms.A.attempts,
    interpretation: 'Observed fraction of the frozen intended questions, used as an explicit common scenario condition; not a market frequency estimate.',
  };
  return {
    schema: 'agi-alpha.work-discovery.calibration.v1', measurementKind: 'EXECUTED_PUBLIC_LOCAL',
    acceptanceScope: 'Selected structural GET 2xx application/json response-contract dossiers; documentation review is still required for runtime compatibility.',
    acceptanceSpecificationSha256, sourceManifestSha256: campaign.finalSourceCheck.sha256,
    acceptanceEquivalent: armIds.every(id => recordGroups[id].available.every(row => row.accepted)),
    evidence, arms, sourceAvailability,
    commonCosts: {
      experimentalAcquisitionCpuSecondsPerPlanned: sharedCPU,
      experimentalAcquisitionWallSecondsPerPlanned: sharedWall,
      experimentalArmSharingDivisor: armIds.length,
      standaloneAcquisitionCpuSecondsPerPlanned: sharedCPU * armIds.length + sessionOverheadCPU,
      standaloneAcquisitionWallSecondsPerPlanned: sharedWall * armIds.length + sessionOverheadWall,
      acquisitionSessionOverheadCpuSecondsPerPlanned: sessionOverheadCPU,
      acquisitionSessionOverheadWallSecondsPerPlanned: sessionOverheadWall,
      driverCpuSecondsPerPlanned: driverCPU,
      driverWallSecondsPerPlanned: driverWall,
      allocation: `Experimental acquisition is divided among ${armIds.length} arms and ${plannedQuestions} registered questions. Each standalone policy restores the four-arm factor, retains inter-question sharing and adds its session-overhead share once. Driver overhead is divided among the ${campaign.records.length} intended primary records.`,
    },
  };
}
