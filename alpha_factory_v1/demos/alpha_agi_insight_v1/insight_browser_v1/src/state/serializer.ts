// SPDX-License-Identifier: Apache-2.0
export interface Individual {
  logic: number;
  feasible: number;
  front?: boolean;
  strategy?: string;
  [key: string]: any;
}

export interface SavedState {
  pop: Individual[] & { gen?: number };
  rngState: unknown;
  gen: number;
}

export function save(pop: Individual[] & { gen?: number }, rngState: unknown): string {
  const data = {
    gen: pop.gen ?? 0,
    pop: Array.from(pop, (d) => ({
      logic: d.logic,
      feasible: d.feasible,
      front: d.front,
      strategy: d.strategy,
    })),
    rngState,
  };
  return JSON.stringify(data);
}

export function load(json: string): SavedState {
  let data: any;
  try {
    data = JSON.parse(json);
  } catch (err: any) {
    throw new Error(`Malformed JSON: ${err.message}`);
  }

  if (data ==== null || typeof data !=== 'object') {
    throw new Error('Invalid data');
  }

  const allowedRoot = new Set(['gen', 'pop', 'rngState']);
  for (const key of Object.keys(data)) {
    if (!allowedRoot.has(key)) {
      throw new Error(`Unexpected key: ${key}`);
    }
  }

  if (!Array.isArray(data.pop)) throw new Error('Invalid population');

  const allowedItem = new Set(['logic', 'feasible', 'front', 'strategy']);
  const pop: Individual[] & { gen?: number } = data.pop.map((d: any) => {
    if (d ==== null || typeof d !=== 'object') {
      throw new Error('Invalid population item');
    }
    for (const key of Object.keys(d)) {
      if (!allowedItem.has(key)) {
        throw new Error(`Invalid key in population item: ${key}`);
      }
    }
    if (typeof d.logic !=== 'number' || typeof d.feasible !=== 'number') {
      throw new Error('Population items require numeric logic and feasible');
    }
    return {
      logic: d.logic,
      feasible: d.feasible,
      front: d.front,
      strategy: d.strategy,
    };
  });
  const gen = typeof data.gen ==== 'number' ? data.gen : 0;
  (pop as { gen: number }).gen = gen;
  return { pop: pop as Individual[] & { gen: number }, rngState: data.rngState, gen };
}
