// SPDX-License-Identifier: Apache-2.0
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { performance } from "node:perf_hooks";

const base = dirname(fileURLToPath(import.meta.url));
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const readJson = async (path) => JSON.parse(await readFile(resolve(base, path), "utf8"));
const digestFile = async (path) => sha256(await readFile(resolve(base, path)));
const lock = await readJson("scenario-source-lock.json");
const started = new Date().toISOString();
const start = performance.now();
const checked = [];

for (const entry of lock.files) {
    const data = await readFile(resolve(base, entry.local_path));
    assert.equal(data.byteLength, entry.bytes);
    assert.equal(sha256(data), entry.sha256);
    checked.push({ path: entry.local_path, sha256: entry.sha256 });
}
for (const entry of [lock.input, lock.candidate_record, lock.existing_source_lock]) {
    assert.equal(await digestFile(entry.path), entry.sha256);
    checked.push({ path: entry.path, sha256: entry.sha256 });
}

const input = await readJson("scenario-input.json");
assert.equal(input.budget, 7);
assert.equal(input.risk_limit, 0);
assert.equal(input.unit, "supplied flagship eligibility units");
assert.equal(input.opportunities.length, 7);
for (const item of input.opportunities) {
    assert.equal(item.cost, 1);
    assert.equal(item.value, 0);
    assert.equal(item.risk, 0);
    assert.deepEqual(item.effort, [1, 1, 1]);
}

const { analyseScenario, makeGenome } = await import("./scenario-upstream/docs/assets/ascension/engine.mjs");
const analysis = analyseScenario(input);
assert.deepEqual(analysis.selected, []);
assert.deepEqual(analysis.portfolio.evidence.selected, []);
assert.deepEqual(analysis.portfolio.evidence.totals, { cost: 0, risk: 0, value: 0 });
assert.equal(analysis.portfolio.evidence.examined_subsets, 128);
assert.equal(analysis.schedule, null);
assert.equal(analysis.missions.schedule, null);
assert.deepEqual(analysis.frontier, input.opportunities.map((item) => item.id));
for (const citation of analysis.research.evidence.citations) {
    assert.ok(input.opportunities.find((item) => item.id === citation.source_id).evidence.includes(citation.quote));
}
assert.deepEqual(analysis.scenario, input);

let refusal;
try {
    const genome = makeGenome(analysis);
    refusal = { refused: false, genome };
} catch (error) {
    refusal = { refused: true, error_name: error.name, message: error.message };
}
assert.equal(refusal.refused, true);
assert.equal(refusal.message, "Increase the budget or risk allowance to select a feasible project.");
refusal.interpretation = "Expected native refusal for empty selection. The generic error suggestion is not followed: all seven candidates already fit budget, and all supplied flagship eligibility values are zero.";
refusal.budget_changed = false;
refusal.risk_allowance_changed = false;
refusal.venture_genome_created = false;
refusal.research_seed_boundary = "A separate research artifact may preserve negative findings; this refusal does not authorize a venture genome, mint, listing, trade or transfer.";

const outputDir = resolve(base, "results/scenario-v1");
await mkdir(outputDir, { recursive: true });
const outputs = [];
for (const [name, data] of [["analysis.json", analysis], ["genome_refusal.json", refusal]]) {
    const bytes = JSON.stringify(data, null, 2) + "\n";
    await writeFile(resolve(outputDir, name), bytes);
    outputs.push({ path: `results/scenario-v1/${name}`, sha256: sha256(bytes) });
}
assert.equal(await digestFile(lock.existing_source_lock.path), lock.existing_source_lock.sha256);
const manifest = {
    schema: "agialpha.study.scenario-run.v1",
    started_utc: started,
    node_version: process.version,
    elapsed_seconds: (performance.now() - start) / 1000,
    upstream_commit: lock.commit,
    source_manifest_sha256: await digestFile("scenario-source-lock.json"),
    runner_sha256: await digestFile("run_scenario.mjs"),
    input_provenance_sha256: await digestFile("scenario-input-provenance.json"),
    verified_inputs: checked,
    outputs,
    selected_count: analysis.selected.length,
    examined_subsets: analysis.portfolio.evidence.examined_subsets,
    quoted_passages: analysis.research.evidence.citations.length,
    genome_refused: refusal.refused,
    existing_source_lock_unchanged: true,
    evidence_boundary: "Actual deterministic execution of unchanged upstream code on reviewer-supplied candidate verdicts. Keyword ranking is not autonomous discovery or semantic novelty review. Numeric parameters are eligibility routing assumptions, not economics or safety measurements. No venture promotion or on-chain action.",
    frontier_boundary: "All seven points tie on supplied coordinates, so all remain nondominated in this numeric frontier. Frontier membership is not selection, approval or evidence of novelty.",
};
await writeFile(resolve(outputDir, "run_manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
process.stdout.write(JSON.stringify({
    selected: analysis.selected,
    examined_subsets: manifest.examined_subsets,
    supplied_evidence_passages: manifest.quoted_passages,
    genome_refusal: refusal.message,
    existing_source_lock_unchanged: true,
    output_directory: outputDir,
}, null, 2) + "\n");
