// SPDX-License-Identifier: Apache-2.0
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const stages = ['portfolio', 'schedule', 'brief'];
  const local = document.body.dataset.mode === 'local';
  let token = '', epoch = 0, busy = false, active = null, view = 'portfolio';
  let samples = {}, recordings = {}, draft = null, saved = [], control = 'ready', publicKey = '';
  let creationId = null;
  const fmt = number => Number(number).toLocaleString('en-US');
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function error(message) { $('error').textContent = message; $('error').hidden = false; }
  function clearError() { $('error').hidden = true; $('error').textContent = ''; }
  function download(text, name) {
    const url = URL.createObjectURL(new Blob([text], {type:'application/json'}));
    const anchor = node('a'); anchor.href = url; anchor.download = name; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function request(path, method = 'GET', value, raw = false) {
    const response = await fetch(path, {method, headers: {'Authorization':'Bearer '+token,
      ...(method === 'POST' ? {'Content-Type':'application/json'} : {})},
      ...(method === 'POST' ? {body: raw ? value : JSON.stringify(value ?? {})} : {})});
    const text = await response.text();
    let data; try { data = JSON.parse(text); } catch { throw new Error('The local service returned an unreadable response. Refresh retained state.'); }
    if (!response.ok) throw new Error(data.error || data.detail || `Local service returned HTTP ${response.status}`);
    return {data, text};
  }
  function controls() {
    const unlocked = local && Boolean(token);
    $('create').disabled = !unlocked || busy || control === 'paused' || !draft;
    $('refresh').disabled = !unlocked || busy;
    $('advance').disabled = !unlocked || busy || control === 'paused' || !active || !['ready','queued'].includes(active.state);
    $('advance').hidden = !local || ['completed','rejected'].includes(active?.state);
    $('recover').hidden = !local || !active || !['failed','running'].includes(active.state);
    $('recover').disabled = !unlocked || busy || control === 'paused';
    $('review-form').hidden = !local || !active || active.state !== 'review' || view !== active.next_stage;
    for (const id of ['approve','reject','review-note','review-check']) $(id).disabled = !unlocked || busy || control === 'paused';
    $('pause').disabled = !unlocked; $('pause').textContent = control === 'paused' ? 'Resume execution' : 'Pause execution';
    $('lock').disabled = !unlocked; $('copy-key').disabled = !publicKey;
    $('download').hidden = !active || active.state !== 'completed'; $('download').disabled = busy;
    for (const id of ['case','budget','risk','mandate-file','mandate-json','apply-json','download-input','history']) $(id).disabled = busy || (!local && id !== 'case') || (local && !token);
    $('unlock').hidden = !local || Boolean(token);
  }
  function table(headers, rows) {
    const wrapper = node('div', undefined, 'table-scroll'); wrapper.tabIndex = 0;
    const result = node('table'), head = node('thead'), tr = node('tr');
    headers.forEach(text => {const th = node('th', text); th.scope = 'col'; tr.append(th);});
    head.append(tr); result.append(head); const body = node('tbody');
    rows.forEach(row => {const line = node('tr'); row.forEach(value => line.append(node('td', String(value)))); body.append(line);});
    result.append(body); wrapper.append(result); return wrapper;
  }
  function svgElement(tag, attributes, text) {
    const element = document.createElementNS('http://www.w3.org/2000/svg',tag);
    Object.entries(attributes).forEach(([key,value]) => element.setAttribute(key,String(value)));
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function portfolioChart(spec, result) {
    const chart = svgElement('svg', {viewBox:'0 0 640 270',role:'img','aria-label':'Project cost versus assumed benefit; selected projects are violet'});
    chart.append(svgElement('line',{x1:65,y1:225,x2:625,y2:225,class:'axis'}),svgElement('line',{x1:65,y1:20,x2:65,y2:225,class:'axis'}));
    const xmax = Math.max(...spec.projects.map(p=>p.cost)), ymax = Math.max(...spec.projects.map(p=>p.value));
    const groups = new Map();
    spec.projects.forEach(p => {const key=`${p.cost}:${p.value}`;groups.set(key,[...(groups.get(key)||[]),p]);});
    groups.forEach(projects => {
      const p=projects[0];
      const x = 65+p.cost/xmax*510, y = 225-p.value/ymax*170;
      const circle = svgElement('circle',{cx:x,cy:y,r:projects.length>1?10:8,class:projects.some(item=>result.selected.includes(item.id))?'chosen':'other'});
      circle.append(svgElement('title',{},`${projects.map(item=>item.title).join('; ')}: each costs ${p.cost} ${spec.cost_unit}, assumed value ${p.value}. See the decision table for individual selections.`));
      const label=projects.map(item=>item.id).join(' + ');
      chart.append(circle,svgElement('text',{x:x>460?x-12:x+10,y:y-10,'text-anchor':x>460?'end':'start','font-size':10},label.length>30?label.slice(0,27)+'…':label));
    });
    chart.append(svgElement('text',{x:65,y:255,'font-size':12},`Resource cost · 0–${xmax} ${spec.cost_unit}`),svgElement('text',{x:65,y:14,'font-size':12},`Assumed value · 0–${fmt(ymax)}`));
    return chart;
  }
  function scheduleChart(result) {
    const resources = [...new Set(result.operations.map(op=>op.machine))];
    const chart = svgElement('svg',{viewBox:`0 0 640 ${70+resources.length*58}`,role:'img','aria-label':'Verified resource schedule with non-overlapping operations'});
    resources.forEach((resource,index)=>{
      const y = 30+index*58; chart.append(svgElement('text',{x:0,y:y+20,'font-size':11},resource));
      result.operations.filter(op=>op.machine===resource).forEach((op,i)=>{
        const x = 115+op.start/result.makespan*510, width = (op.end-op.start)/result.makespan*510;
        const rect = svgElement('rect',{x,y,width:Math.max(1,width-2),height:31,rx:4,fill:i%2?'#8062ac':'#bba0ff'});
        rect.append(svgElement('title',{},`${op.job}: ${op.start}–${op.end}`)); chart.append(rect);
        if(width>75)chart.append(svgElement('text',{x:x+4,y:y+20,'font-size':10,class:'bar-label'},op.job.length>12?op.job.slice(0,10)+'…':op.job));
      });
    });
    chart.append(svgElement('text',{x:115,y:60+resources.length*58,'font-size':12},`0 → ${result.makespan} ${active.mandate.time_unit}`)); return chart;
  }
  function render() {
    const jobs = active?.jobs || {}, job = jobs[view], result = job?.result;
    $('mandate-title').textContent = active?.mandate.title || 'A mandate becomes accountable work.';
    $('workflow-state').textContent = (control==='paused' && local ? 'PAUSED · ' : '')+(active?.state || 'NOT STARTED').toUpperCase();
    stages.forEach(stage=>{
      const button = document.querySelector(`[data-stage="${stage}"]`);
      button.setAttribute('aria-pressed',String(view===stage));
      $(`${stage}-state`).textContent = jobs[stage]?.state || (active?.next_stage===stage?'Ready to run':'Blocked by review');
    });
    $('empty').hidden = Boolean(result); $('result').hidden = !result;
    $('stage-visual').replaceChildren(); $('stage-detail').replaceChildren(); $('trace').replaceChildren();
    if (!result) {
      for (const id of ['metric-value','value-unit','metric-cost','budget-remaining','metric-time','metric-tardiness','stage-kicker','stage-title','stage-status','raw-result']) $(id).textContent='';
    }
    if (result) {
      const spec = active.mandate, portfolio = jobs.portfolio?.result, schedule = jobs.schedule?.result;
      $('metric-value').textContent = portfolio ? fmt(portfolio.value) : '—'; $('value-unit').textContent = spec.value_unit;
      $('metric-cost').textContent = portfolio ? `${fmt(portfolio.cost)} / ${fmt(spec.budget)}` : '—';
      $('budget-remaining').textContent = `${spec.cost_unit} · ${portfolio ? spec.budget-portfolio.cost : spec.budget} unallocated`;
      $('metric-time').textContent = schedule ? `${fmt(schedule.makespan)} ${spec.time_unit}` : 'Awaiting schedule';
      $('metric-tardiness').textContent = schedule ? `Total tardiness: ${schedule.tardiness} ${spec.time_unit}` : 'Portfolio approval required first';
      $('stage-kicker').textContent = view.toUpperCase()+' · ACTUAL NATIVE EXECUTION';
      $('stage-title').textContent = {portfolio:'A feasible, inspectable portfolio.',schedule:'Shared capacity, resolved.',brief:'Evidence behind the mandate.'}[view];
      $('stage-status').textContent = job.state.toUpperCase();
      if (view==='portfolio') {
        $('stage-visual').append(portfolioChart(spec,result));
        $('stage-detail').append(node('p',`Assumed value ${fmt(result.value)} versus density-greedy baseline ${fmt(result.baseline_value)}. ${fmt(result.evaluations)} evaluations. ${result.optimality_proven?'Optimal value verified by enumeration.':'Heuristic solution; optimality is not established.'}`,'muted'));
        $('stage-detail').append(table(['Project','Cost','Assumed value','Risk','Decision'],spec.projects.map(p=>[p.title,p.cost,fmt(p.value),p.risk,result.selected.includes(p.id)?'Selected':'Not selected'])));
      } else if (view==='schedule') {
        $('stage-visual').append(scheduleChart(result));
        $('stage-detail').append(node('p','The schedule verifies every operation, its duration, job precedence and resource exclusivity. It is a plan; no external jobs have been submitted.','muted'));
        $('stage-detail').append(table(['Project','Resource','Start','End'],result.operations.map(op=>[op.job,op.machine,op.start,op.end])));
      } else {
        $('stage-detail').append(node('p',result.method,'muted'));
        result.findings.forEach(finding=>{
          const block = node('blockquote',finding.quote); block.append(node('cite',`Source: ${finding.source_id}`)); $('stage-detail').append(block);
          if(finding.claim!==finding.quote) $('stage-detail').append(node('p',finding.claim));
        });
        $('stage-detail').append(node('p','Quotation presence is checked. Source authenticity, meaning and operational assumptions still require human judgment.','muted'));
      }
      (job.stages||[]).forEach(stage=>{
        const item = node('li'); item.append(node('strong',stage.role+' · '),node('span',JSON.stringify(stage.detail))); $('trace').append(item);
      });
      $('raw-result').textContent = JSON.stringify({request:job.request,result,verification:job.verification,review:job.review},null,2);
    }
    const state = active?.state;
    $('action-title').textContent = !local?'Recorded execution, inspectable evidence.':state==='completed'?'All three results approved.':state==='review'?'Your review is the next step.':state==='rejected'?'This mandate is stopped.':'One explicit step at a time.';
    $('action-description').textContent = !local?'These are actual native fixture runs with automated fixture approvals, not independent validators. Download a packet or launch the local workspace to make your own decisions.':state==='review'?'Inspect the active stage above. Approval binds its current revision and result fingerprint; it does not execute the next stage.':state==='rejected'?'The rejected result remains in the signed journal. Start a new mandate to change assumptions.':state==='completed'?'Export the complete signed packet. Verify it independently using the public key obtained from a trusted channel.':state==='failed'?'The failure is retained. Refresh, inspect the trace, then explicitly recover and retry.':state==='running'?'Execution is active or its worker lease has not expired. Refresh or pause; recovery is allowed only after lease expiry.':`Run ${active?.next_stage || 'the first stage'} to calculate a result. The agent will stop at review.`;
    $('advance').textContent = `Run ${active?.next_stage || 'next stage'}`;
    $('public-key').textContent = publicKey || 'Unlock the local workspace to inspect its public key.';
    controls();
  }
  function applySnapshot(snapshot) {
    active = snapshot; publicKey = snapshot.identity; control = snapshot.control || 'ready';
    view = snapshot.jobs[snapshot.next_stage] ? snapshot.next_stage : stages.filter(stage=>snapshot.jobs[stage]).at(-1)||'portfolio';
    $('review-note').value=''; $('review-check').checked=false; render();
  }
  function applyDraft(value) {
    draft = structuredClone(value); creationId=null; $('budget').value=draft.budget; $('risk').value=draft.max_risk;
    $('cost-unit').textContent=draft.cost_unit; $('provenance').textContent=draft.provenance;
    $('mandate-json').value=JSON.stringify(draft,null,2); controls();
  }
  function lockWorkspace() {
    epoch++; token=''; busy=false; active=null; saved=[]; publicKey=''; control='ready'; view='portfolio';
    $('access-code').value=''; $('review-note').value=''; $('review-check').checked=false;
    $('mandate-file').value=''; $('advanced').open=false; $('case').value='balanced';
    draft=null; creationId=null;
    for (const id of ['budget','risk','mandate-json']) $(id).value='';
    for (const id of ['cost-unit','provenance']) $(id).textContent='';
    if(samples.balanced)applyDraft(samples.balanced);
    $('history').replaceChildren(node('option','Unlock to restore saved mandates'));
    $('mode-note').textContent='Private local workspace. Unlock with the access code printed in your terminal.';
    $('status').textContent='Tab locked. Unsaved inputs and review notes were cleared; the local journal is retained.';
    clearError(); render(); $('access-code').focus();
  }
  async function refresh() {
    const generation=epoch; const response=await request('/api/status'); if(generation!==epoch)return;
    const data=response.data; saved=data.workflows; publicKey=data.public_key; control=data.control;
    $('history').replaceChildren(node('option','Select a saved mandate'));
    $('history').firstChild.value='';
    saved.forEach(item=>{const option=node('option',`${item.mandate.title} · ${item.state}`);option.value=item.id;$('history').append(option);});
    if(active){const next=saved.find(item=>item.id===active.id);if(next){
      if(active.jobs[active.next_stage]?.digest!==next.jobs[next.next_stage]?.digest){$('review-check').checked=false;$('review-note').value='';}
      active=next;$('history').value=active.id;}}
    $('status').textContent=`Signed journal verified · ${saved.length} mandate(s) · ${data.model}`; render();
  }
  async function action(callback) {
    if(busy)return; const generation=epoch; busy=true; clearError(); controls();
    try{await callback();}catch(exc){if(generation===epoch)error(String(exc.message||exc));}
    finally{if(generation===epoch){busy=false;controls();}}
  }
  async function mutate(kind,value) {
    const ident=active.id, generation=epoch;
    const response=await request(`/api/workflows/${ident}/${kind}`,'POST',value);
    if(generation!==epoch)return;
    if(active?.id===ident)applySnapshot(response.data);
    await refresh();
  }
  function recorded(caseId) {
    const packet=JSON.parse(recordings[caseId].packet_json), jobs={};
    stages.forEach(stage=>{const receipt=packet.body.receipts[stage].receipt; jobs[stage]={...receipt.body.document,id:receipt.body.mission,revision:receipt.body.sequence,digest:receipt.hash};});
    applySnapshot({id:packet.body.workflow_id,mandate:packet.body.mandate,state:'completed',next_stage:null,jobs,identity:packet.public_key,control:'ready'});
    view='portfolio'; render(); $('status').textContent='Recorded native execution · synthetic assumptions · all approvals are automated fixtures';
  }
  $('unlock-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
    const generation=epoch;
    token=$('access-code').value.trim(); $('access-code').value='';
    $('status').textContent='Checking local access…'; controls();
    try{await refresh();if(generation===epoch)$('mode-note').textContent='Local workspace unlocked. Changes persist in your signed journal; new work always stops at review.';}
    catch(exc){if(generation===epoch)token='';throw exc;}
  });});
  $('lock').addEventListener('click',lockWorkspace);
  $('case').addEventListener('change',()=>{applyDraft(samples[$('case').value]);if(!local)recorded($('case').value);});
  for(const id of ['budget','risk'])$(id).addEventListener('input',()=>{creationId=null;});
  $('mandate-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
    const generation=epoch;const spec={...draft,budget:Number($('budget').value),max_risk:Number($('risk').value)};
    creationId=creationId||crypto.randomUUID();const response=await request('/api/workflows','POST',{id:creationId,mandate:spec});
    if(generation!==epoch)return;creationId=null;applySnapshot(response.data);await refresh();
  });});
  $('advance').addEventListener('click',()=>action(()=>mutate('advance')));
  $('recover').addEventListener('click',()=>action(()=>mutate('recover')));
  $('review-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
    const job=active.jobs[active.next_stage];await mutate('review',{revision:job.revision,result_hash:job.verification.result_hash,approve:true,note:$('review-note').value.trim()});
  });});
  $('reject').addEventListener('click',()=>action(async()=>{
    if(!$('review-note').value.trim())throw new Error('Add a review note explaining the rejection.');
    const job=active.jobs[active.next_stage];await mutate('review',{revision:job.revision,result_hash:job.verification.result_hash,approve:false,note:$('review-note').value.trim()});
  }));
  $('refresh').addEventListener('click',()=>action(refresh));
  $('history').addEventListener('change',()=>{const item=saved.find(value=>value.id===$('history').value);if(item)applySnapshot(item);});
  $('pause').addEventListener('click',async()=>{const generation=epoch;try{clearError();await request('/api/control','POST',{state:control==='paused'?'ready':'paused'});if(generation===epoch)await refresh();}catch(exc){if(generation===epoch)error(exc.message);}});
  $('copy-key').addEventListener('click',()=>action(async()=>{const generation=epoch;await navigator.clipboard.writeText(publicKey);if(generation===epoch)$('status').textContent='Public key copied. Obtain it through a trusted channel when verifying another operator’s packet.';}));
  $('download').addEventListener('click',()=>action(async()=>{
    const generation=epoch;
    const text=local?(await request(`/api/workflows/${active.id}/export`)).text:recordings[$('case').value].packet_json;
    if(generation!==epoch)return;
    download(text,`sovereign-${active.id}.json`);$('status').textContent='Signed packet downloaded. No private signing key or access code is included.';
  }));
  $('download-input').addEventListener('click',()=>{if(draft)download(JSON.stringify({...draft,budget:Number($('budget').value),max_risk:Number($('risk').value)},null,2),'sovereign-mandate.json');});
  async function importRaw(raw) {const generation=epoch;const response=await request('/api/validate','POST',raw,true);if(generation!==epoch)return;applyDraft(response.data);$('status').textContent='Mandate validated. Create it to start a new, independent review workflow.';}
  $('apply-json').addEventListener('click',()=>action(()=>importRaw($('mandate-json').value)));
  $('mandate-file').addEventListener('change',()=>action(async()=>{const generation=epoch;const file=$('mandate-file').files[0];if(!file)return;if(file.size>262144)throw new Error('Mandate file exceeds 256 KiB.');const raw=await file.text();if(generation===epoch)await importRaw(raw);}));
  document.querySelectorAll('[data-stage]').forEach(button=>button.addEventListener('click',()=>{view=button.dataset.stage;$('review-check').checked=false;render();}));
  async function init() {
    samples=await (await fetch('examples.json')).json();applyDraft(samples.balanced);
    if(!local){$('mode-label').textContent='RECORDED NATIVE EVIDENCE';$('mode-note').textContent='Recorded native execution over synthetic operational assumptions. No live agents, wallet access, token transfers or independent validator approvals occur on this page.';$('identity-title').textContent='Public fixture signing identity';$('identity-note').textContent='This key checks fixture integrity. Automated fixture approvals are not independent validation or operational authorization.';$('unlock').hidden=true;$('history-wrap').hidden=true;$('control-buttons').hidden=true;$('advanced').hidden=true;$('mandate-form').hidden=true;$('create').hidden=true;
      recordings=(await (await fetch('recorded.json')).json()).cases;recorded('balanced');
    }else{$('status').textContent='Ready. Unlock the local workspace to create or resume a mandate.';render();}
  }
  init().catch(exc=>error('Could not load the workspace assets. Reload to retry. '+exc.message));
})();
