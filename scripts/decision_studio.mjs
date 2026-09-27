#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Reproduce browser decisions without a browser or provider.
import fs from "node:fs/promises";
import path from "node:path";
import { solve, verify, csv, brief } from "../docs/assets/studio/engine.mjs";
const cases = JSON.parse(
    await fs.readFile(
        new URL("../docs/assets/studio/cases.json", import.meta.url),
        "utf8",
    ),
);
const args = process.argv.slice(2);
const usage =
    "Usage: node scripts/decision_studio.mjs --case <id> | --input scenario.json | --verify report.json [--output directory]\nCases: " +
    cases.map((c) => c.id).join(", ");
try {
    if (!args.length || args.includes("--help")) {
        console.log(usage);
        process.exit(0);
    }
    const options = {};
    for (let i = 0; i < args.length; i += 2) {
        if (
            !["--case", "--input", "--verify", "--output"].includes(args[i]) ||
            !args[i + 1] ||
            options[args[i]]
        )
            throw new Error(usage);
        options[args[i]] = args[i + 1];
    }
    if (
        ["--case", "--input", "--verify"].filter((k) => options[k]).length !== 1
    )
        throw new Error(usage);
    let report;
    if (options["--case"]) {
        const c = cases.find((c) => c.id === options["--case"]);
        if (!c) throw new Error("Unknown case. " + usage);
        report = solve(c.input);
    } else {
        const filename = options["--input"] || options["--verify"];
        const limit = options["--verify"] ? 1048576 : 256000;
        if ((await fs.stat(filename)).size > limit)
            throw new Error("Input exceeds the permitted file size.");
        const content = await fs.readFile(filename);
        if (content.length > limit)
            throw new Error("Input exceeds the permitted file size.");
        report = options["--verify"]
            ? verify(JSON.parse(content.toString()))
            : solve(JSON.parse(content.toString()));
    }
    if (options["--output"]) {
        const dir = path.resolve(options["--output"]);
        await fs.mkdir(dir, { recursive: true });
        if ((await fs.readdir(dir)).length)
            throw new Error(
                "Choose an empty output directory to preserve existing files.",
            );
        const outputs = {
            "scenario.json": JSON.stringify(report.input, null, 2) + "\n",
            "dossier.json": JSON.stringify(report, null, 2) + "\n",
            "plan.csv": csv(report),
            "decision-brief.md": brief(report),
            "proof-jobs.json":
                JSON.stringify(
                    {
                        schema: "agialpha.decision.jobs.v1",
                        scenario: report.input.id,
                        provenance: report.input.provenance,
                        status: "UNSUBMITTED",
                        jobs: report.output.jobs,
                    },
                    null,
                    2,
                ) + "\n",
        };
        for (const [name, value] of Object.entries(outputs))
            await fs.writeFile(path.join(dir, name), value, { flag: "wx" });
        console.log(
            `Wrote ${Object.keys(outputs).length} decision artifacts to ${dir}`,
        );
    }
    console.log(
        JSON.stringify(
            {
                case: report.input.id,
                verdict: report.output.verdict,
                summary: report.output.summary,
                metrics: report.output.metrics,
            },
            null,
            2,
        ),
    );
} catch (error) {
    console.error(error.message);
    process.exitCode = 1;
}
