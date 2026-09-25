// SPDX-License-Identifier: Apache-2.0
// Executable white-paper models. Inputs are scenario assumptions, not live market observations.
import { runMission } from "../portal/mission-engine.mjs";

const requireThat = (condition, message) => {
    if (!condition) throw new Error(message);
};
const finite = (value, name, min = 0, max = 1e9) => {
    requireThat(
        typeof value === "number" &&
            Number.isFinite(value) &&
            value >= min &&
            value <= max,
        `${name} must be a finite number from ${min} to ${max}.`,
    );
    return value;
};
const integer = (value, name, min = 0, max = 1e9) => {
    finite(value, name, min, max);
    requireThat(Number.isSafeInteger(value), `${name} must be a whole number.`);
    return value;
};
const text = (value, name, max = 2000) => {
    requireThat(
        typeof value === "string" &&
            value.trim().length > 0 &&
            value.length <= max,
        `${name} needs 1–${max} characters.`,
    );
    return value;
};
const sum = (values) => values.reduce((a, b) => a + b, 0);
const UNIT = 10n ** 18n;
const MAX_UNITS = 2n ** 256n - 1n;

export function tokenUnits(value) {
    requireThat(
        typeof value === "string" &&
            /^(0|[1-9]\d{0,59})(\.\d{1,18})?$/.test(value),
        "Token amounts need an unsigned decimal string with at most 18 decimal places.",
    );
    const [whole, fraction = ""] = value.split(".");
    const units = BigInt(whole) * UNIT + BigInt(fraction.padEnd(18, "0"));
    requireThat(units <= MAX_UNITS, "Token amount exceeds uint256.");
    return units;
}

export function tokenDecimal(units) {
    requireThat(
        typeof units === "bigint" && units >= 0n && units <= MAX_UNITS,
        "Invalid token base units.",
    );
    const fraction = (units % UNIT)
        .toString()
        .padStart(18, "0")
        .replace(/0+$/, "");
    return (units / UNIT).toString() + (fraction ? `.${fraction}` : "");
}

export function validateScenario(input) {
    requireThat(
        input && typeof input === "object" && !Array.isArray(input),
        "Import a scenario object.",
    );
    requireThat(
        JSON.stringify(input).length <= 150000,
        "Scenario exceeds 150 KB.",
    );
    const s = structuredClone(input);
    requireThat(
        s.schema === "agialpha.ascension.scenario.v1",
        "Unsupported scenario schema.",
    );
    text(s.id, "Scenario ID", 64);
    text(s.title, "Scenario title", 120);
    text(s.goal, "Mission goal", 1000);
    text(s.description, "Scenario description", 2000);
    text(s.unit, "Value unit", 60);
    integer(s.budget, "Budget", 1, 1000000);
    integer(s.risk_limit, "Risk allowance", 0, 70000);
    requireThat(
        Array.isArray(s.opportunities) &&
            s.opportunities.length >= 1 &&
            s.opportunities.length <= 7,
        "An Ascension mission needs 1–7 opportunities.",
    );
    const ids = new Set();
    for (const item of s.opportunities) {
        requireThat(
            typeof item.id === "string" &&
                /^[a-zA-Z0-9_-]{1,64}$/.test(item.id),
            "Opportunity IDs must be short letters, digits or dashes.",
        );
        requireThat(!ids.has(item.id), "Opportunity IDs must be unique.");
        ids.add(item.id);
        text(item.title, "Opportunity title", 120);
        text(item.sector, "Sector", 60);
        text(item.evidence, "Source note", 10000);
        integer(item.cost, "Project cost", 1, 1000000);
        integer(item.value, "Assumed project value", 0, 1000000);
        integer(item.risk, "Project risk score", 0, 10000);
        requireThat(
            Array.isArray(item.effort) && item.effort.length === 3,
            "Each project needs research, delivery and verification effort.",
        );
        item.effort.forEach((n) => integer(n, "Task duration", 1, 1000));
    }
    return s;
}

