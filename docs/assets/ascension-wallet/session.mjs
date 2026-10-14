// SPDX-License-Identifier: Apache-2.0
import { MarkClient, unresolved } from './client.mjs';
import { RecoveryStore } from './recovery.mjs';
// Both workspaces use the same journal key and atomic Web Lock.
export class WalletSession {
  constructor(profile, storage, locks, notify = () => {}) {
    this.store = new RecoveryStore(storage, locks);
    this.client = new MarkClient(profile, notify, journal => {
      this.store.write(journal); this.last = JSON.stringify(journal);
    });
    this.last = null;
    this.sync();
  }
  sync() {
    const value = this.store.read(), raw = JSON.stringify(value);
    if (raw === this.last) return;
    if (value) this.client.restore(value);
    else if (unresolved(this.client.pending)) throw Error('Outstanding journal was removed. Export and reconcile before continuing.');
    this.last = raw; this.client.cancelPreview();
  }
  async exclusive(fn) { return this.store.exclusive(async () => { this.sync(); return fn(); }); }
  async prepare(action, values) { return this.exclusive(() => this.client.prepare(action,values)); }
  async confirm(ack, before = async () => {}) {
    return this.exclusive(async () => { await before(); return this.client.confirm(ack); });
  }
  async reconcile(hash) { return this.exclusive(() => this.client.receipt(hash,true)); }
  async restore(journal) {
    return this.exclusive(async () => {
      if (unresolved(this.client.pending)) throw Error('Reconcile the existing journal before importing another.');
      const check = new MarkClient(this.client.profile); check.restore(journal);
      if (check.pending) check.pending.status = 'submission-unknown';
      this.store.write(check.journal()); this.last = null; this.sync();
    });
  }
}
export function discoverWallets(target, add) {
  const seen = new Set();
  const accept = (provider,name) => {
    if (!provider || typeof provider.request !== 'function' || seen.has(provider) || seen.size >= 20) return;
    seen.add(provider); add(provider,String(name || 'Browser wallet').slice(0,80));
  };
  const listener = event => { try { accept(event.detail?.provider,event.detail?.info?.name); } catch { /* untrusted metadata */ } };
  target.addEventListener('eip6963:announceProvider',listener);
  target.dispatchEvent(new Event('eip6963:requestProvider'));
  accept(target.ethereum,'Browser wallet');
  return () => target.removeEventListener('eip6963:announceProvider',listener);
}
