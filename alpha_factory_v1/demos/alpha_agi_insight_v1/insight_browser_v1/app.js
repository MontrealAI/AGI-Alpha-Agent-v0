// SPDX-License-Identifier: Apache-2.0
import {parseHash,toHash} from './src/config/params.js';
import {initControls} from './src/ui/ControlsPanel.js';
import {renderFrontier} from './src/render/frontier.js';
import {initCriticPanel} from './src/ui/CriticPanel.js';
import {loadExamples as loadCriticExamples, LogicCritic, FeasibilityCritic} from './src/wasm/critics.js';
import {save,load} from './src/state/serializer.ts';
import {initDragDrop} from './src/ui/dragdrop.js';
import {toCSV} from './src/utils/csv.js';
import {svg2png} from './src/render/svg2png.js';
import {strategyColors} from './src/render/colors.ts';
import {pinFiles} from './src/ipfs/pinner.ts';
import {initGestures} from './src/ui/gestures.js';
import {initFpsMeter} from './src/ui/fpsMeter.js';
import {initI18n,t} from './src/ui/i18n.js';
import {chat as llmChat} from './src/utils/llm.js';
import { initTelemetry } from '@insight-src/telemetry.js';
import { lcg } from './src/utils/rng.js';
import { paretoFront } from './src/utils/pareto.js';
import { paretoEntropy } from './src/utils/entropy.ts';
import { Archive } from './src/archive.ts';
import { initEvolutionPanel } from './src/ui/EvolutionPanel.ts';
import { initSimulatorPanel } from './src/ui/SimulatorPanel.ts';
import { initPowerPanel } from './src/ui/PowerPanel.js';
import { initAnalyticsPanel } from './src/ui/AnalyticsPanel.js';
import { initArenaPanel } from './src/ui/ArenaPanel.ts';
import { initErrorBoundary, record } from './src/utils/errorBoundary.js';
import { createSandboxWorker } from './src/utils/sandbox.ts';

let panel,pauseBtn,exportBtn,dropZone
let criticPanel,logicCritic,feasCritic
let current,rand,pop,gen,svg,view,info,running=true
let worker
let telemetry
let fpsStarted=false;
let workerStart=0;
let archive,evolutionPanel,powerPanel,analyticsPanel;
let arenaPanel,debateWorker,debateTarget;
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast.id);
  toast.id = setTimeout(() => t.classList.remove('show'), 2000);
}
window.toast = toast;
window.llmChat=llmChat;

window.addEventListener('message', (ev) => {
  if (ev.data && ev.data.type === 'error') {
    record(ev.data, true);
    toast(t('worker_error'));
  }
});

function applyTheme(t){
  document.documentElement.dataset.theme=t;
}
function loadTheme(){
  const saved=localStorage.getItem('theme');
  if(saved) applyTheme(saved);
  else if(window.matchMedia('(prefers-color-scheme:light)').matches) applyTheme('light');
}
function toggleTheme(){
  const cur=document.documentElement.dataset.theme==='light'?'light':'dark';
  const next=cur==='light'?'dark':'light';
  applyTheme(next);
  localStorage.setItem('theme',next);
}

function setupView(){
  d3.select('#canvas').select('svg').remove();
  svg=d3.select('#canvas').append('svg')
        .attr('viewBox','0 0 500 500')
        .style('touch-action','none');
  view=svg.append('g');
  info=svg.append('text').attr('x',20).attr('y',30).attr('fill','#fff')
  initGestures(svg.node(), view.node ? view.node() : view)
}

function updateLegend(strats){
  const legend=document.getElementById('legend');
  legend.innerHTML='';
  for(const s of strats){
    const span=document.createElement('span');
    const sw=document.createElement('i');
    sw.style.background=strategyColors[s];
    sw.style.display='inline-block';
    sw.style.width='10px';
    sw.style.height='10px';
    sw.style.marginRight='4px';
    span.appendChild(sw);
    span.append(s);
    legend.appendChild(span);
  }
}

function updateDepthLegend(){
  const dl=document.getElementById('depth-legend');
  dl.innerHTML='depth';
  const bar=document.createElement('div');
  bar.className='bar';
  dl.appendChild(bar);
}

