# SPDX-License-Identifier: Apache-2.0
"""Build the self-contained, source-bound Alpha flagship without remote dependencies."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    """Bundle only reviewed local modules; keep imported projects inert."""
    names: dict[Path, str] = {}
    sources: dict[str, str] = {}
    chunks: list[str] = []

    def visit(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Flagship modules must remain inside the repository")
        if path in names:
            return names[path]
        name = f"alpha_module_{len(names)}"
        names[path] = name
        source = path.read_text(encoding="utf-8")
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

        def imports(match: re.Match[str]) -> str:
            binding, location = match.groups()
            if not location.startswith("."):
                raise ValueError("Only repository-local modules may enter the browser bundle")
            binding = binding.strip().removeprefix("* as ")
            return f"const {binding} = {visit(path.parent / location)};"

        first_export = re.search(r"^export\s+", source, flags=re.MULTILINE)
        boundary = first_export.start() if first_export else 0
        prefix = re.sub(
            r"^import\s+([^;]*?)\s+from\s+['\"]([^'\"]+)['\"];", imports, source[:boundary], flags=re.MULTILINE
        )
        source = prefix + source[boundary:]
        exports = re.findall(r"^export\s+(?:async\s+)?(?:function|class|const)\s+(\w+)", source, flags=re.MULTILINE)
        source = re.sub(r"^export\s+", "", source, flags=re.MULTILINE)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
        return name

    engine_path = root / "examples/successor-alpha/engine.mjs"
    project_path = root / "examples/successor-alpha/project.mjs"
    engine = visit(engine_path)
    project = visit(project_path)
    research = visit(root / "examples/successor-alpha/research.mjs")
    continuity = visit(root / "examples/successor-alpha/continuity.mjs")
    capability = visit(root / "examples/successor-alpha/capability.mjs")
    computer = visit(root / "examples/successor-alpha/computer.mjs")
    learning = visit(root / "examples/successor-alpha/learning.mjs")
    transport = visit(root / "docs/assets/successor/engine.mjs")
    core_source = engine_path.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    deployment_path = root / "examples/successor-alpha/deployment.json"
    deployment = json.loads(deployment_path.read_text(encoding="utf-8"))
    template = root / "scripts/templates/successor-alpha"
    for path in [*template.iterdir(), deployment_path, Path(__file__).resolve()]:
        if path.is_file():
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    worker = (
        "\n".join(chunks)
        + f"\nconst alpha={engine},research={research},continuity={continuity},SOURCE_HASH={json.dumps(source_hash)};\n"
        + """
self.onmessage=async event=>{
  try {
    const options={
      sourceHash:SOURCE_HASH,
      onProgress:progress=>self.postMessage({type:'progress',progress})
    };
    const payload=event.data;
    const result=payload.kind==='strategy'
      ? await research.discoverStrategy(payload.mission,{...payload.options,...options})
      : payload.kind==='native'
        ? await continuity.runNativeHandoff(payload.handoff,options)
        : await alpha.runJoinExperiment(payload,{onProgress:options.onProgress});
    self.postMessage({type:'result',result});
  } catch(error) {self.postMessage({type:'error',message:error.message});}
};
"""
    )
    bootstrap = """
