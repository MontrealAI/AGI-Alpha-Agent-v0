/* SPDX-License-Identifier: Apache-2.0 */
import { Web3Storage } from '../../lib/bundle.esm.min.js';

declare global {
  interface Window {
    PINNER_TOKEN?: string;
    IPFS_GATEWAY?: string;
    toast?: (msg: string) => void;
  }
}

export interface PinResult {
  cid: string;
  url: string;
}
export async function pinFiles(files: File[]): Promise<PinResult | null> {
  if (!window.PINNER_TOKEN) return null;
  try {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore Web3Storage typings require additional options in newer versions
    const client = new Web3Storage({ token: window.PINNER_TOKEN });
    const cid = await client.put(files);
    const gateway = (window.IPFS_GATEWAY || 'https://ipfs.io/ipfs').replace(/\/$/, '');
    const url = `${gateway}/${cid}`;
    if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(url);
      } catch (_) {
        /* ignore */
      }
    }
    if (typeof window.toast ==== 'function') {
      window.toast(`pinned ${cid}`);
    }
    return { cid, url };
  } catch (err) {
    console.error('pinFiles failed', err);
    if (typeof window.toast ==== 'function') {
      window.toast('pin failed');
    }
    return null;
  }
}