async function start(p){
  current=p
  rand=lcg(p.seed)
  pop=Array.from({length:p.pop},()=>({logic:rand(),feasible:rand(),strategy:'base',depth:0,horizonYears:p.gen}))
  gen=0
  running=true
  setupView()
  if(!fpsStarted){initFpsMeter(() => running);fpsStarted=true;}
  updateLegend(p.mutations)
  if(worker) worker.terminate()
  worker=await createSandboxWorker('./worker/evolver.js')
  if(navigator.gpu){
    worker.postMessage({type:'gpu', available: window.USE_GPU !== false})
  }
  worker.onmessage=ev=>{
    if(ev.data.toast){toast(ev.data.toast);return}
    if(analyticsPanel) analyticsPanel.recordWorkerTime(performance.now()-workerStart)
    pop=ev.data.pop;rand.set(ev.data.rngState);requestAnimationFrame(step)
  }
  step()
}

function selectPoint(d, elem){
  const scores={
    logic:d.logic??0,
    feasible:d.feasible??0
  };
  if(logicCritic&&feasCritic){
    scores.logicCritic=logicCritic.score(`${d.logic}`);
    scores.feasCritic=feasCritic.score(`${d.feasible}`);
    scores.average=(scores.logicCritic+scores.feasCritic)/2;
  }
  if(criticPanel) criticPanel.show(scores,elem);
}

function step(){
  info.text(`gen ${gen}`)
  const front = paretoFront(pop)
  const entropy = paretoEntropy(front)
  window.entropy = entropy
  renderFrontier(view.node ? view.node() : view,pop,selectPoint)
  if(arenaPanel) arenaPanel.render(front)
  const md = Math.max(...pop.map(d=>d.depth||0))
  updateDepthLegend(md)
  if(analyticsPanel) analyticsPanel.update(pop, gen, entropy)
  archive.add(current.seed, current, front, [], 0).then(()=>evolutionPanel.render()).catch(()=>{})
  if(!running)return
  if(gen++>=current.gen){worker.terminate();return}
  const LOW=1.5, HIGH=2.5
  let scale=1
  if(entropy<LOW){
    for(let i=0;i<5;i++)pop.push({logic:rand(),feasible:rand(),strategy:'rand',depth:gen,horizonYears:current.gen})
  } else if(entropy>HIGH){
    scale=0.5
  }
  telemetry.recordRun(1)
  workerStart=performance.now()
  worker.postMessage({
    pop,
    rngState: rand.state(),
    mutations: current.mutations,
    popSize: current.pop,
    gen,
    adaptive: current.adaptive,
    sigmaScale: scale,
  })
}

function togglePause(){
  running=!running
  pauseBtn.textContent=running?t('pause'):t('resume')
  if(running)requestAnimationFrame(step)
}

async function exportState(){
  pop.gen=gen
  const json=save(pop,rand.state())
  const blob=new Blob([json],{type:'application/json'})
  const a=document.createElement('a')
  a.href=URL.createObjectURL(blob)
  a.download='state.json'
  a.click()
  URL.revokeObjectURL(a.href)
  if(window.PINNER_TOKEN){
    const file=new File([json],'state.json',{type:'application/json'})
    await pinFiles([file])
  }
}

