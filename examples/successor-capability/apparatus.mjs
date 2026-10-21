// SPDX-License-Identifier: Apache-2.0
/** Public synthetic apparatus contracts. These contain no response law or final cases. */
export const APPARATUS_SCHEMA = 'out-evolve-apparatus/v1';
export const TOPOLOGIES = Object.freeze(['shielded', 'routed', 'referenced']);

function primitive(id, phase, kind, target, cost, gain = 1, requires = []) {
    const effects = {
        shield: ['installed'], route: ['installed'], sensor: ['installed'],
        attenuate: ['nuisance', 'transfer'], reference: ['observations'], destroy: ['productive']
    }[kind];
    return {id, phase, kind, target, gain, cost, requires, effects,
        support: {scopes: ['standard', 'reservoir'], boundedGain: gain}};
}

export function apparatus(topology = 'shielded', expanded = false) {
    if (!TOPOLOGIES.includes(topology)) throw Error('Unknown synthetic topology.');
    const channel = (id, initial = 8, drift = 2, cap = 16, scopes = ['standard', 'reservoir']) =>
        ({id, initial, drift, cap, scopes});
    const edge = (id, from, to, gain = 1) => ({id, from, to, gain});
    let channels, edges, primitives;
    if (topology === 'shielded') {
        channels = [channel('residual')];
        edges = [edge('residual-readout', 'residual', 'readout')];
        primitives = [primitive('protect-residual', 'install', 'shield', 'residual', 4),
            primitive('flush-residual', 'prepare', 'attenuate', 'residual', 1, 0),
            primitive('halve-residual', 'prepare', 'attenuate', 'residual', 1, 0.5),
            primitive('route-residual', 'install', 'route', 'residual-readout', 20),
            primitive('sense-residual', 'install', 'sensor', 'residual', 18),
            primitive('reference-residual', 'prepare', 'reference', 'residual', 1, 1, ['sense-residual'])];
    } else if (topology === 'routed') {
        channels = [channel('left'), channel('right', 6, 3), channel('junction', 0, 0)];
        edges = [edge('left-junction', 'left', 'junction'), edge('right-junction', 'right', 'junction'),
            edge('junction-readout', 'junction', 'readout')];
        primitives = [primitive('route-junction', 'install', 'route', 'junction-readout', 5)];
        for (const id of ['left', 'right']) primitives.push(
            primitive(`protect-${id}`, 'install', 'shield', id, 5),
            primitive(`flush-${id}`, 'prepare', 'attenuate', id, 1, 0),
            primitive(`sense-${id}`, 'install', 'sensor', id, 8),
            primitive(`reference-${id}`, 'prepare', 'reference', id, 1, 1, [`sense-${id}`]));
    } else {
        channels = [channel('common', 12, 4, 24), channel('local', 1, 0, 4)];
        edges = [edge('common-readout', 'common', 'readout'), edge('local-readout', 'local', 'readout', 0.5)];
        primitives = [primitive('sense-common', 'install', 'sensor', 'common', 2),
            primitive('reference-common', 'prepare', 'reference', 'common', 1, 1, ['sense-common']),
            primitive('protect-common', 'install', 'shield', 'common', 12),
            primitive('flush-common', 'prepare', 'attenuate', 'common', 2, 0),
            primitive('route-common', 'install', 'route', 'common-readout', 18),
            primitive('flush-local', 'prepare', 'attenuate', 'local', 1, 0),
            primitive('halve-local', 'prepare', 'attenuate', 'local', 1, 0.5)];
    }
    channels.push(channel('reservoir', 10, 3, 20, ['reservoir']));
    edges.push(edge('reservoir-readout', 'reservoir', 'readout'));
    primitives.push(primitive('protect-reservoir', 'install', 'shield', 'reservoir', 4),
        primitive('flush-reservoir', 'prepare', 'attenuate', 'reservoir', 1, 0),
        primitive('sense-reservoir', 'install', 'sensor', 'reservoir', 9),
        primitive('reference-reservoir', 'prepare', 'reference', 'reservoir', 1, 1, ['sense-reservoir']),
        primitive('erase-product', 'prepare', 'destroy', 'productive', 0, 0));
    return {schema: APPARATUS_SCHEMA, id: `synthetic-${topology}${expanded ? '-expanded' : ''}`,
        channels, edges, scope: expanded ? ['standard', 'reservoir'] : ['standard'], tolerance: 0,
        primitives, limits: {maxInstructions: 32, maxRepeat: 16, maxCost: 1_000_000, maxCycles: 1024}};
}

export function expandApparatus(input) {
    const result = JSON.parse(JSON.stringify(input));
    // The scope is identity-bound separately; preserve long valid IDs rather than
    // overflowing the public 80-character contract or truncating distinct labels.
    if (!result.id.endsWith('-expanded') && result.id.length <= 71) result.id += '-expanded';
    result.scope = ['standard', 'reservoir'];
    return result;
}