export function analyseScenario(input, overrides = {}) {
    const scenario = validateScenario({ ...input, ...overrides });
    const allocationMission = {
        goal: scenario.goal,
        work: {
            kind: "allocation",
            budget: scenario.budget,
            max_risk: scenario.risk_limit,
            unit: scenario.unit,
            items: scenario.opportunities.map(({ id, cost, value, risk }) => ({
                id,
                cost,
                value,
                risk,
            })),
        },
    };
    const portfolio = runMission(allocationMission);
    const selected = scenario.opportunities.filter((item) =>
        portfolio.evidence.selected.includes(item.id),
    );
    const researchMission = {
        goal: scenario.goal,
        work: {
            kind: "research",
            sources: scenario.opportunities.map((item) => ({
                id: item.id,
                title: item.title,
                text: item.evidence,
            })),
        },
    };
    const research = runMission(researchMission);
    const scheduleMission = selected.length
        ? {
              goal: `Coordinate research, delivery and verification for ${scenario.title}.`,
              work: {
                  kind: "schedule",
                  jobs: selected.map((item) => ({
                      id: item.id,
                      due: 10000,
                      operations: ["research", "delivery", "verification"].map(
                          (machine, i) => ({
                              machine,
                              duration: item.effort[i],
                          }),
                      ),
                  })),
              },
          }
        : null;
    const schedule = scheduleMission ? runMission(scheduleMission) : null;
    const frontier = scenario.opportunities.filter(
        (a) =>
            !scenario.opportunities.some(
                (b) =>
                    b.id !== a.id &&
                    b.cost <= a.cost &&
                    b.risk <= a.risk &&
                    b.value >= a.value &&
                    (b.cost < a.cost || b.risk < a.risk || b.value > a.value),
            ),
    );
    return {
        schema: "agialpha.ascension.analysis.v1",
        scenario,
        portfolio,
        selected,
        research,
        schedule,
        frontier: frontier.map((item) => item.id),
        missions: {
            allocation: allocationMission,
            research: researchMission,
            schedule: scheduleMission,
        },
    };
}

export function makeGenome(analysis) {
    requireThat(
        analysis.selected.length > 0,
        "Increase the budget or risk allowance to select a feasible project.",
    );
    return {
        schema: "agialpha.novaseed.genome.v1",
        title: analysis.scenario.title,
        goal: analysis.scenario.goal,
        data_mode: "user_supplied_scenario",
        scenario: structuredClone(analysis.scenario),
        source_notes: analysis.scenario.opportunities.map(
            ({ id, evidence }) => ({ id, evidence }),
        ),
        fusion_plan: {
            selected: analysis.selected,
            schedule: analysis.schedule.evidence,
            missions: analysis.missions,
        },
        assumptions: {
            budget: analysis.scenario.budget,
            risk_limit: analysis.scenario.risk_limit,
            value_unit: analysis.scenario.unit,
        },
        checks: analysis.portfolio.checks.concat(analysis.schedule.checks),
    };
}

// Linear discrete bonding curve: the next lot costs base + slope * outstanding lots.
// Reserve is the exact sum of all issued lot prices. This is a model, not an on-chain exchange.
export function curveQuote({ supply, lots, base, slope, direction = "buy" }) {
    integer(supply, "Outstanding lots", 0, 1000000);
    integer(lots, "Lots", 1, 1000000);
    requireThat(
        direction === "buy" || direction === "sell",
        "Choose buy or sell.",
    );
    if (direction === "sell")
        requireThat(lots <= supply, "Cannot redeem more lots than exist.");
    else
        requireThat(
            supply + lots <= 1000000,
            "The lab supports at most one million outstanding lots.",
        );
    const b = tokenUnits(base),
        m = tokenUnits(slope);
    requireThat(b > 0n, "Base price must be positive.");
    const start = BigInt(direction === "buy" ? supply : supply - lots),
        n = BigInt(lots);
    const units = n * b + (m * n * (2n * start + n - 1n)) / 2n;
    requireThat(units <= MAX_UNITS, "Quote exceeds uint256.");
    return {
        units: units.toString(),
        amount: tokenDecimal(units),
        next_supply: direction === "buy" ? supply + lots : supply - lots,
    };
}

