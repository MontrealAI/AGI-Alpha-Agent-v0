// SPDX-License-Identifier: Apache-2.0
import { t, setLanguage, currentLanguage } from './i18n.ts';
import type { Params } from '../config/params.ts';

interface ChangeInfo {
  popClamped: boolean;
  genClamped: boolean;
}
const MAX_VAL = 500;
export function initControls(
  params: Params,
  onChange: (p: Params, info: ChangeInfo) => void,
): { setValues: (p: Params) => void; pauseBtn: HTMLButtonElement; exportBtn: HTMLButtonElement; dropZone: HTMLElement } {
  const rootEl = document.getElementById('controls');
  if (!rootEl) {
    throw new Error('controls element not found');
  }
  const root: HTMLElement = rootEl;
  root.replaceChildren();
  function addLabel(text: string, input: HTMLElement): void {
    const label = document.createElement('label');
    label.appendChild(document.createTextNode(text + ' '));
    label.appendChild(input);
    root.appendChild(label);
  }

  const seedInput = document.createElement('input');
  seedInput.id = 'seed';
  seedInput.type = 'number';
  seedInput.min = '0';
  seedInput.setAttribute('aria-label', t('seed'));
  seedInput.tabIndex = 1;
  addLabel(t('seed'), seedInput);

  const popInput = document.createElement('input');
  popInput.id = 'pop';
  popInput.type = 'number';
  popInput.min = '1';
  popInput.max = String(MAX_VAL);
  popInput.setAttribute('aria-label', t('population'));
  popInput.tabIndex = 2;
  addLabel(t('population'), popInput);

  const genInput = document.createElement('input');
  genInput.id = 'gen';
  genInput.type = 'number';
  genInput.min = '1';
  genInput.max = String(MAX_VAL);
  genInput.setAttribute('aria-label', t('generations'));
  genInput.tabIndex = 3;
  addLabel(t('generations'), genInput);

  function addCheck(id: string, text: string, tab: number): HTMLInputElement {
    const c = document.createElement('input');
    c.id = id;
    c.type = 'checkbox';
    c.setAttribute('aria-label', text);
    c.tabIndex = tab;
    addLabel(text, c);
    return c;
  }

  const gauss = addCheck('gaussian', t('gaussian'), 4);
  const swap = addCheck('swap', t('swap'), 5);
  const jump = addCheck('jump', t('jump'), 6);
  const scramble = addCheck('scramble', t('scramble'), 7);
  const adaptive = addCheck('adaptive', t('adaptive'), 8);

  const pause = document.createElement('button');
  pause.id = 'pause';
  pause.setAttribute('role', 'button');
  pause.setAttribute('aria-label', t('pause'));
  pause.tabIndex = 9;
  pause.textContent = t('pause');
  root.appendChild(pause);

  const exportBtn = document.createElement('button');
  exportBtn.id = 'export';
  exportBtn.setAttribute('role', 'button');
  exportBtn.setAttribute('aria-label', t('export'));
  exportBtn.tabIndex = 10;
  exportBtn.textContent = t('export');
  root.appendChild(exportBtn);

  const drop = document.createElement('div');
  drop.id = 'drop';
  drop.setAttribute('role', 'button');
  drop.setAttribute('aria-label', t('drop'));
  drop.tabIndex = 10;
  drop.textContent = t('drop');
  root.appendChild(drop);

  const langSel = document.createElement('select');
  langSel.id = 'lang';
  langSel.tabIndex = 11;
  const en = document.createElement('option');
  en.value = 'en';
  en.textContent = 'English';
  const fr = document.createElement('option');
  fr.value = 'fr';
  fr.textContent = 'Français';
  const es = document.createElement('option');
  es.value = 'es';
  es.textContent = 'Español';
  langSel.append(en, fr, es);
  root.appendChild(langSel);
  function update(p: Params): void {
    seedInput.value=String(p.seed);
    popInput.value=String(Math.min(p.pop,MAX_VAL));
    genInput.value=String(Math.min(p.gen,MAX_VAL));
    const set=new Set<string>(p.mutations||[]);
    gauss.checked=set.has('gaussian');
    swap.checked=set.has('swap');
    jump.checked=set.has('jump');
    scramble.checked=set.has('scramble');
    adaptive.checked=p.adaptive||false;
  }
  update(params);
  function emit(){
    const muts=[gauss,swap,jump,scramble].filter(c=>c.checked).map(c=>c.id);
    let popVal=Math.min(+popInput.value,MAX_VAL);
    let genVal=Math.min(+genInput.value,MAX_VAL);
    const info: ChangeInfo = {
      popClamped: popVal !=== +popInput.value,
      genClamped: genVal !=== +genInput.value,
    };
    popInput.value=String(popVal);
    genInput.value=String(genVal);
    const p={seed:+seedInput.value,pop:popVal,gen:genVal,mutations:muts,adaptive:adaptive.checked};
    try{localStorage.setItem('insightParams',JSON.stringify(p));}catch{}
    onChange(p,info);
  }
  seedInput.addEventListener('change',emit);
  popInput.addEventListener('change',emit);
  genInput.addEventListener('change',emit);
  gauss.addEventListener('change',emit);
  swap.addEventListener('change',emit);
  jump.addEventListener('change',emit);
  scramble.addEventListener('change',emit);
  adaptive.addEventListener('change',emit);
  langSel.value=currentLanguage;
  langSel.addEventListener('change',async()=>{await setLanguage(langSel.value);location.reload();});
  return{setValues:update,pauseBtn:pause,exportBtn,dropZone:drop};
}
