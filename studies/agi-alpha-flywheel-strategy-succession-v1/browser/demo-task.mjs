// SPDX-License-Identifier: Apache-2.0
// Public synthetic demonstration input, separate from all confirmatory tasks.
export const TASK_LABELS = Object.freeze({
    J1: 'Scope the release',
    J2: 'Build the API',
    J3: 'Build the interface',
    J4: 'Prepare test data',
    J5: 'Check the service',
    J6: 'Check the interface',
    J7: 'Integration tests',
    J8: 'Write release notes',
    J9: 'Release review',
});

export function initialTask() {
    return {
        schema: 'release-plan/v1',
        id: 'browser-release-example',
        kind: 'plan',
        jobs: [
            {id: 'J1', duration: 3, crew: 1, deps: []},
            {id: 'J2', duration: 8, crew: 2, deps: ['J1']},
            {id: 'J3', duration: 6, crew: 1, deps: ['J1']},
            {id: 'J4', duration: 3, crew: 1, deps: ['J1']},
            {id: 'J5', duration: 4, crew: 2, deps: ['J2', 'J4']},
            {id: 'J6', duration: 3, crew: 1, deps: ['J3', 'J4']},
            {id: 'J7', duration: 5, crew: 2, deps: ['J5', 'J6']},
            {id: 'J8', duration: 3, crew: 1, deps: ['J2', 'J3']},
            {id: 'J9', duration: 2, crew: 1, deps: ['J7', 'J8']},
        ],
        capacity: Array(64).fill(3),
        release: {},
        locked: {},
        deadline: 28,
        public_or_synthetic: 'synthetic',
        planning_only: true,
    };
}