async function runAlphaTask(payload,{onProgress,signal}={}) {
  if(signal?.aborted)throw Error('Experiment stopped. No result was admitted.');
  if(typeof Worker==='undefined') {
    const options={signal,onProgress,checkpoint:()=>new Promise(r=>setTimeout(r,0))};
    if(payload.kind==='strategy')return research.discoverStrategy(payload.mission,{
      ...payload.options,sourceHash:SOURCE_HASH,signal,onProgress
    });
    if(payload.kind==='native')return continuity.runNativeHandoff(payload.handoff,{...options,sourceHash:SOURCE_HASH});
    return alpha.runJoinExperiment(payload,options);
  }
  return new Promise((resolve,reject)=>{
    let worker,url;
    const clean=()=>{worker?.terminate();if(url)URL.revokeObjectURL(url);signal?.removeEventListener('abort',cancel);};
    const cancel=()=>{clean();reject(Error('Experiment stopped. No result was admitted.'));};
    try {
      url=URL.createObjectURL(new Blob([WORKER_SOURCE],{type:'text/javascript'}));worker=new Worker(url);
      signal?.addEventListener('abort',cancel,{once:true});
      worker.onmessage=event=>{
        if(event.data.type==='progress')onProgress?.(event.data.progress);
        else if(event.data.type==='result'){clean();resolve(event.data.result);}
        else{clean();reject(Error(event.data.message||'The experiment could not finish.'));}
      };
      worker.onerror=()=>{
        clean();reject(Error('The local worker could not start. Save your project and try a modern desktop browser.'));
      };
      worker.postMessage(payload);
    }catch(error){clean();reject(error);}
  });
}
async function runAlphaMission(mission,options) { return runAlphaTask(mission,options); }
async function runAlphaResearch(mission,options={}) {
  const {signal,onProgress,...settings}=options;
  return runAlphaTask({kind:'strategy',mission,options:settings},{signal,onProgress});
}
async function runAlphaNative(handoff,options={}) {
  return runAlphaTask({kind:'native',handoff},options);
}
function exportPortable(dossier) {
  const clone=document.documentElement.cloneNode(true);
  const saved=clone.querySelector('#saved-project');
  if(!saved)throw Error('Portable project placeholder is unavailable.');
  saved.textContent=project.serializeProject(dossier).replaceAll('<','\\\\u003c');
  const learning=clone.querySelector('#saved-learning');
  if(learning)learning.textContent=serializeLearningArchive().replaceAll('<','\\\\u003c');
  for(const el of clone.querySelectorAll('[data-i18n]'))el.textContent=en[el.dataset.i18n];
  for(const el of clone.querySelectorAll('[data-i18n-aria]'))el.setAttribute('aria-label',ariaEn[el.dataset.i18nAria]);
  for(const el of clone.querySelectorAll('[data-i18n-alt]'))el.setAttribute('alt',altEn[el.dataset.i18nAlt]);
  for(const el of clone.querySelectorAll('[style]'))el.removeAttribute('style');
  clone.lang='en';clone.dataset.language=language;
  clone.querySelector('title').textContent=dossier.name+' · SUCCESSOR Ω';
  for(const a of clone.querySelectorAll('a[href]')) {
    const href=a.getAttribute('href');
    if(href&&!href.startsWith('#')&&!/^[a-z]+:/i.test(href)) {
      a.href=new URL(href,'https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/alpha/').href;
    }
  }
  return '<!doctype html>\\n'+clone.outerHTML;
}
"""
    code = "\n(()=>{\n'use strict';\n" + "\n".join(chunks)
    code += f"\nconst alpha={engine},project={project},SOURCE_HASH={json.dumps(source_hash)};\n"
    code += (
        f"const research={research},continuity={continuity},transport={transport},capability={capability},"
        f"computer={computer},learning={learning};\n"
    )
    reusable_source = {
        "engineSource": core_source,
        "researchSource": (root / "examples/successor-alpha/research.mjs").read_text(encoding="utf-8"),
    }
    code += "const REUSABLE_SOURCE=" + json.dumps(reusable_source, ensure_ascii=False) + ";\n"
    code += "const DEPLOYMENT=" + json.dumps(deployment, ensure_ascii=False) + ";\n"
    code += "const WORKER_SOURCE=" + json.dumps(worker, ensure_ascii=False) + ";\n"
    code += (
        "project.configure({engineSource:" + json.dumps(core_source, ensure_ascii=False) + ",deployment:DEPLOYMENT});\n"
    )
    code += bootstrap + (template / "app.js").read_text(encoding="utf-8") + "\n})();\n"
    if "</script" in code.lower():
        raise ValueError("Closing script tag is forbidden inside the flagship bundle")
    style = "\n" + (template / "style.css").read_text(encoding="utf-8") + "\n"
    page = (template / "index.html").read_text(encoding="utf-8")
    artwork_path = root / "docs/assets/successor-alpha/institution.webp"
    artwork = artwork_path.read_bytes()
    sources[artwork_path.relative_to(root).as_posix()] = hashlib.sha256(artwork).hexdigest()
    page = page.replace(
        "../../assets/successor-alpha/institution.webp", "data:image/webp;base64," + base64.b64encode(artwork).decode()
    )
    for key, value in (("SCRIPT", code), ("STYLE", style)):
        hashed = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        page = page.replace("{{" + key + "_HASH}}", "sha256-" + hashed).replace("{{" + key + "}}", value)
    notices = []
    for license_path in (root / "LICENSE", root / "examples/build-successor/vendor/agijobs/LICENSE"):
        sources[license_path.relative_to(root).as_posix()] = hashlib.sha256(license_path.read_bytes()).hexdigest()
        notices.append(license_path.read_text(encoding="utf-8"))
    page = page.replace("{{SOURCE_HASH}}", source_hash).replace("{{LICENSES}}", html.escape("\n\n".join(notices)))
    if "{{" in page:
        raise ValueError("Unexpanded flagship template")
    destination = root / "docs/successor/alpha"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(page, encoding="utf-8")
    manifest = {
        "schema": "successor-alpha-source/v1",
        "engineSourceHash": source_hash,
        "sources": sources,
        "pageSha256": hashlib.sha256(page.encode()).hexdigest(),
    }
    (destination / "sources.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    build()
