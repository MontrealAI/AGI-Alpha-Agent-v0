// SPDX-License-Identifier: Apache-2.0
export interface ReplayDelta {
  [key: string]: any;
}

export interface ReplayFrame {
  id: number;
  parent: number | null;
  delta: ReplayDelta;
  timestamp: number;
}

async function sha256Hex(data: Uint8Array): Promise<string> {
  if (globalThis.crypto?.subtle) {
    const hash = await globalThis.crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }
  const crypto = await import('crypto');
  return crypto.createHash('sha256').update(data).digest('hex');
}

export class ReplayDB {
  private frames = new Map<number, ReplayFrame>();

  constructor(private name = 'replay') {}

  async open(): Promise<void> {
    return;
  }

  async addFrame(parent: number | null, delta: ReplayDelta): Promise<number> {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    const frame: ReplayFrame = { id, parent, delta, timestamp: Date.now() };
    this.frames.set(id, frame);
    return id;
  }

  async getFrame(id: number): Promise<ReplayFrame | undefined> {
    return this.frames.get(id);
  }

  async exportThread(id: number): Promise<ReplayFrame[]> {
    const out: ReplayFrame[] = [];
    let cur: number | null = id;
    while (cur) {
      const frame = this.frames.get(cur);
      if (!frame) break;
      out.unshift(frame);
      cur = frame.parent;
    }
    return out;
  }

  static async cidForFrames(frames: ReplayFrame[]): Promise<string> {
    const deltas = frames.map((f) => f.delta);
    const buf = new TextEncoder().encode(JSON.stringify(deltas));
    return sha256Hex(buf);
  }

  async computeCid(id: number): Promise<string> {
    const frames = await this.exportThread(id);
    return ReplayDB.cidForFrames(frames);
  }
}