export function councilChecks(analysis) {
    const scenario = validateScenario(analysis.scenario);
    const selected = analysis.selected;
    const authentic =
        new Set(selected.map((item) => item.id)).size === selected.length &&
        selected.every((item) => {
            const source = scenario.opportunities.find(
                (entry) => entry.id === item.id,
            );
            return (
                source &&
                ["cost", "value", "risk"].every(
                    (key) => item[key] === source[key],
                ) &&
                JSON.stringify(item.effort) === JSON.stringify(source.effort)
            );
        });
    const cost = sum(selected.map((item) => item.cost));
    const risk = sum(selected.map((item) => item.risk));
    const operations = analysis.schedule?.evidence.operations || [];
    const totals = analysis.portfolio.evidence.totals;
    const budget =
        authentic &&
        selected.length > 0 &&
        cost <= scenario.budget &&
        risk <= scenario.risk_limit &&
        totals.cost === cost &&
        totals.risk === risk &&
        totals.value === sum(selected.map((item) => item.value));
    let capacity =
        authentic &&
        selected.length > 0 &&
        operations.length === selected.length * 3;
    for (const project of selected) {
        const tasks = operations
            .filter((op) => op.job === project.id)
            .sort((a, b) => a.sequence - b.sequence);
        capacity &&=
            tasks.length === 3 &&
            tasks.every(
                (op, i) =>
                    Number.isSafeInteger(op.start) &&
                    Number.isSafeInteger(op.end) &&
                    op.start >= 0 &&
                    op.sequence === i &&
                    op.machine ===
                        ["research", "delivery", "verification"][i] &&
                    op.end - op.start === project.effort[i] &&
                    (!i || op.start >= tasks[i - 1].end),
            );
    }
    for (let i = 0; i < operations.length; i++) {
        const a = operations[i];
        for (const b of operations.slice(i + 1)) {
            if (a.machine === b.machine && a.end > b.start && b.end > a.start)
                capacity = false;
        }
    }
    return [
        {
            id: "budget-verifier",
            title: "Budget & risk",
            passed: budget,
            detail: `${cost}/${analysis.scenario.budget} cost · ${risk}/${analysis.scenario.risk_limit} risk`,
        },
        {
            id: "capacity-verifier",
            title: "Sequence & capacity",
            passed: capacity,
            detail: `${operations.length} operations checked for order, duration and overlap`,
        },
    ];
}

