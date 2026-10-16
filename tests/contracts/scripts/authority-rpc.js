// SPDX-License-Identifier: Apache-2.0
// Read-only JSON-RPC transport. This module has no signing or relay path.
const https = require("https");
const http = require("http");
const ethers = require("ethers");
const LIMITS = Object.freeze({ timeoutMs: 20000, responseBytes: 2 * 1024 * 1024,
    requestBytes: 256 * 1024, requests: 2000, totalBytes: 100 * 1024 * 1024,
    deadlineMs: 300000, logChunkBlocks: 1000, logIntervalBlocks: 100000, logs: 10000 });
function fail(message) { const e = Error(message); e.publicMessage = true; return e; }
function need(value, message) { if (!value) throw fail(message); }
const quantity = x => typeof x === "string" && /^0x(?:0|[1-9a-f][0-9a-f]*)$/.test(x) && x.length <= 66;
const hash = x => typeof x === "string" && /^0x[0-9a-fA-F]{64}$/.test(x);
const bytes = x => typeof x === "string" && /^0x(?:[0-9a-fA-F]{2})*$/.test(x);
const address = x => typeof x === "string" && /^0x[0-9a-fA-F]{40}$/.test(x);
const block = x => quantity(x) || ["latest", "pending", "finalized"].includes(x);
function keys(value, allowed) { return value && typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === allowed.length && allowed.every(k => Object.hasOwn(value, k)); }
function limitsFor(overrides = {}) {
    need(overrides && typeof overrides === "object" && !Array.isArray(overrides), "Invalid RPC limits");
    const limits = { ...LIMITS };
    for (const [k, v] of Object.entries(overrides)) {
        need(Object.hasOwn(LIMITS, k) && Number.isSafeInteger(v) && v > 0 && v <= LIMITS[k], "RPC limits may only be reduced"); limits[k] = v;
    }
    return limits;
}
function validate(method, params, scope, limits) {
    const addresses = scope.graph;
    need(Array.isArray(params), "RPC parameters must be an array");
    let valid = false;
    switch (method) {
    case "eth_chainId": valid = params.length === 0; break;
    case "eth_getCode": case "eth_getTransactionCount": case "eth_getBalance": valid = params.length === 2 && address(params[0]) && block(params[1]); break;
    case "eth_getTransactionByHash": case "eth_getTransactionReceipt": valid = params.length === 1 && hash(params[0]); break;
    case "eth_getBlockByNumber": valid = params.length === 2 && block(params[0]) && typeof params[1] === "boolean"; break;
    case "eth_call": valid = params.length === 2 && keys(params[0], ["to", "data"]) && address(params[0].to) && bytes(params[0].data) && block(params[1]); break;
    case "eth_getLogs": {
        const f = params[0];
        valid = params.length === 1 && keys(f, ["address", "fromBlock", "toBlock"]) && Array.isArray(f.address) && f.address.length === 5 &&
            f.address.every(address) && new Set(f.address.map(a => a.toLowerCase())).size === 5 &&
            JSON.stringify(f.address.map(a => a.toLowerCase()).sort()) === JSON.stringify(addresses) && quantity(f.fromBlock) && quantity(f.toBlock);
        if (valid) valid = BigInt(f.fromBlock) <= BigInt(f.toBlock) && BigInt(f.toBlock) - BigInt(f.fromBlock) < BigInt(limits.logIntervalBlocks);
        break;
    }
    default: throw fail("RPC method is not read-only allowlisted");
    }
    if (valid && ["eth_getCode", "eth_getTransactionCount", "eth_getBalance"].includes(method)) valid = scope.all.includes(params[0].toLowerCase());
    if (valid && method === "eth_call") valid = scope.all.includes(params[0].to.toLowerCase());
    if (valid && method === "eth_getLogs") valid = BigInt(params[0].fromBlock) >= BigInt(scope.earliestBlock);
    need(valid, "RPC parameter shape or scope rejected");
}
function resultShape(method, result) {
    if (["eth_chainId", "eth_getTransactionCount", "eth_getBalance"].includes(method)) return quantity(result);
    if (["eth_getCode", "eth_call"].includes(method)) return bytes(result);
    if (method === "eth_getLogs") return Array.isArray(result);
    if (result === null) return true;
    return result && typeof result === "object" && !Array.isArray(result);
}
function makeRpc(endpoint, inputScope, options, localTest) {
    const { limits: overrides, ...extra } = options || {};
    need(Object.keys(extra).length === 0, "Unsupported RPC options");
    let url; try { url = new URL(endpoint); } catch { throw fail("Invalid RPC endpoint"); }
    need(!url.username && !url.password && !url.hash, "RPC endpoint must not contain credentials or fragments");
    need(localTest ? url.protocol === "http:" && ["127.0.0.1", "[::1]"].includes(url.hostname) : url.protocol === "https:",
        localTest ? "Disposable test RPC must use numeric loopback HTTP" : "RPC endpoint must use HTTPS");
    const inputAddresses = inputScope?.graph;
    need(Array.isArray(inputAddresses) && inputAddresses.length === 5 && inputAddresses.every(address), "Five exact graph addresses required");
    const addresses = inputAddresses.map(a => a.toLowerCase()).sort();
    need(new Set(addresses).size === 5, "Five distinct graph addresses required");
    need(keys(inputScope, ["graph", "all", "earliestBlock"]) && Array.isArray(inputScope.all) && inputScope.all.every(address) &&
        inputScope.all.length <= 128 && Number.isSafeInteger(inputScope.earliestBlock) && inputScope.earliestBlock >= 0, "Invalid RPC read scope");
    const scope = { graph: addresses, all: [...new Set(inputScope.all.map(a => a.toLowerCase()))], earliestBlock: inputScope.earliestBlock };
    need(addresses.every(a => scope.all.includes(a)), "RPC scope must include graph addresses");
    const limits = limitsFor(overrides), started = Date.now();
    let requests = 0, totalBytes = 0, stopped = false, busy = false;
    function budget() { need(!stopped && Date.now() - started < limits.deadlineMs, "Read-only RPC stopped or deadline exhausted"); }
    async function request(method, params) {
        budget(); validate(method, params, scope, limits);
        need(requests < limits.requests, "RPC request budget exhausted");
        const id = ++requests, body = JSON.stringify({ jsonrpc: "2.0", id, method, params });
        const size = Buffer.byteLength(body); need(size <= limits.requestBytes && totalBytes + size <= limits.totalBytes, "RPC byte budget exhausted"); totalBytes += size;
        return new Promise((resolve, reject) => {
            let settled = false, req;
            const finish = (error, value) => { if (settled) return; settled = true; clearTimeout(timer); if (error) { stopped = true; req?.destroy(); reject(error); } else resolve(value); };
            const timer = setTimeout(() => finish(fail("Read-only RPC timeout")), Math.min(limits.timeoutMs, limits.deadlineMs - (Date.now() - started)));
            try {
                req = (localTest ? http : https).request(url, { method: "POST", headers: { "content-type": "application/json", "content-length": size, "accept-encoding": "identity" }, agent: false }, res => {
                    if (res.statusCode !== 200 || (res.headers["content-encoding"] && res.headers["content-encoding"] !== "identity")) { finish(fail("Read-only RPC HTTP status or encoding rejected")); return res.destroy(); }
                    const length = res.headers["content-length"];
                    if (length !== undefined && (!/^\d+$/.test(length) || Number(length) > limits.responseBytes || Number(length) + totalBytes > limits.totalBytes)) { finish(fail("RPC response byte budget exhausted")); return res.destroy(); }
                    let received = 0; const chunks = [];
                    res.on("data", chunk => {
                        received += chunk.length; totalBytes += chunk.length;
                        if (received > limits.responseBytes || totalBytes > limits.totalBytes) { finish(fail("RPC response byte budget exhausted")); res.destroy(); }
                        else chunks.push(chunk);
                    });
                    res.on("error", () => finish(fail("Read-only RPC response failed")));
                    res.on("aborted", () => finish(fail("Read-only RPC response interrupted")));
                    res.on("end", () => {
                        if (settled) return;
                        try {
                            budget(); const value = JSON.parse(Buffer.concat(chunks).toString("utf8"));
                            need(keys(value, ["jsonrpc", "id", "result"]) && value.jsonrpc === "2.0" && value.id === id && resultShape(method, value.result), "Malformed or error RPC response");
                            finish(null, value.result);
                        } catch { finish(fail("Malformed or error RPC response")); }
                    });
                });
                req.on("error", () => finish(fail("Read-only RPC network failure"))); req.end(body);
            } catch { finish(fail("Read-only RPC network failure")); }
        });
    }
    async function boundary(n) {
        const b = await request("eth_getBlockByNumber", [ethers.toQuantity(n), false]);
        need(b && quantity(b.number) && BigInt(b.number) === n && hash(b.hash), "Missing canonical log boundary"); return b.hash.toLowerCase();
    }
    async function logs(filter) {
        const from = BigInt(filter.fromBlock), to = BigInt(filter.toBlock);
        const initial = [await boundary(from), await boundary(to)], entries = [], seen = new Set();
        for (let low = from; low <= to; low += BigInt(limits.logChunkBlocks)) {
            const high = low + BigInt(limits.logChunkBlocks) - 1n < to ? low + BigInt(limits.logChunkBlocks) - 1n : to;
            const batch = await request("eth_getLogs", [{ address: [...filter.address], fromBlock: ethers.toQuantity(low), toBlock: ethers.toQuantity(high) }]);
            need(entries.length + batch.length <= limits.logs, "RPC log count budget exhausted");
            for (const log of batch) {
                need(log && address(log.address) && addresses.includes(log.address.toLowerCase()) && log.removed === false && quantity(log.blockNumber) &&
                    BigInt(log.blockNumber) >= low && BigInt(log.blockNumber) <= high && hash(log.blockHash) && hash(log.transactionHash) &&
                    quantity(log.transactionIndex) && quantity(log.logIndex) && bytes(log.data) && Array.isArray(log.topics) && log.topics.length <= 4 && log.topics.every(hash), "Malformed, removed or out-of-scope RPC log");
                const key = `${log.blockNumber}:${log.logIndex}`;
                need(!seen.has(key), "Duplicate RPC log"); seen.add(key); entries.push(log);
            }
        }
        need(initial[0] === await boundary(from) && initial[1] === await boundary(to), "Canonical log boundary changed");
        return entries;
    }
    const rpc = async (method, params) => {
        need(!busy, "Concurrent RPC calls are unsupported"); busy = true;
        try { budget(); validate(method, params, scope, limits); return method === "eth_getLogs" ? await logs(params[0]) : await request(method, params); }
        catch (error) { stopped = true; throw error.publicMessage ? error : fail("Read-only RPC failed"); }
        finally { busy = false; }
    };
    rpc.stats = () => ({ requests, totalBytes, stopped, elapsedMs: Date.now() - started });
    return rpc;
}
function scopeForPlan(plan) {
    const c = plan.config, graph = Object.values(plan.addresses);
    return { graph, all: [...new Set([...graph, c.deployer, c.governor.address, ...Object.values(c.dependencies).map(d => d.address),
        ...(c.sender.target ? [c.sender.target] : []), ...(c.sender.stateChecks || []).map(s => s.to)].map(a => ethers.getAddress(a)))], earliestBlock: c.block.number };
}
function createReadOnlyRpc(endpoint, scope, options) { return makeRpc(endpoint, scope, options, false); }
// Deliberately separate adapter; never exposed as an operator CLI option.
function createTestReadOnlyRpc(endpoint, scope, options) { return makeRpc(endpoint, scope, options, true); }
module.exports = { LIMITS, scopeForPlan, createReadOnlyRpc, createTestReadOnlyRpc };
