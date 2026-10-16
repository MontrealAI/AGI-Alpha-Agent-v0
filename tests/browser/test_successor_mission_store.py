# SPDX-License-Identifier: Apache-2.0
"""Real IndexedDB transactions, conflicting tabs, persistence and bounded failures."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            result = page.evaluate(
                """async () => {
              const modulePath='/examples/successor-workbench/mission-store.mjs';
              const {openMissionStore,MAX_RECORD_BYTES} = await import(modulePath);
              const check = (ok, label) => { if (!ok) throw Error(label); };
              const rejects = async (action, code) => {
                try { await action(); } catch (e) { check(e.code === code, `${code}: ${e}`); return; }
                throw Error(`Expected ${code}`);
              };
              await rejects(() => openMissionStore({indexedDB:null}), 'LOCAL_STORAGE_UNAVAILABLE');
              const a = await openMissionStore({name:'mission-store-test'});
              const b = await openMissionStore({name:'mission-store-test'});
              const initial = {missionId:'mission_0001',revision:0,value:'initial'};
              await a.save(initial);
              const results = await Promise.allSettled([
                a.save({...initial,revision:1,value:'a'},0),
                b.save({...initial,revision:1,value:'b'},0),
              ]);
              check(results.filter(x=>x.status==='fulfilled').length===1,'exactly one CAS winner');
              check(results.find(x=>x.status==='rejected').reason.code==='LOCAL_REVISION_CONFLICT','conflict');
              const winner = await b.get(initial.missionId);
              check(winner.revision===1,'revision preserved');
              await rejects(()=>a.save(initial),'LOCAL_REVISION_CONFLICT');
              await rejects(()=>a.save({...winner,revision:3},1),'INVALID_NEXT_REVISION');
              const oversized={...winner,revision:2,value:'x'.repeat(MAX_RECORD_BYTES)};
              await rejects(()=>a.save(oversized,1),'LOCAL_RECORD_LIMIT');
              check((await b.get(initial.missionId)).revision===1,'rejected writes preserve state');
              a.close(); b.close();
              const recovered = await openMissionStore({name:'mission-store-test'});
              check(JSON.stringify(await recovered.get(initial.missionId))===JSON.stringify(winner),'recovery exact');
              for(let i=2;i<=12;i++){
                await recovered.save({missionId:`mission_${String(i).padStart(4,'0')}`,revision:0});
              }
              await rejects(()=>recovered.save({missionId:'mission_0013',revision:0}),'LOCAL_MISSION_LIMIT');
              check((await recovered.list()).length===12,'mission limit');
              await recovered.save({...winner,revision:2,value:'allowed update at capacity'},1);
              recovered.close();
              await rejects(()=>recovered.get(initial.missionId),'LOCAL_STORAGE_CLOSED');
              const corrupt = await openMissionStore({name:'mission-corrupt-test'});
              const raw = await new Promise((resolve,reject)=>{
                const request=indexedDB.open('mission-corrupt-test');
                request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
              });
              await new Promise((resolve,reject)=>{
                const tx=raw.transaction('missions','readwrite');
                tx.objectStore('missions').put({missionId:'mission_corrupt',revision:-1});
                tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error);
              });
              await rejects(()=>corrupt.get('mission_corrupt'),'LOCAL_RECORD_CORRUPT');
              await rejects(()=>corrupt.list(),'LOCAL_RECORD_CORRUPT');
              await new Promise(resolve=>{
                const tx=raw.transaction('missions','readwrite');
                tx.objectStore('missions').put({missionId:'mission_aborted',revision:0});
                tx.onabort=resolve;tx.abort();
              });
              check(await corrupt.get('mission_aborted')===null,'aborted transaction leaves no partial record');
              raw.close();corrupt.close();
              return {winner,checks:15};
            }"""
            )
            assert result["checks"] == 15
            # A genuinely separate page reads the same committed origin database.
            other = context.new_page()
            other.goto(page.url)
            assert (
                other.evaluate(
                    """async()=>{
              const {openMissionStore}=await import('/examples/successor-workbench/mission-store.mjs');
              const store=await openMissionStore({name:'mission-store-test'});
              const record=await store.get('mission_0001');store.close();return record.revision;
            }"""
                )
                == 2
            )
            browser.close()
        print("PASS: real IndexedDB atomic conflicts, recovery, limits and separate-page visibility")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