export class SettlementLab {
    #supply;
    #escrow;
    #treasury = 0n;
    #paid = 0n;
    #burned = 0n;
    #minted = 0n;
    #completed = new Set();
    #events = [];
    #emissionCap;
    #eta;
    #burn;
    constructor({
        deposit,
        emission_cap = "0",
        eta_bps = 9400,
        burn_bps = 100,
    }) {
        this.#escrow = tokenUnits(deposit);
        this.#supply = this.#escrow;
        this.#emissionCap = tokenUnits(emission_cap);
        this.#eta = integer(eta_bps, "Mint coefficient", 0, 10000);
        this.#burn = integer(burn_bps, "Payout burn", 0, 10000);
    }
    settle({ id, gross, certified_value = "0", reviewers }) {
        text(id, "Job ID", 64);
        requireThat(!this.#completed.has(id), "This job was already settled.");
        requireThat(
            Array.isArray(reviewers) &&
                reviewers.length === 2 &&
                reviewers.every((r) => r.passed === true) &&
                new Set(reviewers.map((r) => r.id)).size === 2 &&
                reviewers.every((r) =>
                    ["budget-verifier", "capacity-verifier"].includes(r.id),
                ),
            "Two distinct passing model checks are required.",
        );
        const amount = tokenUnits(gross),
            value = tokenUnits(certified_value);
        requireThat(
            amount > 0n && amount <= this.#escrow,
            "Payout exceeds available escrow or is zero.",
        );
        const burn = (amount * BigInt(this.#burn)) / 10000n;
        const wanted = (value * BigInt(this.#eta)) / 10000n;
        const remaining = this.#emissionCap - this.#minted;
        const mintEach = wanted < remaining / 2n ? wanted : remaining / 2n;
        requireThat(
            this.#supply + 2n * mintEach <= MAX_UNITS,
            "Emission would exceed uint256.",
        );
        this.#escrow -= amount;
        this.#paid += amount - burn + mintEach;
        this.#treasury += mintEach;
        this.#burned += burn;
        this.#minted += 2n * mintEach;
        this.#supply += 2n * mintEach - burn;
        this.#completed.add(id);
        this.#events.push({
            id,
            gross: tokenDecimal(amount),
            burn: tokenDecimal(burn),
            worker: tokenDecimal(amount - burn + mintEach),
            actor_mint: tokenDecimal(mintEach),
            treasury_mint: tokenDecimal(mintEach),
            emission_capped: mintEach < wanted,
        });
        return this.snapshot();
    }
    snapshot() {
        requireThat(
            this.#escrow + this.#paid + this.#treasury === this.#supply,
            "Token conservation failed.",
        );
        return {
            mode: "protocol_simulation",
            decimals: 18,
            escrow: tokenDecimal(this.#escrow),
            workers: tokenDecimal(this.#paid),
            treasury: tokenDecimal(this.#treasury),
            burned: tokenDecimal(this.#burned),
            minted: tokenDecimal(this.#minted),
            supply: tokenDecimal(this.#supply),
            conservation: true,
            settled_jobs: this.#completed.size,
            events: structuredClone(this.#events),
        };
    }
}

export function runSettlement(
    analysis,
    { certified_value = "0", emission_cap = "0", deposit } = {},
) {
    const reviewers = councilChecks(analysis);
    requireThat(
        analysis.selected.length > 0,
        "Select a feasible project before settlement.",
    );
    const ledger = new SettlementLab({
        deposit: deposit ?? String(analysis.scenario.budget),
        emission_cap,
    });
    // Certified value belongs to a completed outcome, not to Insight's optimistic projections.
    analysis.selected.forEach((item, i) =>
        ledger.settle({
            id: item.id,
            gross: String(item.cost),
            reviewers,
            certified_value: i === 0 ? certified_value : "0",
        }),
    );
    return ledger.snapshot();
}

export function stakeDecision({ stake, minimum, severity, attested, name }) {
    const amount = tokenUnits(stake),
        floor = tokenUnits(minimum);
    integer(severity, "Fault severity in basis points", 0, 10000);
    text(name, "Agent identity", 120);
    // The sandbox checks an explicit attestation flag. It does not resolve ENS or verify a wallet.
    const slash = (amount * BigInt(severity)) / 10000n;
    return {
        name,
        eligible: attested === true && amount >= floor,
        slash: tokenDecimal(slash),
        remaining: tokenDecimal(amount - slash),
        mode: "protocol_simulation",
    };
}

export function quadraticBallot(votes, budget) {
    integer(budget, "Voting credit budget", 0, 1000000);
    requireThat(
        Array.isArray(votes) && votes.length >= 1 && votes.length <= 20,
        "Use 1–20 proposal vote allocations.",
    );
    votes.forEach((v) => integer(v, "Votes", -1000, 1000));
    const spent = sum(votes.map((v) => v * v));
    return {
        spent,
        remaining: budget - spent,
        admitted: spent <= budget,
        votes: [...votes],
    };
}

export function upgradeStatus({
    queued_at,
    now,
    delay_days = 8,
    approved,
    policy_valid,
}) {
    integer(queued_at, "Queue timestamp", 0, 8e12);
    integer(now, "Current timestamp", 0, 8e12);
    integer(delay_days, "Delay in days", 8, 365);
    const unlock = queued_at + delay_days * 86400;
    return {
        unlock,
        seconds_remaining: Math.max(0, unlock - now),
        executable: approved === true && policy_valid === true && now >= unlock,
    };
}

export const PAPER_RISKS = [
    {
        id: "R0",
        title: "Specification drift",
        p: 0.22,
        impact: 0.8,
        stake: 0.3,
        formal: 0.45,
        fuzz: 0.4,
        printed: 0.073,
    },
    {
        id: "R1",
        title: "Economic exploit",
        p: 0.18,
        impact: 0.75,
        stake: 0.6,
        formal: 0.2,
        fuzz: 0.35,
        printed: 0.027,
    },
    {
        id: "R2",
        title: "Protocol attack",
        p: 0.1,
        impact: 0.9,
        stake: 0.55,
        formal: 0.7,
        fuzz: 0.5,
        printed: 0.012,
    },
    {
        id: "R3",
        title: "Model misbehavior",
        p: 0.25,
        impact: 0.65,
        stake: 0.25,
        formal: 0.4,
        fuzz: 0.55,
        printed: 0.056,
    },
    {
        id: "R4",
        title: "Societal externality",
        p: 0.08,
        impact: 1,
        stake: 0.35,
        formal: 0.1,
        fuzz: 0.15,
        printed: 0.047,
    },
];

export function riskAudit(rows, threshold = 0.3) {
    finite(threshold, "Risk threshold", 0, 5);
    requireThat(
        Array.isArray(rows) && rows.length >= 1 && rows.length <= 20,
        "Use 1–20 risk rows.",
    );
    const results = rows.map((row) => {
        for (const key of ["p", "impact", "stake", "formal", "fuzz"])
            finite(row[key], key, 0, 1);
        const coverage = 0.4 * row.stake + 0.4 * row.formal + 0.2 * row.fuzz;
        return {
            ...row,
            coverage,
            residual: row.p * row.impact * (1 - coverage),
        };
    });
    const aggregate = sum(results.map((row) => row.residual));
    return {
        rows: results,
        aggregate,
        threshold,
        admitted: aggregate <= threshold,
        interpretation:
            "Sum of normalized scenario risk scores; this is not a catastrophe probability.",
    };
}

export function actionRisk(per_action, actions, target = 0.001) {
    finite(per_action, "Per-action failure probability", 0, 1);
    integer(actions, "Action count", 1, 1e15);
    finite(target, "Risk budget", 0, 1);
    return {
        expected_failures: per_action * actions,
        union_bound: Math.min(1, per_action * actions),
        independent_probability:
            per_action === 0
                ? 0
                : per_action === 1
                  ? 1
                  : -Math.expm1(actions * Math.log1p(-per_action)),
        union_budget_per_action: target / actions,
    };
}

export function replicatorField(matrix, mix) {
    requireThat(
        Array.isArray(matrix) && matrix.length >= 2 && matrix.length <= 5,
        "Use 2–5 strategies.",
    );
    const n = matrix.length;
    requireThat(
        Array.isArray(mix) && mix.length === n,
        "Strategy proportions do not match the payoff matrix.",
    );
    mix.forEach((v) => finite(v, "Strategy proportion", 0, 1));
    requireThat(
        Math.abs(sum(mix) - 1) < 1e-8,
        "Strategy proportions must sum to one.",
    );
    for (const row of matrix) {
        requireThat(
            Array.isArray(row) && row.length === n,
            "Payoff matrix must be square.",
        );
        row.forEach((v) => finite(v, "Payoff", -100, 100));
    }
    const payoffs = matrix.map((row) => sum(row.map((v, i) => v * mix[i])));
    const mean = sum(payoffs.map((v, i) => v * mix[i]));
    return {
        derivative: mix.map((v, i) => v * (payoffs[i] - mean)),
        payoffs,
        mean,
    };
}

export function evolveStrategies(
    matrix,
    initial,
    { steps = 600, dt = 0.04 } = {},
) {
    integer(steps, "Integration steps", 1, 4000);
    finite(dt, "Time step", 0.0001, 0.1);
    replicatorField(matrix, initial);
    let state = [...initial];
    const history = [
        { t: 0, mix: [...state], welfare: replicatorField(matrix, state).mean },
    ];
    // RK4 in log-ratio coordinates preserves the simplex without clipping negative populations.
    requireThat(
        state.every((x) => x > 0),
        "Start each strategy above zero for log-ratio integration.",
    );
    const softmax = (z) => {
        const max = Math.max(...z),
            exps = z.map((v) => Math.exp(v - max)),
            total = sum(exps);
        return exps.map((v) => v / total);
    };
    let z = state.map(Math.log);
    const velocity = (v) => replicatorField(matrix, softmax(v)).payoffs;
    for (let i = 1; i <= steps; i++) {
        const a = velocity(z),
            b = velocity(z.map((v, j) => v + 0.5 * dt * a[j]));
        const c = velocity(z.map((v, j) => v + 0.5 * dt * b[j])),
            d = velocity(z.map((v, j) => v + dt * c[j]));
        z = z.map((v, j) => v + (dt * (a[j] + 2 * b[j] + 2 * c[j] + d[j])) / 6);
        const shift = Math.max(...z);
        z = z.map((v) => v - shift);
        state = softmax(z);
        history.push({
            t: i * dt,
            mix: [...state],
            welfare: replicatorField(matrix, state).mean,
        });
    }
    return history;
}

export function hawkDove(value, cost, initial = 0.2) {
    finite(value, "Resource value", 0.001, 100);
    finite(cost, "Conflict cost", 0.001, 100);
    finite(initial, "Initial hawk fraction", 0.001, 0.999);
    const matrix = [
        [(value - cost) / 2, value],
        [0, value / 2],
    ];
    return {
        matrix,
        equilibrium: Math.min(1, value / cost),
        interior: value < cost,
        history: evolveStrategies(matrix, [initial, 1 - initial]),
    };
}

export function architectSearch(input) {
    const base = validateScenario(input),
        candidates = [];
    // The same supplied opportunity values are used throughout: this is sensitivity search,
    // not learning, a held-out performance measurement, or fabricated economic growth.
    for (const scale of [0.6, 0.8, 1, 1.2, 1.4]) {
        const budget = Math.min(
            1000000,
            Math.max(1, Math.round(base.budget * scale)),
        );
        for (const riskScale of [0.5, 0.75, 1, 1.25]) {
            const risk_limit = Math.min(
                70000,
                Math.round(base.risk_limit * riskScale),
            );
            const analysis = analyseScenario(base, { budget, risk_limit });
            const { cost, value, risk } = analysis.portfolio.evidence.totals;
            candidates.push({
                id: `policy-${candidates.length + 1}`,
                budget,
                risk_limit,
                cost,
                value,
                risk,
                selected: analysis.portfolio.evidence.selected,
                duration: analysis.schedule?.evidence.makespan || 0,
            });
        }
    }
    return candidates.map((a) => ({
        ...a,
        frontier: !candidates.some(
            (b) =>
                b.cost <= a.cost &&
                b.risk <= a.risk &&
                b.duration <= a.duration &&
                b.value >= a.value &&
                (b.cost < a.cost ||
                    b.risk < a.risk ||
                    b.duration < a.duration ||
                    b.value > a.value),
        ),
    }));
}