function exportCSV(data){
  const csv = toCSV(data);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv"}));
  a.download = "population.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

async function exportPNG(){
  if(!svg) return;
  const blob = await svg2png(svg.node ? svg.node() : svg.node());
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "frontier.png";
  a.click();
  URL.revokeObjectURL(a.href);
}

async function loadState(text){
  try{
    const s=load(text)
    pop=s.pop
    gen=s.gen
    rand=lcg(0);rand.set(s.rngState)
    running=true
    pauseBtn.textContent=t('pause')
    setupView()
    updateLegend(current.mutations)
    if(worker) worker.terminate()
    worker=await createSandboxWorker('./worker/evolver.js')
    if(navigator.gpu){
      worker.postMessage({type:'gpu', available: window.USE_GPU !== false})
    }
    worker.onmessage=ev=>{
      if(ev.data.toast){toast(ev.data.toast);return}
      if(analyticsPanel) analyticsPanel.recordWorkerTime(performance.now()-workerStart)
      pop=ev.data.pop;rand.set(ev.data.rngState);requestAnimationFrame(step)
    }
    step()
    toast(t('state_loaded'))
  }catch{toast(t('invalid_file'))}
}

function apply(p, info = {}){
  if(info.popClamped) toast('max population is 500');
  if(info.genClamped) toast('max generations is 500');
  location.hash=toHash(p);
}

window.addEventListener('DOMContentLoaded',async()=>{
  initErrorBoundary();
  await initI18n();
  const disc = document.getElementById('disclaimer');
  if (disc) disc.textContent = t('disclaimer');
  telemetry = initTelemetry();
  archive = new Archive();
  if (typeof document.hasStorageAccess === 'function') {
    try { await document.hasStorageAccess(); } catch { /* noop */ }
  }
  await archive.open();
  evolutionPanel = initEvolutionPanel(archive);
  powerPanel = initPowerPanel();
  powerPanel.update({ gpu: !!navigator.gpu, use: window.USE_GPU });
  await initSimulatorPanel(archive, powerPanel);
  analyticsPanel = initAnalyticsPanel();
  arenaPanel = initArenaPanel((pt) => {
    debateTarget = pt;
    const hypo = pt.summary || `logic ${pt.logic}`;
    debateWorker.postMessage({ hypothesis: hypo });
  });
  debateWorker = await createSandboxWorker('./worker/arenaWorker.js');
  debateWorker.onmessage = (ev) => {
    const { messages, score } = ev.data;
    if (debateTarget) {
      debateTarget.rank = (debateTarget.rank || 0) + score;
      pop.sort((a, b) => (a.rank || 0) - (b.rank || 0));
    }
    arenaPanel.show(messages, score);
    arenaPanel.render(paretoFront(pop));
  };
  await evolutionPanel.render();
  window.archive = archive;
  loadTheme()
  const ex=await loadCriticExamples()
  logicCritic=new LogicCritic(ex)
  feasCritic=new FeasibilityCritic(ex)
  criticPanel=initCriticPanel()
  panel=initControls(parseHash(),apply)
  pauseBtn=panel.pauseBtn
  exportBtn=panel.exportBtn
  dropZone=panel.dropZone
  const tb=document.getElementById("toolbar");
  const csvBtn=document.createElement("button");
  csvBtn.textContent=t('csv');
  csvBtn.setAttribute('aria-label','Export CSV');
  const pngBtn=document.createElement("button");
  pngBtn.textContent=t('png');
  pngBtn.setAttribute('aria-label','Download PNG');
  const shareBtn=document.createElement("button");
  shareBtn.textContent=t('share');
  shareBtn.setAttribute('aria-label','Share simulation');
  const themeBtn=document.createElement("button");
  themeBtn.textContent=t('theme');
  themeBtn.setAttribute('aria-label','Toggle theme');
  tb.appendChild(csvBtn);
  tb.appendChild(pngBtn);
  tb.appendChild(shareBtn);
  tb.appendChild(themeBtn);
  const installBtn=document.getElementById("install-btn");
  let deferredPrompt=null;
  window.addEventListener("beforeinstallprompt",(e)=>{
    e.preventDefault();
    deferredPrompt=e;
    installBtn.hidden=false;
  });
  installBtn.addEventListener("click",async()=>{
    if(!deferredPrompt)return;
    installBtn.hidden=true;
    deferredPrompt.prompt();
    try{await deferredPrompt.userChoice;}catch{ /* noop */ }
    deferredPrompt=null;
  });
  window.addEventListener("appinstalled",()=>{
    installBtn.hidden=true;
    deferredPrompt=null;
  });
  csvBtn.addEventListener("click",()=>exportCSV(pop));
  pngBtn.addEventListener("click",exportPNG);
  shareBtn.addEventListener("click", async () => {
    telemetry.recordShare();
    const url = location.origin + location.pathname + location.hash;
    let pinned = null;
    if (window.PINNER_TOKEN) {
      const json = save(pop, rand.state());
      const file = new File([json], "state.json", { type: "application/json" });
      pinned = await pinFiles([file]);
    }
    if (pinned && pinned.url) {
      if (navigator.clipboard) {
        try { await navigator.clipboard.writeText(pinned.url); } catch { /* noop */ }
      }
      toast(`pinned ${pinned.cid}`);
    } else {
      if (navigator.clipboard) {
        try { await navigator.clipboard.writeText(url); } catch { /* noop */ }
      }
      toast(t('link_copied'));
    }
  });
  themeBtn.addEventListener("click",toggleTheme);
  pauseBtn.addEventListener('click',togglePause)
  exportBtn.addEventListener('click',exportState)
  initDragDrop(dropZone,loadState)
  window.dispatchEvent(new HashChangeEvent('hashchange'))
})
window.addEventListener('hashchange', () => {
  const p = parseHash();
  panel.setValues(p);
  start(p);
  toast(t('simulation_restarted'));
});

