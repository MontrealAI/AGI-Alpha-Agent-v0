// SPDX-License-Identifier: Apache-2.0
/** Declarations describe the bounded data interface, not permission to execute external tasks. */
export type Cost = number | null;
export interface Variable { id: string; domain: number[] }
export interface Factor { id: string; scope: string[]; costs: Cost[] }
export interface FiniteModel {
    schema: 'out-execute-finite-model/v1';
    semantics: 'finite-nonnegative-integer-min-sum/v1';
    variables: Variable[];
    factors: Factor[];
}
export interface SourceIdentity {
    compilerSha256: string;
    checkerSha256: string;
    evaluatorVersion: 'out-execute-independent-enumeration/v1';
}
export interface Module { id: string; private: string[]; interface: string[]; factorIds: string[] }
export interface BoundaryRow { boundary: number[]; cost: Cost; witness: number[] | null }
export interface Contract {
    schema: 'out-execute-boundary-contract/v1';
    compilerVersion: 'out-execute-finite-compiler/v1';
    checkerVersion: 'out-execute-independent-enumeration/v1';
    module: Module; model: FiniteModel; rows: BoundaryRow[]; digest: string;
}
export interface Decomposition { boundary: string[]; boundaryFactors: string[]; modules: Module[] }
export interface SelectionPolicy { maxBoundary: 0 | 1 | 2 | 3; shortlist: string[] | null; horizon: number }
export interface BoundarySelector {
    decomposition: Decomposition; proxy: number; inspected: number; scopeVisits: number; policy: SelectionPolicy;
}
export type WorkCounter = 'inputEntries' | 'boundaryCandidates' | 'scopeVisits' | 'constructionAssignments'
    | 'constructionFactorLookups' | 'qualificationAssignments' | 'qualificationFactorLookups'
    | 'reuseAuditAssignments' | 'reuseAuditFactorLookups' | 'reuseAuditInputEntries' | 'reuseAuditBoundaryCandidates'
    | 'reuseAuditScopeVisits' | 'reuseAuditProfileComparisons' | 'boundaryAssignments' | 'profileLookups' | 'boundaryFactorLookups'
    | 'outputFactorLookups' | 'materializedValues' | 'profileComparisons' | 'acceptanceBoundaryAssignments'
    | 'acceptanceProfileLookups' | 'acceptanceFactorLookups';
export type Ledger = Record<WorkCounter, number>;
export interface ChangePlan { retained: string[]; invalidated: {module: string; reason: string}[]; removed: string[] }
export interface Completion {
    schema: 'out-execute-completion/v1'; attemptId: string; source: SourceIdentity; model: FiniteModel;
    selector: BoundarySelector; decomposition: Decomposition; contracts: Contract[];
    selection: {status: 'OPTIMAL' | 'INFEASIBLE'; boundary: Record<string, number> | null; cost: Cost};
    artifact: Record<string, number> | null; change: ChangePlan & {rebuilt: string[]; semanticStop: boolean};
    work: Ledger; countedWork: number; budget: number; parentDigest: string | null; cumulativeCountedWork: number;
    evidence: {scope: 'supplied-finite-model-only'; sourceAuthenticity: 'not-established'; authority: [];
        paymentRoute: 'none'; excludedCosts: string[]}; digest: string;
}
export interface Archive { schema: 'out-execute-archive/v1'; completions: Completion[] }
export interface Checkpoint {
    schema: 'out-execute-checkpoint/v1'; attemptId: string; source: SourceIdentity; model: FiniteModel;
    selection: BoundarySelector; archive: Archive; budget: number; plan: ChangePlan;
    contracts: (Contract | null)[]; next: number; work: Ledger;
    status: 'PAUSED' | 'CANCELLED' | 'INCONCLUSIVE' | 'COMPLETE'; reason: string | null; completion: Completion | null;
}
export interface ExecutionOptions { source: SourceIdentity; archive?: Archive | null; selection?: SelectionPolicy;
    budget?: number; attemptId?: string }
export function startExecution(model: FiniteModel, options: ExecutionOptions): Promise<Checkpoint>;
export function advanceExecution(checkpoint: Checkpoint, options?: {modules?: number; cancel?: boolean}): Promise<Checkpoint>;
export function execute(model: FiniteModel, options: ExecutionOptions): Promise<Checkpoint>;
export function restoreExecution(input: Checkpoint): Promise<{checkpoint: Checkpoint; verificationWork: Ledger;
    countedVerificationWork: number; scope: 'additional-import-verification-not-in-frozen-completion-cost'}>;
export function retainCompletion(checkpoint: Checkpoint): Promise<Archive>;
