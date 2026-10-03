// SPDX-License-Identifier: Apache-2.0
import { canonical, digest, verify } from "./engine.mjs?v=1.23.3";
const number = (value) =>
    value.toLocaleString("en-US", { maximumFractionDigits: 0 });
export function brief(report) {
    const { input: source, result } = report,
        p = result.portfolio;
    const lines = [
        `# ${source.title}`,
        "",
        `Status: ${result.status}`,
        `Evidence: ${source.provenance.kind} — ${source.provenance.note}`,
        "",
    ];
    if (p)
        lines.push(
            `Selected projects: ${p.projectIds.join(", ") || "none"}`,
            `Three-year expected NPV: USD ${number(p.expectedNpvUsd)}`,
            `Policy-downside NPV: USD ${number(p.downsideNpvUsd)}`,
            `Capital including contingency: USD ${number(p.stressedCostUsd)} / ${number(source.policy.budgetUsd)}`,
            `Staff days: ${p.staffDays} / ${source.policy.staffDays}`,
            `Review minutes: ${p.reviewMinutes} / ${source.policy.reviewMinutes}`,
            `Unsubmitted job bounties: ${number(p.bountyTokens)} AGIALPHA / ${number(source.policy.jobBudgetTokens)}`,
        );
    else
        lines.push(
            "No subset meets all declared constraints. Change the inputs or reserve more resources before proceeding.",
        );
    lines.push(
        "",
        "## Before implementation",
        "",
        "Independently verify the cited inputs and job success metrics. Review adverse scenarios. No project is funded or approved by this calculation.",
        "",
        "## Method",
        "",
        "Year-end cash flows over three years, no terminal value. Each discounted cash flow is floored to whole USD; adverse capital is rounded up. Negative cash flows worsen under the haircut. The optimizer reserves stressed capital, staff time, reviewer time and a separate AGIALPHA job budget.",
        "",
        result.scope,
        "",
        `Dossier SHA-256: ${report.sha256}`,
        "",
    );
    return lines.join("\n");
}
export async function artifacts(report) {
    await verify(report);
    const selected = new Set(report.result.portfolio?.projectIds || []),
        rows = new Map(report.result.analysis.map((row) => [row.id, row]));
    const csv = [
        [
            "project_id",
            "cost_usd",
            "stressed_cost_usd",
            "expected_npv_usd",
            "downside_npv_usd",
            "staff_days",
            "review_minutes",
            "bounty_agialpha",
        ],
    ];
    for (const p of report.input.projects)
        if (selected.has(p.id)) {
            const r = rows.get(p.id);
            csv.push([
                p.id,
                p.costUsd,
                r.stressedCostUsd,
                r.expectedNpvUsd,
                r.downsideNpvUsd,
                p.staffDays,
                p.reviewMinutes,
                p.bountyTokens,
            ]);
        }
    const seed = {
        schema: "agialpha.business3.seed-draft.v1",
        status: "UNMINTED_UNENCRYPTED",
        dossierSha256: report.sha256,
        jobsSha256: await digest(report.result.jobs),
        note: "A content commitment for review, not an ERC-721 or encrypted secret. Compile jobs with alpha-agent ascension-compile; review the local-EVM protocol before deployment.",
    };
    const files = {
        "scenario.json": canonical(report.input) + "\n",
        "dossier.json": canonical(report) + "\n",
        "jobs.json": canonical(report.result.jobs) + "\n",
        "seed-draft.json": canonical(seed) + "\n",
        "decision-brief.md": brief(report),
        "selected-projects.csv":
            csv.map((row) => row.join(",")).join("\n") + "\n",
    };
    const sums = [];
    for (const name of Object.keys(files).sort()) {
        const raw = await crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(files[name]),
        );
        sums.push(
            Array.from(new Uint8Array(raw), (b) =>
                b.toString(16).padStart(2, "0"),
            ).join("") +
                "  " +
                name +
                "\n",
        );
    }
    files.SHA256SUMS = sums.join("");
    return files;
}
