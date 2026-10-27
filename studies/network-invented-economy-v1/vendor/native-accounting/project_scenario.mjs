// SPDX-License-Identifier: Apache-2.0
import {replayLedger} from './shadow-ledger.mjs';

export function projectScenario(serializedMissions) {
  if (typeof serializedMissions !== 'string' || serializedMissions.length > 250000)
    throw Error('Scenario projection requires bounded serialized JSON');
  const missions = JSON.parse(serializedMissions);
  if (!Array.isArray(missions)) throw Error('Scenario projection requires an array');
  const events = [];
  for (const mission of missions) {
    if (!mission || typeof mission !== 'object' || Array.isArray(mission) ||
        Object.keys(mission).sort().join(',') !==
        'acceptance,costsMinor,id,modeledCollectionsMinor,obligationMinor,reserveMinor')
      throw Error('Unexpected scenario projection fields');
    const {id, acceptance, modeledCollectionsMinor, costsMinor, reserveMinor, obligationMinor} = mission;
    const reference = 'SIMULATED accounting projection; no customer receipt or native mission is asserted';
    events.push({id:`${id}:mission`,type:'mission',missionId:id,acceptance,reference});
    const monetary = (type,category,amountMinor,basis) => ({
      id:`${id}:${type}:${category}`,type,missionId:id,reference,category,amountMinor,basis
    });
    events.push(monetary('revenue','collected',null,'unknown'));
    events.push(monetary('revenue','price',modeledCollectionsMinor,'assumed'));
    for (const category of ['delivery','business','capability','maintenance']) {
      events.push(monetary('cost',category,costsMinor?.[category] ?? null,
        costsMinor?.[category] == null ? 'unknown' : 'assumed'));
    }
    events.push(monetary('reserve','reliability',reserveMinor,reserveMinor === null ? 'unknown' : 'assumed'));
    events.push(monetary('obligation','unpaid',obligationMinor,obligationMinor === null ? 'unknown' : 'assumed'));
  }
  const ledger = {schema:'alpha-shadow-ledger/v1',currency:'USD',events};
  return {
    schema:'network-economy-native-projection/v1',
    evidenceBasis:'SIMULATED',
    scope:'Reuses native arithmetic only. This is not a native mission, receipt, finite-cash engine, deployment or authority grant.',
    ledger,
    summary:replayLedger(ledger)
  };
}
