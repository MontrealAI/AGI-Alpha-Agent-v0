// SPDX-License-Identifier: Apache-2.0
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const money = (value) => new Intl.NumberFormat('en-US', {style:'currency', currency:'USD'}).format(value);
  const pct = (value) => `${(value * 100).toFixed(2)}%`;
  const num = (value) => new Intl.NumberFormat('en-US', {maximumFractionDigits:6}).format(value);
  const local = BOOTSTRAP.mode === 'local';
  let report = null;
  let revision = 0;
  function clear() {
    revision += 1;
    report = null;
    $('result').hidden = true;
    $('empty').hidden = false;
    $('error').hidden = true;
  }
  function table(id, rows) {
    const target = $(id);
    target.replaceChildren();
    for (const row of rows) {
      const tr = document.createElement('tr');
      for (const value of row) {
        const td = document.createElement('td');
        td.textContent = String(value);
        tr.append(td);
      }
      target.append(tr);
    }
  }
  function chart(data) {
    const svg = $('equity-chart');
    svg.replaceChildren();
    const primary = [data.config.initial_cash, ...data.result.equity.map((r) => r.equity)];
    const reference = [data.config.initial_cash, ...data.benchmark.equity.map((r) => r.equity)];
    const all = [...primary, ...reference];
    let low = Math.min(...all), high = Math.max(...all);
    const gap = Math.max((high-low)*0.1, data.config.initial_cash*0.01);
    low -= gap; high += gap;
    const x = (i) => 72 + i / (primary.length-1)*700;
    const y = (v) => 264 - (v-low)/(high-low)*234;
    const node = (name, attrs, text) => {
      const element = document.createElementNS('http://www.w3.org/2000/svg', name);
      for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
      if (text !== undefined) element.textContent = text;
      svg.append(element);
    };
    node('title', {}, `Strategy finishes at ${money(primary.at(-1))}; buy-and-hold at ${money(reference.at(-1))}.`);
    for (let i=0;i<5;i++) {
      const value = low + (high-low)*i/4;
      node('line', {x1:'72', x2:'772', y1:String(y(value)), y2:String(y(value)), stroke:'#3c324c'});
      node('text', {x:'62', y:String(y(value)+4), 'text-anchor':'end'}, Math.round(value).toLocaleString('en-US'));
    }
    node('line', {x1:'72',x2:'772',y1:String(y(data.config.initial_cash)),y2:String(y(data.config.initial_cash)),stroke:'#efc386','stroke-dasharray':'5 5'});
    for (const [series,color] of [[reference,'#93e2ca'],[primary,'#bc9bff']]) {
      node('polyline', {points:series.map((v,i) => `${x(i)},${y(v)}`).join(' '),fill:'none',stroke:color,'stroke-width':'2.5'});
    }
    node('text', {x:'72',y:'292'}, 'Initial cash');
    node('text', {x:'772',y:'292','text-anchor':'end'}, data.result.equity.at(-1).date);
  }
  function show(data) {
    if (data.status !== 'complete' || data.execution !== 'paper_only') throw new Error('Incomplete paper report');
    report = data;
    const result = data.result, s = result.summary, b = data.benchmark.summary;
    $('empty').hidden = true; $('result').hidden = false;
    $('data-label').textContent = `${data.data.kind === 'synthetic' ? 'SYNTHETIC SCENARIO' : 'USER DATA · UNVERIFIED'} / ${data.data.dates} DATES / ${data.data.symbols.length} ASSETS`;
    $('result-title').textContent = `${data.config.strategy.replaceAll('_',' ')} · paper outcome`;
    $('risk-state').textContent = s.halted ? 'DRAWDOWN HALT TRIGGERED' : 'RUN COMPLETE · REVIEW REQUIRED';
    $('net-return').textContent = pct(s.net_return);
    $('net-return').className = s.net_return < 0 ? 'negative' : 'positive';
    $('net-pnl').textContent = `${money(s.net_pnl)} marked P&L`;
    $('drawdown').textContent = pct(s.max_drawdown);
    $('costs').textContent = money(s.fees+s.slippage_cost);
    $('cost-detail').textContent = `${money(s.fees)} fees + ${money(s.slippage_cost)} slippage`;
    $('date-range').textContent = `${result.equity[0].date} — ${result.equity.at(-1).date}`;
    chart(data);
    table('comparison', [
      ['Final equity',money(s.final_equity),money(b.final_equity)],
      ['Net return',pct(s.net_return),pct(b.net_return)],
      ['Maximum drawdown',pct(s.max_drawdown),pct(b.max_drawdown)],
      ['Realized P&L',money(s.realized_pnl),money(b.realized_pnl)],
      ['Unrealized P&L',money(s.unrealized_pnl),money(b.unrealized_pnl)],
      ['Fees',money(s.fees),money(b.fees)],
      ['Slippage already in fills',money(s.slippage_cost),money(b.slippage_cost)],
      ['Simulated fills',s.trades,b.trades],
      ['Observed bar VaR95',pct(s.observed_risk.var95),pct(b.observed_risk.var95)],
      ['Observed bar CVaR95',pct(s.observed_risk.cvar95),pct(b.observed_risk.cvar95)],
    ]);
    const last=result.equity.at(-1);
    $('reconcile').textContent = `Cash ${money(last.cash)} + positions ${money(last.market_value)} = equity ${money(last.equity)}. Realized ${money(s.realized_pnl)} + unrealized ${money(s.unrealized_pnl)} = net P&L ${money(s.net_pnl)}. Costs are already included.`;
    $('halt-note').hidden = !s.halted;
    $('halt-note').textContent = s.pending_liquidation ? 'The final close breached the drawdown limit. Liquidation is pending because no later open exists in this input.' : 'The drawdown limit triggered. Positions were liquidated at the next supplied open; re-entry stayed disabled. The observed loss may exceed the threshold.';
    table('decisions',result.decisions.slice(-12).map((r) => [`${r.signal_date} → ${r.execution_date}`,r.reason.replaceAll('_',' '),pct(Object.values(r.targets).reduce((a,b)=>a+b,0)),pct(r.estimated_risk.cvar95)]));
    table('trades',result.trades.slice(-12).map((r) => [`${r.date} / ${r.symbol}`,`${r.side} ${num(r.quantity)}`,money(r.fill_price),money(r.fee)]));
    table('positions',result.positions.map((r) => [r.symbol,num(r.quantity),money(r.cost_basis),money(r.last_close)]));
    $('configuration').textContent = JSON.stringify(data.config,null,2);
    $('input-hash').textContent = data.data.sha256;
    $('engine-hash').textContent = data.provenance.engine_sha256;
    $('methods').replaceChildren(...Object.values(data.method).map((value) => {const li=document.createElement('li');li.textContent=value;return li;}));
    $('status').textContent = local ? 'Complete. Inspect the ledger and download the evidence.' : 'Bundled report loaded. These are recorded paper measurements.';
  }
  $('mode-note').textContent = local ? 'LOCAL PAPER LAB · All calculations run in this local Python process. Default prices are synthetic. No API key, model, exchange account or Docker required.' : 'RECORDED PAPER EVIDENCE · This page displays an actual Python-engine report. It does not fetch live prices or place orders. Use the local app for a new experiment.';
  $('local-controls').hidden = !local;
  $('start-locally').hidden = local;
  if (!local) {
    $('run').textContent='Inspect scenario ↗';
    if (BOOTSTRAP.mode==='report') $('experiment').hidden=true;
  }
  $('clear-file').addEventListener('click',()=>{$('csv-file').value='';clear();$('status').textContent='Imported file cleared. Run a synthetic scenario.';});
  $('experiment').addEventListener('change',()=>{clear();$('status').textContent='Settings changed. Run again to produce matching evidence.';});
  $('experiment').addEventListener('submit',async(event)=>{
    event.preventDefault(); clear(); $('run').disabled=true;
    const activeRevision = revision;
    $('status').textContent=local ? 'Calculating signals, fills, risk and reconciliation…' : 'Loading recorded scenario…';
    try {
      if (!local) {show(BOOTSTRAP.scenarios[$('case').value]);return;}
      const config={strategy:$('strategy').value};
      for (const key of ['initial_cash','lookback','fee_bps','slippage_bps','rebalance_every','max_exposure','max_position','max_drawdown','max_cvar']) config[key]=Number($(key).value);
      const payload={case:$('case').value,config};
      const file=$('csv-file').files[0];
      if(file){if(file.size>2000000)throw new Error('CSV exceeds 2 MB');payload.csv=await file.text();}
      if (revision !== activeRevision) return;
      const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json','X-Finance-Token':BOOTSTRAP.token},body:JSON.stringify(payload)});
      const data=await response.json();
      if (revision !== activeRevision) return;
      if(!response.ok)throw new Error(data.error || `Request failed (${response.status})`);
      show(data);
    }catch(error){if(revision!==activeRevision)return;clear();$('error').textContent=error.message;$('error').hidden=false;$('status').textContent='Run failed. Correct the input and retry; no stale result is displayed.';}
    finally{$('run').disabled=false;}
  });
  $('download').addEventListener('click',()=>{
    if(!report)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)+'\n'],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='finance-alpha-report.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  if(BOOTSTRAP.report)show(BOOTSTRAP.report);
  else if(BOOTSTRAP.scenarios)show(BOOTSTRAP.scenarios.trend);
})();
