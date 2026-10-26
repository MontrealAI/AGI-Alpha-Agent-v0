// SPDX-License-Identifier: Apache-2.0
// Reporting-only replay of existing frozen worlds. Never modifies a frozen source or result.
import {readFileSync,writeFileSync,mkdirSync,existsSync,appendFileSync,createReadStream,statSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {createGunzip,gzipSync} from 'node:zlib';
import {createInterface} from 'node:readline';
import {isDeepStrictEqual} from 'node:util';
import {pairedSimulation} from './market-expose.mjs';
import {annotateExploratory,annotatePolicy} from './annotations.mjs';

const root=dirname(fileURLToPath(import.meta.url)),market=resolve(root,'..');
const args=process.argv.slice(2),out=resolve(args.includes('--output')?args[args.indexOf('--output')+1]:resolve(root,'results-01'));
const sha=value=>createHash('sha256').update(value).digest('hex'),sum=values=>values.reduce((a,b)=>a+b,0);
const manifest=JSON.parse(readFileSync(resolve(root,'source-manifest.json'),'utf8'));
const assert=(condition,message)=>{if(!condition)throw Error(message);};
function verifySources(){
  for(const f of manifest.files)assert(sha(readFileSync(resolve(market,f.path)))===f.sha256,`Reporting source identity changed: ${f.path}`);
  for(const stage of manifest.stages){
    assert(sha(readFileSync(resolve(market,stage.originalFreeze)))===stage.originalFreezeSHA256,'Original freeze changed');
    const freeze=JSON.parse(readFileSync(resolve(market,stage.originalFreeze),'utf8'));
    for(const f of freeze.files)assert(sha(readFileSync(resolve(market,f.path)))===f.sha256,`Frozen source changed: ${f.path}`);
    assert(sha(readFileSync(resolve(market,stage.originalArchive)))===stage.originalArchiveSHA256,'Original archive changed');
  }
}
verifySources();
assert(!existsSync(out),'Refusing to overwrite any prior reporting replay');
mkdirSync(out,{recursive:true});
const priorRows=readFileSync(resolve(market,'exploratory/results-01/outcomes.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const prior=new Map(priorRows.map(x=>[`${x.scenario}|${x.seed}|${x.arm}`,x]));

function reconstructBalances(firm,weeks){
  return weeks.map(week=>{
    const events=firm.cashEvents.filter(x=>x.week<=week),bills=firm.bills.filter(x=>x.week<=week),
      paid=bills.filter(x=>x.paid&&x.paidWeek<=week),invoices=firm.invoices.filter(x=>x.week<=week);
    const invoiceCollected=x=>x.status==='collected'&&x.collectedWeek<=week;
    // Defaults have no cash event; the frozen collect() resolves them at dueWeek.
    const invoiceDefaulted=x=>x.status==='defaulted'&&x.dueWeek<=week;
    const cash=firm.openingCashCents+sum(events.map(x=>x.amountCents)),accrued=sum(bills.map(x=>x.amountCents)),
      paidCosts=sum(paid.map(x=>x.amountCents)),obligations=accrued-paidCosts,
      receivables=sum(invoices.filter(x=>!invoiceCollected(x)&&!invoiceDefaulted(x)).map(x=>x.amountCents));
    return {week,cashCents:cash,receivablesCents:receivables,obligationsCents:obligations,
      overdueObligationsCents:sum(bills.filter(x=>x.dueWeek<=week&&!(x.paid&&x.paidWeek<=week)).map(x=>x.amountCents)),
      accruedCostsCents:accrued,paidCostsCents:paidCosts,
      grossInvoicesCents:sum(invoices.map(x=>x.amountCents)),
      grossCollectionsCents:sum(events.filter(x=>x.type==='simulated_collection').map(x=>x.amountCents)),
      writtenOffCents:sum(invoices.filter(invoiceDefaulted).map(x=>x.amountCents)),
      cashLessExistingObligationsCents:cash-obligations,
      accruedProfitExcludingOpeningCashCents:cash+receivables-obligations-firm.openingCashCents,
      insolvent:firm.insolvent&&firm.insolventWeek<=week};
  });
}

const completed=[];
try{
  for(const stage of manifest.stages){
    const output=resolve(out,`${stage.id}-competitor-accounts.jsonl.gz`),originalDigest=createHash('sha256'),replayedDigest=createHash('sha256');
    let pairedMatches=0,armMatches=0,competitorFirms=0,invoices=0,bills=0,cashEvents=0;
    const keys=new Set(),lines=createInterface({input:createReadStream(resolve(market,stage.originalArchive)).pipe(createGunzip()),crlfDelay:Infinity});
    for await(const line of lines){
      if(!line)continue;
      const original=JSON.parse(line),key=`${original.config.id}|${original.seed}`;
      assert(!keys.has(key),`Duplicate original identity: ${stage.id}/${key}`);keys.add(key);
      const replayed=pairedSimulation(original.config,original.seed),accounts={};
      for(const arm of ['A','B','C']){
        accounts[arm]=replayed.arms[arm].competitorAccounts;
        delete replayed.arms[arm].competitorAccounts;
      }
      if(stage.id==='exploratory')annotateExploratory(replayed);
      if(stage.id==='policy-diagnostic'){
        const c=original.config,regime=`${c.investmentCostBasis==='full-history'?'full':'adoption'}-${c.investmentFunding==='operating-surplus'?'earned':'seed'}`,
          priorId=`explore-i${c.integrationCents}-a${c.arrivalProbability}-m${c.ordinaryFinalizationMinutes}-${c.choiceModel}-${regime}`;
        annotatePolicy(replayed,c,original.seed,priorId,prior);
      }
      const replayedLine=JSON.stringify(replayed);
      if(replayedLine!==line){
        writeFileSync(resolve(out,'first-mismatch.json'),JSON.stringify({stage:stage.id,scenario:original.config.id,seed:original.seed,
          originalLineSHA256:sha(line),replayedLineSHA256:sha(replayedLine),fieldsEqual:isDeepStrictEqual(replayed,original)},null,2)+'\n');
        throw Error(`Original paired output did not match exactly: ${stage.id}/${key}`);
      }
      originalDigest.update(line+'\n');replayedDigest.update(replayedLine+'\n');pairedMatches++;
      for(const arm of ['A','B','C']){
        const originalArm=JSON.stringify(original.arms[arm]),replayedArm=JSON.stringify(replayed.arms[arm]);
        assert(originalArm===replayedArm,'Arm equality failed after full paired equality');armMatches++;
        const derived=Object.fromEntries(Object.entries(accounts[arm]).map(([id,firm])=>{
          competitorFirms++;invoices+=firm.invoices.length;bills+=firm.bills.length;cashEvents+=firm.cashEvents.length;
          const balances=reconstructBalances(firm,original.arms[arm].histories.balances.map(x=>x.week));
          assert(balances.at(-1).cashCents===firm.cashCents,'Reconstructed competitor cash mismatch');
          assert(balances.at(-1).accruedCostsCents===sum(Object.values(firm.costs)),'Reconstructed competitor accrued costs mismatch');
          assert(balances.at(-1).paidCostsCents===sum(Object.values(firm.paidCosts)),'Reconstructed competitor paid costs mismatch');
          return [id,balances];
        }));
        const supplement={schema:'agi-alpha-competitor-account-supplement/v1',stage:stage.id,scenario:original.config.id,
          seed:original.seed,arm,basis:'SIMULATED_REPORTING_ONLY',financialAuthority:'NONE',observedCustomerCollectionsCents:0,
          originalArchiveSHA256:stage.originalArchiveSHA256,originalPairedLineSHA256:sha(line),
          originalArmSHA256:sha(originalArm),replayedArmSHA256:sha(replayedArm),allOriginalFieldsMatchExactly:true,
          competitors:accounts[arm],reconstructedWeeklyBalances:derived,
          reconstructionBasis:'Posthoc end-of-week reconstruction from retained cash events, invoice issue/collection/default due dates and bill accrual/payment dates; native balanceHistory is preserved separately without invention.',
          finalAccounting:Object.fromEntries(Object.entries(derived).map(([id,balances])=>[id,balances.at(-1)]))};
        appendFileSync(output,gzipSync(JSON.stringify(supplement)+'\n',{level:6,mtime:0}));
      }
      if(pairedMatches%250===0)process.stdout.write(JSON.stringify({stage:stage.id,pairedExactMatches:pairedMatches})+'\n');
    }
    assert(pairedMatches===stage.pairedWorlds,'Stage paired count mismatch');
    assert(armMatches===stage.enterpriseRuns,'Stage arm count mismatch');
    const oldSHA=originalDigest.digest('hex'),newSHA=replayedDigest.digest('hex');assert(oldSHA===newSHA,'Stage JSON content digest differs');
    const receipt={stage:stage.id,pairedExactMatches:pairedMatches,armExactMatches:armMatches,competitorFirmAccounts:competitorFirms,
      competitorInvoices:invoices,competitorBills:bills,competitorCashEvents:cashEvents,
      originalArchiveSHA256:stage.originalArchiveSHA256,originalUncompressedJSONSHA256:oldSHA,replayedUncompressedJSONSHA256:newSHA,
      supplement:output.slice(out.length+1),supplementBytes:statSync(output).size,supplementSHA256:sha(readFileSync(output))};
    completed.push(receipt);writeFileSync(resolve(out,`${stage.id}-completion.json`),JSON.stringify(receipt,null,2)+'\n');
    process.stdout.write(JSON.stringify(receipt)+'\n');
  }
  verifySources();
  const completion={schema:'agi-alpha-reporting-only-replay-completion/v1',complete:true,
    completedUTC:new Date().toISOString(),sourceManifestSHA256:sha(readFileSync(resolve(root,'source-manifest.json'))),
    originalCoreSHA256:manifest.originalCoreSHA256,instrumentedCoreSHA256:manifest.instrumentedCoreSHA256,
    originalFrozenSourcesAndArchivesUnchanged:true,stages:completed,
    pairedExactMatches:sum(completed.map(x=>x.pairedExactMatches)),armExactMatches:sum(completed.map(x=>x.armExactMatches)),
    competitorFirmAccounts:sum(completed.map(x=>x.competitorFirmAccounts)),newEconomicScenarios:0,
    observedCustomerCollectionsCents:0,actualFinancialTransactions:0,
    interpretation:'Posthoc reporting supplement for the same frozen worlds; does not add economic scenarios or independent evidence.'};
  assert(completion.pairedExactMatches===6480&&completion.armExactMatches===19440,'Total replay identity count mismatch');
  writeFileSync(resolve(out,'completion.json'),JSON.stringify(completion,null,2)+'\n');
  process.stdout.write(JSON.stringify({complete:true,pairedExactMatches:completion.pairedExactMatches,armExactMatches:completion.armExactMatches})+'\n');
}catch(error){
  writeFileSync(resolve(out,'failure.json'),JSON.stringify({complete:false,utc:new Date().toISOString(),message:error.message,
    stack:error.stack,completedStages:completed,newEconomicScenarios:0},null,2)+'\n');
  throw error;
}
