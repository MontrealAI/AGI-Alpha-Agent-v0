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
    core_source = engine_path.read_text(encoding="utf-8")
    source_hash = hashlib.sha256((core_source + "\n" + project_path.read_text(encoding="utf-8")).encode()).hexdigest()
    deployment_path = root / "examples/successor-alpha/deployment.json"
    deployment = json.loads(deployment_path.read_text(encoding="utf-8"))
    template = root / "scripts/templates/successor-alpha"
    for path in [*template.iterdir(), deployment_path, Path(__file__).resolve()]:
        if path.is_file():
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    worker = re.sub(r"^export\s+", "", core_source, flags=re.MULTILINE) + """
self.onmessage=async event=>{
  try {
    const result=await runJoinExperiment(event.data,{onProgress:progress=>self.postMessage({type:'progress',progress})});
    self.postMessage({type:'result',result});
  } catch(error) {self.postMessage({type:'error',message:error.message});}
};
"""
    bootstrap = """
async function runAlphaMission(mission,{onProgress,signal}={}) {
  if(signal?.aborted)throw Error('Experiment stopped. No result was admitted.');
  if(typeof Worker==='undefined')return alpha.runJoinExperiment(mission,{signal,onProgress,checkpoint:()=>new Promise(r=>setTimeout(r,0))});
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
      worker.onerror=()=>{clean();reject(Error('The local worker could not start. Save your project and try a modern desktop browser.'));};
      worker.postMessage(mission);
    }catch(error){clean();reject(error);}
  });
}
function exportPortable(dossier) {
  const clone=document.documentElement.cloneNode(true);
  const saved=clone.querySelector('#saved-project');
  if(!saved)throw Error('Portable project placeholder is unavailable.');
  saved.textContent=project.serializeProject(dossier).replaceAll('<','\\u003c');
  for(const el of clone.querySelectorAll('[data-i18n]'))el.textContent=en[el.dataset.i18n];
  for(const el of clone.querySelectorAll('[data-i18n-aria]'))el.setAttribute('aria-label',ariaEn[el.dataset.i18nAria]);
  for(const el of clone.querySelectorAll('[data-i18n-alt]'))el.setAttribute('alt',altEn[el.dataset.i18nAlt]);
  for(const el of clone.querySelectorAll('[style]'))el.removeAttribute('style');
  clone.lang='en';clone.dataset.language=language;
  clone.querySelector('title').textContent=dossier.name+' · SUCCESSOR Ω';
  for(const a of clone.querySelectorAll('a[href]')) {
    const href=a.getAttribute('href');
    if(href&&!href.startsWith('#')&&!/^[a-z]+:/i.test(href))a.href=new URL(href,'https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/alpha/').href;
  }
  return '<!doctype html>\\n'+clone.outerHTML;
}
"""
    code = "\n(()=>{\n'use strict';\n" + "\n".join(chunks)
    code += f"\nconst alpha={engine},project={project},SOURCE_HASH={json.dumps(source_hash)};\n"
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
    page = page.replace("{{SOURCE_HASH}}", source_hash).replace(
        "{{LICENSES}}", html.escape((root / "LICENSE").read_text(encoding="utf-8"))
    )
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
