// SPDX-License-Identifier: Apache-2.0
import {defaultConfig,validateConfig} from '../src/market.mjs';
export function configurationsFor(protocol){
  const result=[],main=protocol.main_grid,corners=protocol.adverse_corners;
  for(const integrationCents of main.integrationCents)for(const arrivalProbability of main.arrivalProbability)
    for(const choiceModel of main.choiceModel)for(const investmentCostBasis of main.investmentCostBasis){
      result.push({...defaultConfig,...protocol.fixed,integrationCents,arrivalProbability,choiceModel,investmentCostBasis,
        id:`robust-main-i${integrationCents}-a${arrivalProbability}-${choiceModel}-${investmentCostBasis}`});
    }
  if(result.length!==main.configurations)throw Error('Main grid count mismatch');
  for(const variant of corners.variants)for(const integrationCents of corners.integrationCents)
    for(const choiceModel of corners.choiceModel)for(const investmentCostBasis of corners.investmentCostBasis){
      result.push({...defaultConfig,...protocol.fixed,...variant.parameters,integrationCents,
        arrivalProbability:corners.arrivalProbability,choiceModel,investmentCostBasis,
        id:`robust-stress-${variant.id}-i${integrationCents}-a${corners.arrivalProbability}-${choiceModel}-${investmentCostBasis}`});
    }
  if(result.length!==protocol.total_configurations||result.length!==128)throw Error('Bounded total count mismatch');
  if(new Set(result.map(x=>x.id)).size!==result.length)throw Error('Duplicate condition identity');
  for(const c of result){
    validateConfig(c);
    if(c.initialPriceCents!==2000||c.pricingPolicy!=='fixed'||c.weeks!==52||c.initialCashCents!==100000||
      c.investmentFunding!=='seed-funded'||c.historicalCostTiming!=='opening'||c.nextAsset!==null)
      throw Error('A bounded fixed design field changed');
  }
  return result;
}
