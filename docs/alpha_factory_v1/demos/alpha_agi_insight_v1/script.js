// SPDX-License-Identifier: Apache-2.0
const timers = new Set();
const delay = (fn, ms) => {
    const id = setTimeout(
        fn,
        matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : ms,
    );
    timers.add(id);
    return id;
};
const status = (text) => {
    document.getElementById("legacy-status").textContent = text;
};
const controls = ["offline-mode", "online-mode"].map((id) =>
    document.getElementById(id),
);
controls[0].textContent = "Replay bundled sample";
controls[1].textContent = "Generate synthetic data with OpenAI…";
function validate(forecast, population, tree) {
    const numeric = (value) =>
        typeof value === "number" && Number.isFinite(value);
    const label = (value) =>
        typeof value === "string" && value.length <= 100 && !/[<>]/.test(value);
    if (
        !Array.isArray(forecast?.years) ||
        !forecast.years.length ||
        forecast.years.length > 100 ||
        !forecast.years.every(numeric) ||
        !Array.isArray(forecast.capability) ||
        forecast.capability.length !== forecast.years.length ||
        !forecast.capability.every(numeric) ||
        !Array.isArray(forecast.sectors) ||
        forecast.sectors.length > 30 ||
        !forecast.sectors.every(
            (s) =>
                label(s.name) &&
                Array.isArray(s.values) &&
                s.values.length === forecast.years.length &&
                s.values.every(numeric),
        ) ||
        !Array.isArray(population?.solutions) ||
        population.solutions.length > 500 ||
        !population.solutions.every((s) => numeric(s.time) && numeric(s.value))
    )
        throw new Error("Chart data is not a bounded finite scenario");
    let count = 0;
    function visit(n, depth) {
        if (
            ++count > 200 ||
            depth > 12 ||
            !label(n?.name) ||
            (n.children && !Array.isArray(n.children))
        )
            throw new Error("Invalid tree data");
        for (const child of n.children || []) visit(child, depth + 1);
    }
    visit(tree, 0);
}
async function run(action) {
    controls.forEach((b) => (b.disabled = true));
    try {
        await action();
    } catch (error) {
        status(
            `Could not complete: ${error.message}. Replay the bundled sample or retry.`,
        );
    } finally {
        controls.forEach((b) => (b.disabled = false));
    }
}

async function loadDefaultData() {
    const [forecast, population, tree] = await Promise.all([
        fetch("forecast.json").then((r) => {
            if (!r.ok) throw new Error("Forecast unavailable");
            return r.json();
        }),
        fetch("population.json").then((r) => r.json()),
        fetch("tree.json").then((r) => r.json()),
    ]);
    return { forecast, population, tree };
}

