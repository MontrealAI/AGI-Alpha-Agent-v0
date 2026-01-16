// SPDX-License-Identifier: Apache-2.0
export function save(pop, rngState) {
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

export function load(json) {
  let data;
  try {
    data = JSON.parse(json);
  } catch (err) {
    throw new Error(`Malformed JSON: ${err.message}`);
  }

  if (data === null || typeof data !== "object") {
    throw new Error("Invalid data");
  }

  const allowedRoot = new Set(["gen", "pop", "rngState"]);
  for (const key of Object.keys(data)) {
    if (!allowedRoot.has(key)) {
      throw new Error(`Unexpected key: ${key}`);
    }
  }

  if (!Array.isArray(data.pop)) throw new Error("Invalid population");

  const allowedItem = new Set(["logic", "feasible", "front", "strategy"]);
  const pop = data.pop.map((d) => {
    if (d === null || typeof d !== "object") {
      throw new Error("Invalid population item");
    }
    for (const key of Object.keys(d)) {
      if (!allowedItem.has(key)) {
        throw new Error(`Invalid key in population item: ${key}`);
      }
    }
    if (typeof d.logic !== "number" || typeof d.feasible !== "number") {
      throw new Error("Population items require numeric logic and feasible");
    }
    return {
      logic: d.logic,
      feasible: d.feasible,
      front: d.front,
      strategy: d.strategy,
    };
  });
  const gen = typeof data.gen === "number" ? data.gen : 0;
  pop.gen = gen;
  return { pop, rngState: data.rngState, gen };
}
