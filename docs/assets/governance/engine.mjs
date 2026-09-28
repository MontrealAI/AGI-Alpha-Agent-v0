// SPDX-License-Identifier: Apache-2.0
// Exact integer counterpart of solving_agi_governance/workbench.py.
import model from "./constants.mjs?v=1.14.0";
export const SCHEMA = "agialpha.governance.scenario.v1";
export const REPORT_SCHEMA = "agialpha.governance.dossier.v1";
export const MAX_BYTES = 256000;
export const FEMTO = 1e15;
export function canonical(value) {
    if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
    if (value && typeof value === "object")
        return (
            "{" +
            Object.keys(value)
                .sort()
                .map((k) => JSON.stringify(k) + ":" + canonical(value[k]))
                .join(",") +
            "}"
        );
    return JSON.stringify(value);
}
export async function digest(value) {
    return hashBytes(new TextEncoder().encode(canonical(value)));
}
export async function hashBytes(bytes) {
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash), (b) =>
        b.toString(16).padStart(2, "0"),
    ).join("");
}
export function parse(text) {
    if (
        typeof text !== "string" ||
        new TextEncoder().encode(text).length > MAX_BYTES
    )
        throw Error(`Input exceeds ${MAX_BYTES} bytes`);
    const result = JSON.parse(text),
        stack = [];
    const tokens =
        text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^{}\[\]:,\s]+/g) || [];
    for (const token of tokens) {
        if (token === "{" || token === "[") {
            stack.push({
                object: token === "{",
                keys: new Set(),
                expect: true,
            });
            if (stack.length > 24) throw Error("JSON nesting is too deep");
        } else if (token === "}" || token === "]") stack.pop();
        else if (token === ",") {
            if (stack.at(-1)?.object) stack.at(-1).expect = true;
        } else if (
            stack.at(-1)?.object &&
            stack.at(-1).expect &&
            token.startsWith('"')
        ) {
            const key = JSON.parse(token),
                frame = stack.at(-1);
            if (frame.keys.has(key)) throw Error(`Duplicate JSON key: ${key}`);
            frame.keys.add(key);
            frame.expect = false;
        }
    }
    return result;
}
function keys(value, expected, label) {
    if (
        !value ||
        typeof value !== "object" ||
        Array.isArray(value) ||
        canonical(Object.keys(value).sort()) !== canonical([...expected].sort())
    )
        throw Error(
            `${label} must contain exactly: ${[...expected].sort().join(", ")}`,
        );
}
function integer(value, low, high, label) {
    if (!Number.isSafeInteger(value) || value < low || value > high)
        throw Error(`${label} must be an integer from ${low} through ${high}`);
}
function text(value, label, maximum = 160) {
    if (
        typeof value !== "string" ||
        !value.trim() ||
        [...value].length > maximum
    )
        throw Error(
            `${label} must be nonempty text of at most ${maximum} characters`,
        );
    if (/[\u0000-\u001f\ud800-\udfff]/u.test(value))
        throw Error(`${label} contains invalid Unicode or control characters`);
}
export function validate(source) {
    keys(
        source,
        [
            "schema",
            "id",
            "title",
            "note",
            "incentives",
            "risk",
            "policy",
            "upgrade",
            "validators",
        ],
        "Scenario",
    );
    if (source.schema !== SCHEMA)
        throw Error("Unsupported governance scenario schema");
    if (
        typeof source.id !== "string" ||
        !/^[a-z][a-z0-9-]{0,39}$/.test(source.id)
    )
        throw Error(
            "Scenario id must use 1–40 lowercase letters, digits or hyphens, starting with a letter",
        );
    text(source.title, "Title");
    text(source.note, "Source note", 500);
    for (const [section, fields] of Object.entries(model.bounds)) {
        keys(
            source[section],
            [
                ...Object.keys(fields),
                ...(section === "upgrade"
                    ? ["paused", "proposedPolicyHash", "expectedPolicyHash"]
                    : []),
            ],
            section,
        );
        for (const [field, [low, high]] of Object.entries(fields))
            integer(source[section][field], low, high, `${section}.${field}`);
    }
    const i = source.incentives,
        u = source.upgrade;
    if (!(i.temptation > i.reward && i.reward > i.punishment))
        throw Error("Payoffs must satisfy temptation > reward > punishment");
    if (u.now < u.queuedAt)
        throw Error("Current time cannot precede the queue timestamp");
    if (typeof u.paused !== "boolean") throw Error("Paused must be a boolean");
    for (const name of ["proposedPolicyHash", "expectedPolicyHash"])
        if (typeof u[name] !== "string" || !/^[0-9a-f]{64}$/.test(u[name]))
            throw Error(`${name} must be 64 lowercase hexadecimal characters`);
    if (
        !Array.isArray(source.validators) ||
        source.validators.length < 1 ||
        source.validators.length > 64
    )
        throw Error("Use 1–64 validator records");
    const names = new Set();
    for (const v of source.validators) {
        keys(
            v,
            [
                "name",
                "controller",
                "credits",
                "votes",
                "stakeTokens",
                "eligible",
            ],
            "Validator",
        );
        if (
            typeof v.name !== "string" ||
            !/^[a-z][a-z0-9-]{0,39}\.alpha\.club\.agi\.eth$/.test(v.name)
        )
            throw Error(
                "Validator names must be lowercase name.alpha.club.agi.eth",
            );
        if (names.has(v.name)) throw Error("Duplicate validator name");
        names.add(v.name);
        if (
            typeof v.controller !== "string" ||
            !/^[a-z][a-z0-9-]{0,39}$/.test(v.controller)
        )
            throw Error(
                "Controller ids must use 1–40 lowercase letters, digits or hyphens",
            );
        integer(v.credits, 0, 1000000, "Voting credits");
        integer(v.votes, -1000, 1000, "Votes");
        integer(v.stakeTokens, 0, 1000000, "Validator stake");
        if (typeof v.eligible !== "boolean")
            throw Error("Eligible must be a boolean");
    }
    return structuredClone(source);
}
export async function evaluate(source) {
    source = validate(source);
    const { incentives: i, risk: r, policy: p, upgrade: u } = source;
    const electorate = source.validators.filter(
        (v) => v.eligible && v.stakeTokens >= p.minStakeTokens,
    );
    const controllers = electorate.map((v) => v.controller);
    const duplicates = [
        ...new Set(
            controllers.filter((c, index) => controllers.indexOf(c) !== index),
        ),
    ].sort();
    const invalid = electorate
        .filter((v) => v.votes ** 2 > v.credits)
        .map((v) => v.name);
    const ballots = electorate.filter(
        (v) => v.votes !== 0 && v.votes ** 2 <= v.credits,
    );
    const sum = (values) => values.reduce((a, b) => a + b, 0);
    const yes = sum(ballots.map((v) => Math.max(0, v.votes))),
        no = sum(ballots.map((v) => Math.max(0, -v.votes)));
    const margin =
        BigInt(i.reward) * 100000000n -
        (10000n - BigInt(i.discountBps)) *
            (BigInt(i.temptation) * 10000n -
                BigInt(i.detectionBps) * BigInt(i.stake)) -
        BigInt(i.discountBps) * BigInt(i.punishment) * 10000n;
    const exposure = BigInt(r.perActionFemto) * BigInt(r.actions),
        bound = exposure < BigInt(FEMTO) ? Number(exposure) : FEMTO;
    const unlock = u.queuedAt + u.delaySeconds;
    const passed = {
        identity: electorate.length > 0 && duplicates.length === 0,
        credits: invalid.length === 0,
        quorum:
            electorate.length > 0 &&
            ballots.length * 10000 >= electorate.length * p.quorumBps,
        mandate: yes > no && yes * 10000 >= (yes + no) * p.supportBps,
        incentives: margin >= 0n,
        risk: bound <= r.budgetFemto,
        timelock: u.now >= unlock,
        policy: u.proposedPolicyHash === u.expectedPolicyHash,
        pause: !u.paused,
    };
    const gates = model.gates.map(([id, title, nextStep]) => ({
        id,
        title,
        passed: passed[id],
        nextStep,
    }));
    const inputSha256 = await digest(source);
    const jobs = model.gates.map(([, title, step]) => ({
        goal: `Governance verification: ${title}. Input SHA-256: ${inputSha256}`,
        successMetric: step,
        bounty: String(BigInt(p.jobBountyTokens) * 10n ** 18n),
        duration: 604800,
        priceWeight: 5000,
    }));
    const result = {
        status: Object.values(passed).every(Boolean)
            ? "REVIEW_REQUIRED"
            : "BLOCKED",
        inputSha256,
        gates,
        ballot: {
            eligible: electorate.length,
            participants: ballots.length,
            yes,
            no,
            creditsSpent: sum(ballots.map((v) => v.votes ** 2)),
            duplicateControllers: duplicates,
            overBudget: invalid,
        },
        incentives: {
            marginNumerator: String(margin),
            marginDenominator: 100000000,
            condition: "R >= (1-delta)*(T-detection*stake) + delta*P",
        },
        risk: {
            exposureFemto: String(exposure),
            unionBoundFemto: bound,
            maxPerActionFemto: Number(
                BigInt(r.budgetFemto) / BigInt(r.actions),
            ),
        },
        upgrade: {
            unlockAt: unlock,
            secondsRemaining: Math.max(0, unlock - u.now),
        },
        jobs,
        reservedBountyTokens: jobs.length * p.jobBountyTokens,
        scope: model.scope,
    };
    const report = { schema: REPORT_SCHEMA, input: source, result };
    return { ...report, sha256: await digest(report) };
}
export async function verify(report) {
    keys(report, ["schema", "input", "result", "sha256"], "Dossier");
    const expected = await evaluate(report.input);
    if (canonical(report) !== canonical(expected))
        throw Error(
            "Dossier differs from recomputation; supplied results are not trusted",
        );
    return expected;
}
function markdownText(value) {
    return value.replace(/([\\`*_{}\[\]<>()#+.!|])/g, "\\$1");
}
export function brief(report) {
    const { input: source, result } = report;
    const lines = [
        `# ${markdownText(source.title)}`,
        "",
        `Status: ${result.status}`,
        `Source note: ${markdownText(source.note)}`,
        "",
    ];
    for (const gate of result.gates)
        lines.push(
            `- ${gate.passed ? "PASS (model)" : "BLOCKED"}: ${gate.title}`,
            `  Review: ${gate.nextStep}`,
        );
    lines.push(
        "",
        `Unsubmitted verification bounties: ${result.reservedBountyTokens} AGIALPHA.`,
        "",
        "Model: infinite repeated play, stationary payoffs, risk-neutral agents, credible grim-trigger punishment, and detected unilateral deviation slashed once. It is a conditional incentive check, not uniqueness.",
        "Risk: min(1, action count × per-action upper bound). No independence assumption or unverified mitigation credit.",
        "The supplied identity roster, risk bounds, policy hashes and clock still need authoritative verification.",
        "",
        model.scope,
        "",
        `Dossier SHA-256: ${report.sha256}`,
        "",
    );
    return lines.join("\n");
}
export async function artifacts(report) {
    report = await verify(report);
    const values = {
        "scenario.json": canonical(report.input) + "\n",
        "dossier.json": canonical(report) + "\n",
        "jobs.json": canonical(report.result.jobs) + "\n",
        "review-brief.md": brief(report),
    };
    const checksums = [];
    for (const name of Object.keys(values).sort())
        checksums.push(
            `${await hashBytes(new TextEncoder().encode(values[name]))}  ${name}\n`,
        );
    values.SHA256SUMS = checksums.join("");
    return values;
}