async function renderCharts(forecastData, popData, treeData) {
    validate(forecastData, popData, treeData);
    timers.forEach(clearTimeout);
    timers.clear();
    document.getElementById("tree-container").replaceChildren();
    document.getElementById("scenario-data")?.remove();
    const detail = document.createElement("details");
    detail.id = "scenario-data";
    const summary = document.createElement("summary");
    summary.textContent = "Inspect all scenario data";
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(
        { forecast: forecastData, population: popData, tree: treeData },
        null,
        2,
    );
    detail.append(summary, pre);
    document.querySelector("main").append(detail);
    const years = forecastData.years;
    const capability = forecastData.capability;
    const sectors = forecastData.sectors;
    const solutions = popData.solutions;

    const capTrace = {
        x: years,
        y: capability,
        mode: "lines+markers",
        name: "AGI Capability",
        line: { color: "#d62728", width: 3 },
        marker: { size: 6, symbol: "circle", color: "#d62728" },
    };
    const capLayout = {
        margin: { t: 30, r: 20, l: 40, b: 40 },
        xaxis: { title: "Year", tickmode: "array", tickvals: years },
        yaxis: { title: "AGI Capability (T_AGI)", rangemode: "tozero" },
        title: { text: "AGI Capability vs Time", font: { size: 16 } },
    };
    await Plotly.newPlot("capability-chart", [capTrace], capLayout, {
        displayModeBar: false,
        responsive: true,
    });

    const timelineTraces = sectors.map((sector) => {
        const symbols = sector.values.map((_, idx) =>
            years[idx] === sector.disruptionYear ? "star" : "circle",
        );
        const sizes = sector.values.map((_, idx) =>
            years[idx] === sector.disruptionYear ? 12 : 6,
        );
        return {
            x: years,
            y: sector.values,
            mode: "lines+markers",
            name: sector.name,
            line: { width: 2 },
            marker: {
                size: sizes,
                symbol: symbols,
                line: { width: 1, color: "#000" },
            },
        };
    });
    const timelineLayout = {
        margin: { t: 30, r: 20, l: 40, b: 40 },
        xaxis: { title: "Year", tickmode: "array", tickvals: years },
        yaxis: { title: "Sector Performance Index", rangemode: "tozero" },
        title: {
            text: "Sector Performance and Disruption Jumps",
            font: { size: 16 },
        },
        legend: { orientation: "h", x: 0, y: -0.2 },
    };
    await Plotly.newPlot("timeline-chart", timelineTraces, timelineLayout, {
        displayModeBar: false,
        responsive: true,
    });

    const frontierPoints = solutions.filter((s) => s.frontier);
    const otherPoints = solutions.filter((s) => !s.frontier);
    const traceOthers = {
        x: otherPoints.map((p) => p.time),
        y: otherPoints.map((p) => p.value),
        mode: "markers",
        name: "Other Solutions",
        marker: { color: "rgba(100,100,100,0.5)", size: 8, symbol: "circle" },
        hovertemplate: "Time: %{x} yr<br>Value: %{y} trillion<extra></extra>",
    };
    const traceFrontier = {
        x: frontierPoints.map((p) => p.time),
        y: frontierPoints.map((p) => p.value),
        mode: "markers+lines",
        name: "Pareto Frontier",
        marker: { color: "#1f77b4", size: 10, symbol: "diamond" },
        line: { color: "#1f77b4", dash: "solid", width: 2 },
        hovertemplate: "Time: %{x} yr<br>Value: %{y} trillion<extra></extra>",
    };
    const paretoLayout = {
        margin: { t: 30, r: 20, l: 50, b: 50 },
        xaxis: {
            title: "Time to Disruption (years)",
            dtick: 1,
            range: [0.5, 5.5],
        },
        yaxis: { title: "Economic Value (USD trillions)", rangemode: "tozero" },
        title: {
            text: "Evolved Solutions Trade-off (Value vs Time)",
            font: { size: 16 },
        },
        legend: { x: 0.02, y: 0.98 },
    };
    await Plotly.newPlot(
        "pareto-chart",
        [traceOthers, traceFrontier],
        paretoLayout,
        {
            displayModeBar: false,
            responsive: true,
        },
    );

    const container = document.getElementById("tree-container");
    const width = container.clientWidth;
    const height = container.clientHeight;
    const svg = d3
        .select("#tree-container")
        .append("svg")
        .attr("width", width)
        .attr("height", height);
    const g = svg.append("g").attr("transform", "translate(40,40)");
    const root = d3.hierarchy(treeData);
    const treeLayout = d3.tree().size([height - 80, width - 80]);
    treeLayout(root);
    const linkPath = d3
        .linkHorizontal()
        .x((d) => d.y)
        .y((d) => d.x);
    const nodesData = root.descendants();
    let index = 0;
    function addNext() {
        if (index >= nodesData.length) {
            highlightPath();
            return;
        }
        const nd = nodesData[index];
        const parent = nd.parent;
        if (parent) {
            const newLink = g
                .append("path")
                .datum({ source: parent, target: nd })
                .attr("class", "link")
                .attr("d", linkPath({ source: parent, target: nd }))
                .style("opacity", 0);
            const length = newLink.node().getTotalLength();
            newLink
                .attr("stroke-dasharray", `${length} ${length}`)
                .attr("stroke-dashoffset", length)
                .transition()
                .duration(500)
                .style("opacity", 1)
                .attr("stroke-dashoffset", 0);
        }
        const nodeG = g
            .append("g")
            .datum(nd)
            .attr("class", "node")
            .attr("transform", `translate(${nd.y},${nd.x})`)
            .style("opacity", 0);
        nodeG.append("circle").attr("r", 5);
        nodeG.append("text").attr("dx", 8).attr("dy", 3).text(nd.data.name);
        nodeG.transition().duration(500).style("opacity", 1);
        index += 1;
        delay(addNext, 600);
    }
    function highlightPath() {
        const bestPath = root.data.bestPath || [];
        bestPath.forEach((name, idx) => {
            delay(() => {
                g.selectAll(".node")
                    .filter((d) => d.data.name === name)
                    .select("circle")
                    .transition()
                    .duration(400)
                    .attr("fill", "#d62728");
                if (idx > 0) {
                    const prev = bestPath[idx - 1];
                    g.selectAll(".link")
                        .filter(
                            (d) =>
                                d.source.data.name === prev &&
                                d.target.data.name === name,
                        )
                        .transition()
                        .duration(400)
                        .attr("stroke", "#d62728");
                }
            }, idx * 800);
        });
    }
    addNext();

    const logsElement = document.getElementById("logs-panel");
    logsElement.textContent = "";
    const logLines = [
        "[PlanningAgent] Initializing high-level plan and setting 5-year insight horizon.",
        "[ResearchAgent] Gathering domain data for all sectors (offline knowledge base).",
        "[StrategyAgent] Scoring sectors by AGI disruption risk…",
        "[StrategyAgent] -> Top sector identified: Transportation (imminent AGI impact).",
        "[MarketAgent] Estimating economic upside for Transportation: ~$1.5 trillion in first year.",
        "[CodeGenAgent] Generating prototype AGI solutions for Transportation sector.",
        "[SafetyGuardianAgent] Reviewing proposed strategies for alignment with safety policies.",
        "[PlanningAgent] Plan updated. Next target sector: Finance (year 2).",
        "[MemoryAgent] Logging outcome of year 1 disruption (Transportation) to ledger.",
        "----",
        "[PlanningAgent] Proceeding to next iteration with refined strategies…",
    ];
    let logIndex = 0;
    function stepLog() {
        logsElement.textContent += `${logLines[logIndex]}\n`;
        logIndex += 1;
        if (logIndex < logLines.length) {
            delay(stepLog, 1000);
        }
    }
    stepLog();
}

