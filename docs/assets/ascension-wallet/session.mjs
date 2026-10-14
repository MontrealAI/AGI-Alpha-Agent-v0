// SPDX-License-Identifier: Apache-2.0
import { MarkClient, unresolved, availableProfiles, canonicalProfile, deploymentDescriptor, sha256Text } from './client.mjs';
import { RecoveryStore, JOURNAL_KEY } from './recovery.mjs';
// Both workspaces use the same journal key and atomic Web Lock.
// A registry choice may recover persisted state; imported JSON never registers a profile.
export function profileForJournal(defaultProfile, storage) {
  const journal = new RecoveryStore(storage,null).read();
  if (!journal) return defaultProfile;
  const matches = availableProfiles(defaultProfile).filter(choice =>
    (choice.profile.profile === journal.profile || (!journal.profile && choice.stage==='archive')) && choice.profile.chainId === journal.chainId &&
    (!journal.deployment || canonicalProfile(deploymentDescriptor(choice.profile)) === canonicalProfile(journal.deployment)));
  const choice = matches.find(item => item.id === journal.profileIdentity) || matches[0];
  if (!choice) throw Error('The saved journal belongs to a deployment absent from this build. Export it and use its reviewed recovery build.');
  return choice.profile;
}
export class WalletSession {
  constructor(profile, storage, locks, notify = () => {}) {
    this.store = new RecoveryStore(storage, locks); this.notify=notify;
    this.client = this.makeClient(profile); this.last = null; this.sync();
  }
  makeClient(profile) {
    const client = new MarkClient(profile,this.notify,journal => {
      if (client !== this.client) throw Error('Deployment selection changed. Reopen the current workspace before continuing.');
      this.store.write(journal); this.last = JSON.stringify(journal);
    });
    return client;
  }
  sync() {
    const value=this.store.read(),raw=JSON.stringify(value);
    if (raw===this.last) return;
    if (value) this.client.restore(value);
    else if (this.client.history.some(unresolved)) throw Error('Outstanding journal was removed. Export and reconcile before continuing.');
    this.last=raw; this.client.cancelPreview();
  }
  async exclusive(fn) { return this.store.exclusive(async () => { this.sync(); return fn(); }); }
  async prepare(action, values) { return this.exclusive(() => this.client.prepare(action,values)); }
  async confirm(ack, before = async () => {}) {
    return this.exclusive(async () => { await before(); return this.client.confirm(ack); });
  }
  async reconcile(hash, verifyEffects = null) {
    return this.exclusive(async () => {
      const record=await this.client.receipt(hash,true,{requireEffectVerification:!!verifyEffects});
      if (record.status==='effect-unverified' && verifyEffects) {
        await verifyEffects(record); this.client.completeEffects(record);
      }
      return record;
    });
  }
  async restore(journal) {
    return this.exclusive(async () => {
      if (this.client.history.some(unresolved)) throw Error('Reconcile the existing journal before importing another.');
      const check=new MarkClient(this.client.profile); check.restore(journal);
      // Imported terminal labels and semantic flags are untrusted. Reconcile every
      // claimed broadcast, including older receipts, before permitting new signing.
      for (const record of check.history) {
        if (record === check.history.at(-1) || record.hash || record.candidateHash || !['not-submitted','rejected-by-wallet'].includes(record.status)) {
          record.status='submission-unknown'; record.effectVerified=false; delete record.effectBlockHash;
        }
      }
      this.store.write(check.journal()); this.last=null; this.sync();
    });
  }
  async selectProfile(profile) {
    return this.exclusive(async () => {
      const previous=this.client,next=this.makeClient(profile);
      if (previous.history.some(record => record.status==='awaiting-wallet')) throw Error('Finish the open wallet request before selecting a deployment.');
      const before=canonicalProfile(deploymentDescriptor(previous.profile)),after=canonicalProfile(deploymentDescriptor(next.profile));
      if (before===after) next.restore(previous.journal());
      else {
        if (previous.history.some(unresolved)) throw Error('Reconcile every outstanding transaction before changing deployment.');
        const keyFor=async identity => JOURNAL_KEY+'.deployment.'+await sha256Text(identity);
        if (previous.history.length) {
          const oldKey=await keyFor(before),oldRaw=JSON.stringify(previous.journal());
          this.store.storage.setItem(oldKey,oldRaw);
          if (this.store.storage.getItem(oldKey)!==oldRaw) throw Error('The previous deployment journal could not be preserved.');
        }
        const saved=this.store.storage.getItem(await keyFor(after));
        if (saved) {
          if (saved.length>1000000) throw Error('Saved deployment journal exceeds the size limit.');
          next.restore(JSON.parse(saved));
        }
      }
      next.requireEffectVerification=previous.requireEffectVerification;
      if (next.history.length || this.store.read()) { this.store.write(next.journal()); this.last=JSON.stringify(next.journal()); }
      else this.last=JSON.stringify(null);
      previous.detach(); this.client=next;
      if (previous.provider) next.select(previous.provider);
      next.emit(); return next;
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
