// SPDX-License-Identifier: Apache-2.0
// Public transaction intent only. This is recovery state, not authorization to sign.
export const JOURNAL_KEY = 'agialpha.mark-wallet-journal.v2';
export class RecoveryStore {
  constructor(storage, locks) { this.storage=storage; this.locks=locks; }
  read() {
    const raw=this.storage.getItem(JOURNAL_KEY);
    if (raw && raw.length>1000000) throw Error('Recovery journal exceeds the size limit.');
    return raw ? JSON.parse(raw) : null;
  }
  write(journal) {
    const raw=JSON.stringify(journal);
    if(raw.length>1000000) throw Error('Recovery journal exceeds the size limit.');
    this.storage.setItem(JOURNAL_KEY,raw);
    if(this.storage.getItem(JOURNAL_KEY)!==raw) throw Error('Recovery journal could not be saved. No new signing is allowed.');
  }
  async exclusive(fn) {
    if(!this.locks?.request) throw Error('This browser lacks Web Locks. Inspection is available; signing requires a supported secure browser.');
    return this.locks.request(JOURNAL_KEY,{ifAvailable:true},lock=>{
      if(!lock) throw Error('Another MARK tab is processing a wallet action. Finish it first.');
      return fn();
    });
  }
}
