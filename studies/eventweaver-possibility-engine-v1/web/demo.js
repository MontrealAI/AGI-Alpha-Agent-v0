(()=>{
'use strict';
const original=JSON.parse(document.getElementById('demo-data').textContent);
const patterns=original.spec.patterns;
let trace=original.trace.map(x=>({...x})),selected=9;
const timeline=document.getElementById('timeline');
function inspect(pattern,rows,t){
  const anchor=t-pattern.deadline;
  if(anchor<0)return {accepted:false,kind:'waiting',title:'Waiting for a complete interval',detail:`The first possible decision is at tick ${pattern.deadline}.`};
  for(let k=anchor;k<=t;k++)if(rows[k].rst)return {accepted:false,kind:'reset',title:'Reset cleared this interval',detail:`A reset at tick ${k} discards its pending anchors.`};
  if(!(rows[anchor].events&(1<<pattern.a)))return {accepted:false,kind:'empty',title:'No anchor matures at this tick',detail:`There is no A event at tick ${anchor}, ${pattern.deadline} ticks earlier.`};
  for(let k=anchor;k<=t;k++)if(rows[k].events&(1<<pattern.veto))return {accepted:false,kind:'veto',title:'Veto cancels the decision',detail:`Veto channel ${pattern.veto} fires at tick ${k}; both interval endpoints are included.`};
  for(let b=anchor+pattern.l1;b<=anchor+pattern.u1;b++){
    if(!(rows[b].events&(1<<pattern.b)))continue;
    for(let c=b+pattern.l2;c<=Math.min(t,b+pattern.u2);c++)if(rows[c].events&(1<<pattern.c))return {accepted:true,kind:'accepted',title:'Accepted at the deadline',detail:`A at ${anchor} → B at ${b} → C at ${c}. No veto occurs from ${anchor} through ${t}.`};
  }
  return {accepted:false,kind:'unmatched',title:'The required sequence is incomplete',detail:`The anchor at ${anchor} has no B–C path inside both permitted windows.`};
}
function simulate(rows,spec=patterns){return rows.map((_,t)=>spec.reduce((mask,p,j)=>mask|(inspect(p,rows,t).accepted?1<<j:0),0));}
function el(tag,classes,text){const x=document.createElement(tag);if(classes)x.className=classes;if(text!==undefined)x.textContent=text;return x;}
function label(text,tag=''){const x=el('div','row-label',text);if(tag)x.appendChild(el('span','tag',tag));timeline.appendChild(x);}
function render(){
  const focus=document.activeElement?.id;
  const outputs=simulate(trace);
  timeline.replaceChildren();label('LOGICAL TICK');
  for(let t=0;t<trace.length;t++){
    const b=el('button','tick-header'+(t===selected?' selected':''),String(t));b.type='button';b.id=`tick-${t}`;b.setAttribute('aria-label',`Inspect tick ${t}`);b.onclick=()=>{selected=t;render();};timeline.appendChild(b);
  }
  const roles=['A · anchor','B · follow','C · confirm','V · veto','A · anchor','B · follow','C · confirm','V · veto'];
  for(let ch=0;ch<8;ch++){
    label(`CH ${ch}`,roles[ch]);
    for(let t=0;t<trace.length;t++){
      const on=!!(trace[t].events&(1<<ch));
      const b=el('button',`event-cell ${ch>=4?'control ':''}${ch%4===3?'veto ':''}${on?'on ':''}${t===selected?'selected':''}`);
      b.type='button';b.id=`cell-${ch}-${t}`;b.setAttribute('aria-label',`Channel ${ch}, ${roles[ch]}, tick ${t}`);b.setAttribute('aria-pressed',String(on));b.title=`CH ${ch} · tick ${t} · ${on?'event present':'empty'}; click to toggle`;
      b.onclick=()=>{trace[t].events^=1<<ch;selected=t;render();};timeline.appendChild(b);
    }
  }
  label('RESET','clears all');
  for(let t=0;t<trace.length;t++){
    const b=el('button',`event-cell reset ${trace[t].rst?'on ':''}${t===selected?'selected':''}`);b.type='button';b.id=`reset-${t}`;b.setAttribute('aria-label',`Reset at tick ${t}`);b.setAttribute('aria-pressed',String(trace[t].rst));b.onclick=()=>{trace[t].rst=!trace[t].rst;selected=t;render();};timeline.appendChild(b);
  }
  timeline.appendChild(el('div','timeline-divider'));
  for(let p=0;p<patterns.length;p++){
    label(p===0?'HERALDED PROBE':'CONTROL','decision');
    for(let t=0;t<trace.length;t++){const hit=!!(outputs[t]&(1<<p));const x=el('div',`output-cell ${p?'control ':''}${hit?'hit':''}`,hit?'●':'·');x.setAttribute('aria-label',`${patterns[p].name} at tick ${t}: ${hit?'accepted':'no output'}`);timeline.appendChild(x);}
  }
  const count=outputs.reduce((n,x)=>n+(x&1?1:0)+(x&2?1:0),0);
  document.getElementById('demo-summary').textContent=`${count} accepted decisions across ${trace.length} logical ticks`;
  document.getElementById('inspect-tick').value=selected;
  const box=document.getElementById('inspection-cards');box.replaceChildren();
  for(const p of patterns){const v=inspect(p,trace,selected);const card=el('div',`inspection ${v.accepted?'accepted':v.kind==='veto'||v.kind==='reset'?'cancelled':''}`);card.appendChild(el('h3','',p.name.replaceAll('_',' ')));card.appendChild(el('div','result',v.title));card.appendChild(el('div','detail',v.detail));box.appendChild(card);}
  document.getElementById('demo-live').textContent=`Tick ${selected}. ${count} accepted decisions in the current trace.`;
  if(focus)document.getElementById(focus)?.focus({preventScroll:true});
  const scroll=document.querySelector('.demo-scroll'),left=139+selected*28;
  if(left<scroll.scrollLeft+139)scroll.scrollLeft=Math.max(0,left-139);
  else if(left+28>scroll.scrollLeft+scroll.clientWidth)scroll.scrollLeft=Math.max(0,left-scroll.clientWidth+55);
  window.EventWeaverDemo.currentOutputs=outputs;
}
window.EventWeaverDemo={simulate,inspect,getTrace:()=>trace.map(x=>({...x})),getSpec:()=>JSON.parse(JSON.stringify(patterns)),setTrace:rows=>{if(!Array.isArray(rows)||rows.length!==original.trace.length||rows.some(x=>!Number.isInteger(x.events)||x.events<0||x.events>255||typeof x.rst!=='boolean'))throw Error('Invalid editable trace');trace=rows.map(x=>({...x}));render();},currentOutputs:[]};
document.getElementById('restore-demo').onclick=()=>{trace=original.trace.map(x=>({...x}));selected=9;render();};
document.getElementById('late-veto').onclick=()=>{trace[8].events|=1<<3;selected=8;render();};
document.getElementById('add-reset').onclick=()=>{trace[5].rst=true;selected=9;render();};
document.getElementById('clear-demo').onclick=()=>{trace=trace.map(()=>({events:0,rst:false}));trace[0].rst=true;selected=9;render();};
document.getElementById('inspect-tick').onchange=e=>{selected=Math.max(0,Math.min(trace.length-1,parseInt(e.target.value,10)||0));render();};
render();
const toggle=document.getElementById('toc-toggle'),mobile=document.getElementById('mobile-toc');
toggle.onclick=()=>{const isOpen=mobile.classList.toggle('open');toggle.setAttribute('aria-expanded',String(isOpen));};
mobile.querySelectorAll('a').forEach(a=>a.onclick=()=>{mobile.classList.remove('open');toggle.setAttribute('aria-expanded','false');});
document.getElementById('focus-mode').onclick=e=>{const yes=document.body.classList.toggle('reading-focus');e.target.textContent=yes?'Full edition':'Focus reading';e.target.setAttribute('aria-pressed',String(yes));if(yes)document.getElementById('paper').scrollIntoView();};
document.getElementById('print-edition').onclick=()=>window.print();
const equationOverflows=()=>document.querySelectorAll('.equation-scroll').forEach(x=>x.parentElement.classList.toggle('has-overflow',x.scrollWidth>x.clientWidth+1));
equationOverflows();window.addEventListener('resize',equationOverflows,{passive:true});
const headings=[...document.querySelectorAll('main [id]')].filter(x=>/^(H[1-3]|SECTION)$/.test(x.tagName));
const observer=new IntersectionObserver(entries=>{for(const item of entries)if(item.isIntersecting){document.querySelectorAll('.sidebar a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+item.target.id));}},{rootMargin:'-15% 0px -65% 0px'});
headings.forEach(h=>observer.observe(h));
window.addEventListener('scroll',()=>{const max=document.documentElement.scrollHeight-window.innerHeight;document.getElementById('read-progress').style.width=`${max>0?100*window.scrollY/max:0}%`;},{passive:true});
})();