async function runOffline() {
    const { forecast, population, tree } = await loadDefaultData();
    await renderCharts(forecast, population, tree);
    status(
        "Bundled synthetic scenario and scripted agent logs. No forecast model or backend was executed.",
    );
}
async function runOnline(key, model) {
    status("Requesting synthetic chart data from OpenAI…");
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        signal: AbortSignal.timeout(60000),
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${key}`,
        },
        body: JSON.stringify({
            model,
            max_completion_tokens: 1600,
            messages: [
                {
                    role: "user",
                    content:
                        'Return only synthetic illustrative JSON, not factual forecasts: {"forecast":{"years":[2025,2026],"capability":[1,2],"sectors":[{"name":"Example","values":[1,2],"disruptionYear":2026}]},"population":{"solutions":[{"time":1,"value":2,"frontier":true}]},"tree":{"name":"Start","children":[{"name":"Example"}],"bestPath":["Start","Example"]}}. Keep this exact structure and bounded arrays.',
                },
            ],
        }),
    });
    if (!resp.ok) throw new Error(`OpenAI returned HTTP ${resp.status}`);
    const data = await resp.json();
    const parsed = JSON.parse(data.choices?.[0]?.message?.content || "");
    await renderCharts(parsed.forecast, parsed.population, parsed.tree);
    status(
        "OpenAI-generated synthetic scenario. Values and scripted logs are illustrative, not measured economic outcomes.",
    );
}
controls[0].addEventListener("click", () => run(runOffline));
controls[1].addEventListener("click", () =>
    run(async () => {
        const model = prompt(
            "OpenAI model ID for this paid synthetic-data request",
        );
        if (!model?.trim()) return;
        const key = prompt("API key, used for this request only; never saved");
        if (!key?.trim()) return;
        await runOnline(key.trim(), model.trim());
    }),
);
run(runOffline);

document.getElementById("toggle-logs").addEventListener("click", () => {
    const panel = document.getElementById("logs-panel");
    panel.classList.toggle("hidden");
    const expanded = !panel.classList.contains("hidden");
    document
        .getElementById("toggle-logs")
        .setAttribute("aria-expanded", expanded.toString());
});
