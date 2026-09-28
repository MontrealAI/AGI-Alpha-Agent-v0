// SPDX-License-Identifier: Apache-2.0
import { curveQuote, tokenUnits, tokenDecimal } from "../ascension/engine.mjs?v=1.18.0";
const $ = (id) => document.getElementById(id);
let report;
const descriptions = {
    all: "Every transaction below executed successfully against the shipped Solidity contracts on a local EVM.",
    "Nova-Seed":
        "An ERC-721 commits to the encrypted genome and the Merkle root of its executable FusionPlan.",
    "Risk oracle":
        "Two distinct, staked validator addresses approve the seed. Their votes bind evidence and expire after seven days.",
    MARK: "The linear bonding-curve AMM issues 40 funding lots for exactly 158 $AGIALPHA. Before bloom, lots can be sold back or transferred.",
    Sovereign:
        "The seed blooms into a treasury for resilience.alpha.agi.eth. Its funds can only enter jobs proven to belong to the committed plan.",
    "α-Job":
        "Goal, success metric and bounty become a contract-enforced mission. Altering any committed job field invalidates its Merkle proof.",
    Auction:
        "The faster 80-token bidder beats the slower 70-token bidder under this mission’s 60% price / 40% time rule. Losing collateral is unlocked.",
    Delivery:
        "The local alpha-agent runs the actual allocation mission. Its delivered JSON digest is the exact artifact reviewed by the committee.",
    Validation:
        "Two of three selected validators approve the same result hash. Every payment burns 1%; refunds and returned stake are exempt.",
    Recovery:
        "80 tokens fund gross worker and reviewer payouts. The remaining 78 tokens return to the funder; no capital remains trapped in MARK.",
    "Evolution candidate":
        "A successor NFT records parentage and the delivered evidence. It receives no inherited green status; a new review is required.",
};
function node(tag, value, cls) {
    const el = document.createElement(tag);
    el.textContent = value;
    if (cls) el.className = cls;
    return el;
}
function showTrace() {
    const selected = $("stage").value;
    $("stage-detail").textContent = descriptions[selected];
    const rows = report.steps.filter(
        (s) => selected === "all" || s.stage === selected,
    );
    $("trace").replaceChildren(
        ...rows.map((s) => {
            const card = node("article", "", "trace-row");
            const title = node("div", "", "trace-title");
            title.append(
                node("span", s.stage),
                node(
                    "small",
                    `Block ${s.block} · ${BigInt(s.gasUsed).toLocaleString()} gas`,
                ),
            );
            card.append(
                title,
                node("p", s.events.map((e) => e.event).join(" → ")),
                node("code", s.transactionHash),
            );
            const details = document.createElement("details");
            details.append(
                node("summary", "Inspect event arguments"),
                node("pre", JSON.stringify(s.events, null, 2)),
            );
            card.append(details);
            return card;
        }),
    );
    $("trace-count").textContent = `${rows.length} recorded transactions`;
}
function calculate() {
    try {
        const supply = Number($("supply").value),
            lots = Number($("lots").value);
        const cost = curveQuote({
            supply,
            lots,
            base: $("base").value,
            slope: $("slope").value,
        });
        $("quote").textContent = `${cost.amount} $AGIALPHA`;
        $("quote-note").textContent =
            "Exact integer sum of the next lot prices. These are editable assumptions; this calculator places no trade.";
    } catch (error) {
        $("quote").textContent = "Check inputs";
        $("quote-note").textContent = error.message;
    }
}
function auction() {
    try {
        const weight = Number($("price-weight").value);
        const price = tokenUnits($("bid-price").value),
            time = Number($("bid-time").value),
            rep = Number($("reputation").value);
        if (
            !Number.isSafeInteger(time) ||
            time < 1 ||
            time > 86400 ||
            !Number.isSafeInteger(rep) ||
            rep < 0 ||
            rep > 10000 ||
            !Number.isSafeInteger(weight) ||
            weight < 0 ||
            weight > 10000 ||
            price < 100n ||
            price > tokenUnits("100")
        )
            throw Error(
                "Use 0–10,000 reputation, 1–86,400 seconds and a price of at most 100 tokens.",
            );
        const score = (p, t, r) =>
            (((p * BigInt(weight) * 1000000n) / tokenUnits("100") +
                (BigInt(t) * BigInt(10000 - weight) * 1000000n) / 86400n) *
                10000n) /
            BigInt(10000 + r);
        const candidate = score(price, time, rep),
            reference = score(tokenUnits("70"), 86000, 0);
        $("auction-score").textContent = candidate.toLocaleString();
        $("auction-note").textContent =
            `${candidate < reference ? "Wins against" : candidate > reference ? "Loses to" : "Ties with"} the reference bid: 70 tokens, 86,000 seconds, no earned reputation. Lower score wins; ties use price, duration, then address.`;
    } catch (error) {
        $("auction-score").textContent = "Check inputs";
        $("auction-note").textContent = error.message;
    }
}
async function start() {
    const evidence = new URL("./receipt.json", import.meta.url);
    evidence.search = new URL(import.meta.url).search;
    const response = await fetch(evidence);
    if (!response.ok)
        throw Error("The transaction evidence could not be loaded.");
    report = await response.json();
    if (
        report.schema !== "agialpha.ascension.local-evm.v1" ||
        report.chainId !== "31337" ||
        report.steps.some((s) => s.status !== 1)
    )
        throw Error("Unexpected evidence format or failed receipt.");
    const a = report.accounting;
    if (
        BigInt(a.funded) !==
        BigInt(a.workerNet) +
            BigInt(a.validatorsNet) +
            BigInt(a.burned) +
            BigInt(a.refunded) +
            BigInt(a.remainingTreasury)
    )
        throw Error("Accounting does not reconcile.");
    for (const key of ["funded", "burned", "refunded", "workerNet"])
        $(key).textContent = tokenDecimal(BigInt(a[key]));
    const result = report.nativeDelivery.nativeResult.result;
    $("native-result").textContent =
        `${result.selected.length} selected projects · ${result.cost} budget credits · ${result.value} modeled resilience points · risk ${result.risk}`;
    $("boundaries").replaceChildren(
        ...report.limitations.map((value) => node("li", value)),
    );
    $("stage").addEventListener("change", showTrace);
    showTrace();
    $("status").textContent = "Local EVM snapshot · accounting reconciled";
    $("status").classList.add("ready");
}
for (const id of ["supply", "lots", "base", "slope"])
    $(id).addEventListener("input", calculate);
for (const id of ["price-weight", "bid-price", "bid-time", "reputation"])
    $(id).addEventListener("input", auction);
calculate();
auction();
start().catch((error) => {
    $("status").textContent = error.message;
    $("status").setAttribute("role", "alert");
});
if ("serviceWorker" in navigator)
    navigator.serviceWorker
        .register(new URL("../../service-worker.js", import.meta.url))
        .catch(() => {});
