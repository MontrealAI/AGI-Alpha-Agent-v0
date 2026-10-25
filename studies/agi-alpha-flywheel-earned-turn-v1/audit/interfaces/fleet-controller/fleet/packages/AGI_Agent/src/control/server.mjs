import {parseStrict} from '../../successor/vendor/manager/site/assets/successor/safe.mjs';
import {SuccessorController} from '../../successor/controller.mjs';
import {studioSpec,validateHandoff} from '../studio.mjs';
import {validateBundle,computerVerdict} from '../artifacts.mjs';
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { ROOT, ensure } from "../util.mjs";
import { publicError } from "./messages.mjs";
const token = () => crypto.randomBytes(32).toString("hex");
const equal = (a, b) =>
  typeof a === "string" &&
  typeof b === "string" &&
  /^[a-f0-9]{64}$/.test(a) &&
  /^[a-f0-9]{64}$/.test(b) &&
  crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
export async function createControlServer(
  controller,
  { port = 8788, launchSecret = token(), onQuit = null } = {},
) {
  let successorAdapter;
  const successor = () => {
    ensure(typeof controller.home === 'string' && path.isAbsolute(controller.home), 'FLEET_HOME_REQUIRED');
    return successorAdapter ??= new SuccessorController(controller, 'agent', {studioSpec,validateHandoff,validateBundle,computerVerdict});
  };
  const sessions = new Map(),
    bootstraps = new Map(),
    attempts = new Map();
  let actualPort = port;
  const origin = () => `http://127.0.0.1:${actualPort}`;
  // Cookies share a host across ports; original and seed profiles need separate names.
  const sessionCookieName = () => `agi_agent_session_${actualPort}`;
  const bootstrap = () => {
    const key = token();
    bootstraps.set(key, Date.now() + 60000);
    while (bootstraps.size > 8)
      bootstraps.delete(bootstraps.keys().next().value);
    return origin() + "/#" + key;
  };
  const limited = (name, max, window) => {
    const times = (attempts.get(name) ?? []).filter(
      (t) => t > Date.now() - window,
    );
    ensure(times.length < max, "TOO_MANY_ATTEMPTS");
    times.push(Date.now());
    attempts.set(name, times);
  };
  async function body(req, limit = 1024 * 1024) {
    ensure(
      req.headers["content-type"]?.split(";")[0] === "application/json",
      "JSON_REQUEST_REQUIRED",
    );
    ensure(
      Number(req.headers["content-length"] ?? 0) <= limit,
      "REQUEST_TOO_LARGE",
    );
    let bytes = 0,
      parts = [];
    for await (const part of req) {
      bytes += part.length;
      ensure(bytes <= limit, "REQUEST_TOO_LARGE");
      parts.push(part);
    }
    try {
      const raw = Buffer.concat(parts).toString("utf8");
      return req.url.startsWith("/api/successor/") ? parseStrict(raw,limit) : JSON.parse(raw);
    } catch {
      throw new Error("REQUEST_JSON_INVALID");
    }
  }
  const server = http.createServer(async (req, res) => {
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Referrer-Policy", "no-referrer");
    res.setHeader(
      "Content-Security-Policy",
      "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'",
    );
    const json = (value, status = 200) => {
      if (res.writableEnded) return;
      res.writeHead(status, {
        "Content-Type": "application/json; charset=utf-8",
      });
      res.end(JSON.stringify(value));
    };
    try {
      ensure(req.headers.host === `127.0.0.1:${actualPort}`, "HOST_REJECTED");
      const url = new URL(req.url, origin());
      ensure(url.origin === origin(), "HOST_REJECTED");
      if (req.headers.origin)
        ensure(req.headers.origin === origin(), "ORIGIN_REJECTED");
      if (url.pathname === "/api/monitor/status") {
        ensure(req.method === "GET" && !url.search, "METHOD_REJECTED");
        limited("monitor-feed", 60, 60000);
        ensure(
          controller.companion?.acceptsReadToken(
            req.headers.authorization?.replace(/^Bearer /, ""),
          ),
          "AUTH_REQUIRED",
        );
        json(controller.operations.snapshot());
        return;
      }
      if (url.pathname === "/api/companion/status") {
        ensure(req.method === "GET" && !url.search, "METHOD_REJECTED");
        limited("read-feed", 60, 60000);
        ensure(
          controller.companion?.acceptsReadToken(
            req.headers.authorization?.replace(/^Bearer /, ""),
          ),
          "AUTH_REQUIRED",
        );
        json({
          generatedAt: new Date().toISOString(),
          ...controller.companionSnapshot(),
        });
        return;
      }
      if (!url.pathname.startsWith("/api/")) {
        ensure(req.method === "GET", "METHOD_REJECTED");
        const routes = {
          "/": ["index.html", "text/html; charset=utf-8"],
          "/genesis.js": ["genesis.js", "text/javascript; charset=utf-8"],
          "/experience.js": ["experience.js", "text/javascript; charset=utf-8"],
          "/atelier.css": ["atelier.css", "text/css; charset=utf-8"],
          "/genesis.css": ["genesis.css", "text/css; charset=utf-8"],
          "/operations.js": ["operations.js", "text/javascript; charset=utf-8"],
          "/studio.js": ["studio.js", "text/javascript; charset=utf-8"],
          "/successor.js": ["successor.js", "text/javascript; charset=utf-8"],
          "/studio.css": ["studio.css", "text/css; charset=utf-8"],
          "/wallet.js": ["wallet.js", "text/javascript; charset=utf-8"],
          "/public-browser-ui.js": ["public-browser-ui.js", "text/javascript; charset=utf-8"],
          "/app.js": ["app.js", "text/javascript; charset=utf-8"],
          "/style.css": ["style.css", "text/css; charset=utf-8"],
        };
        const item = routes[url.pathname];
        if (!item) {
          res.writeHead(404).end();
          return;
        }
        res.writeHead(200, { "Content-Type": item[1] });
        res.end(fs.readFileSync(path.join(ROOT, "app", item[0])));
        return;
      }
      if (req.method === "POST")
        ensure(req.headers.origin === origin(), "ORIGIN_REQUIRED");
      if (url.pathname === "/api/launch") {
        ensure(
          req.method === "POST" &&
            equal(
              req.headers.authorization?.replace(/^Bearer /, ""),
              launchSecret,
            ),
          "AUTH_REQUIRED",
        );
        limited("launch", 20, 60000);
        await body(req);
        json({ url: bootstrap() });
        return;
      }
      if (url.pathname === "/api/session") {
        ensure(req.method === "POST", "METHOD_REJECTED");
        limited("session", 20, 60000);
        const input = await body(req),
          expiry = bootstraps.get(input.token);
        bootstraps.delete(input.token);
        ensure(expiry && expiry > Date.now(), "SESSION_LINK_EXPIRED");
        const id = token(),
          csrf = token();
        sessions.set(id, { csrf, until: Date.now() + 8 * 3600000 });
        while (sessions.size > 8) sessions.delete(sessions.keys().next().value);
        res.setHeader(
          "Set-Cookie",
          `${sessionCookieName()}=${id}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800`,
        );
        json({ csrf });
        return;
      }
      const cookie = req.headers.cookie
          ?.split(";")
          .map((x) => x.trim())
          .find((x) => x.startsWith(sessionCookieName() + "="))
          ?.slice(sessionCookieName().length + 1),
        session = sessions.get(cookie);
      ensure(session && session.until > Date.now(), "AUTH_REQUIRED");
      session.until = Date.now() + 8 * 3600000;
      if (req.method === "GET") {
        if (url.pathname === "/api/status")
          json({ ...controller.status(), csrf: session.csrf });
        else if (url.pathname === "/api/delivery")
          json(controller.delivery(url.searchParams.get("id")));
        else if (url.pathname === "/api/pilot") json(controller.pilot.report());
        else if (url.pathname === "/api/operations/evidence")
          json(controller.operations.evidenceReport());
        else if (url.pathname === "/api/operations")
          json({
            ...controller.operations.summary(),
            monitor: controller.operations.snapshot(),
          });
        else if (url.pathname === "/api/identity")
          json(controller.operations.identity());
        else if (url.pathname === "/api/report") json(controller.report());
        else if (url.pathname === "/api/successor") json(successor().status());
        else if (url.pathname === "/api/successor/runtime") json(await successor().health());
        else if (url.pathname === "/api/studio") json(controller.studio.status());
        else if (url.pathname === "/api/studio/export") json(controller.studio.export(url.searchParams.get("id"),url.searchParams.get("kind")));
        else if (url.pathname === "/api/companion/public-web-report") {ensure(!url.search,"METHOD_REJECTED");json(controller.companionPublicWebReport());}
        else if (url.pathname === "/api/companion/preview")
          json(controller.companionSnapshot());
        else json({ error: { title: "Page not found" } }, 404);
        return;
      }
      ensure(req.method === "POST", "METHOD_REJECTED");
      ensure(equal(req.headers["x-agi-csrf"], session.csrf), "CSRF_REJECTED");
      limited("mutations", 60, 60000);
      if (["/api/wallet/reveal", "/api/wallet/confirm", "/api/wallet/phrase"].includes(url.pathname)) limited("wallet-recovery", 8, 60000);
      const input = await body(
        req,
        ["/api/restore","/api/backup/verify"].includes(url.pathname) ? 64 * 1024 * 1024 : ["/api/studio/start","/api/successor/prepare"].includes(url.pathname) ? 128 * 1024 * 1024 : 1024 * 1024,
      );
      ensure(
        input && typeof input === "object" && !Array.isArray(input),
        "REQUEST_JSON_INVALID",
      );
      if (url.pathname === "/api/pause") {
        json(controller.pause());
        return;
      }
      if (url.pathname === "/api/quit") {
        ensure(typeof onQuit === "function", "QUIT_UNAVAILABLE");
        json({ quitting: true });
        setTimeout(() => void onQuit(), 100);
        return;
      }
      if (url.pathname === "/api/successor/revoke") { json(successor().revoke()); return; }
      // Cancellation may preempt only an asynchronous SUCCESSOR inspection.
      // Configuration/restore mutations keep their existing exclusive gate.
      if (["/api/successor/stop","/api/studio/cancel","/api/stop","/api/lock"].includes(url.pathname)) {
        successorAdapter?.revoke();
        if (controller.operationKind === "successor-inspection") {
          controller.assertRestoreReady();
          controller.cancellationDepth = (controller.cancellationDepth ?? 0) + 1;
          try {
            await successor().stop();
            json(await (url.pathname === "/api/lock" ? controller.lock() : url.pathname === "/api/stop" ? controller.stop() : Promise.resolve({stopped:true})));
            return;
          } finally { controller.cancellationDepth--; }
        }
      }
      const actions = {
        "/api/successor/prepare": ["Inspecting the SUCCESSOR work", () => successor().prepare(input,session.csrf)],
        "/api/successor/execute": ["Authorizing the exact SUCCESSOR work", () => successor().execute(input,session.csrf)],
        "/api/successor/revoke": ["Revoking pending SUCCESSOR choices", () => successor().revoke()],
        "/api/successor/stop": ["Stopping SUCCESSOR work", () => successor().stop()],
        "/api/successor/result": ["Checking SUCCESSOR results", () => successor().result(input.key,input.review??null)],
        "/api/studio/start": ["Starting Studio work", () => controller.studio.start(input)],
        "/api/studio/cancel": ["Stopping Studio work", () => controller.studio.cancel()],
        "/api/studio/remove": ["Removing saved Studio work", () => controller.studio.remove(input.id)],
        "/api/pilot/start": [
          "Recording pilot evidence",
          () => controller.pilot.start(input),
        ],
        "/api/pilot/job": [
          "Recording pilot evidence",
          () => controller.pilot.job(input),
        ],
        "/api/pilot/intervention": [
          "Recording pilot evidence",
          () => controller.pilot.intervention(input),
        ],
        "/api/pilot/costs": [
          "Recording pilot evidence",
          () => controller.pilot.costs(input),
        ],
        "/api/pilot/finish": [
          "Recording pilot evidence",
          () => controller.pilot.finish(input),
        ],
        "/api/operations/record": [
          "Recording commissioning evidence",
          () => controller.operations.record(input),
        ],
        "/api/operations/peer": [
          "Excluding related identity",
          () => controller.operations.excludePeer(input),
        ],
        "/api/operations/probe": [
          "Checking local dependencies",
          async () => {
            await controller.operations.probe();
            return controller.operations.snapshot();
          },
        ],
        "/api/monitor/access": [
          "Creating monitoring access",
          () => ({
            schema: "agi-fleet-read-access/v1",
            role: "agent",
            url: origin() + "/api/monitor/status",
            ...controller.createReadAccess(),
          }),
        ],
        "/api/publisher/check": [
          "Checking IPFS Desktop",
          () => controller.publisherCheck(),
        ],
        "/api/companion/identity": ["Inspecting compute identity", () => controller.companionInspectIdentity()],
        "/api/companion/approve-identity": ["Approving compute identity", () => controller.approveComputeIdentity(input)],
        "/api/companion/cancel": ["Cancelling compute test", async () => { await controller.companion.cancel(); return { cancelled: true }; }],
        "/api/companion/config": [
          "Saving your AI connection",
          () => controller.saveCompanion(input),
        ],
        "/api/companion/kit": [
          "Preparing your private OpenClaw setup",
          () => controller.companionKit(input),
        ],
        "/api/companion/public-web-commissioning": ["Commissioning protected public browser", () => controller.companionPublicWebCommissioning(input)],
        "/api/companion/workstation-test": ["Testing computer work", () => controller.companionWorkstationTest()],
        "/api/companion/image-test": ["Testing image capability", () => controller.companionImageTest()],
        "/api/companion/test": [
          "Testing OpenClaw and its model",
          () => controller.companionTest(),
        ],
        "/api/companion/brief": [
          "Preparing your operating summary",
          () => controller.companionBrief(),
        ],
        "/api/companion/read-token": [
          "Creating read-only access",
          () => ({
            schema: "agi-agent-read-access/v1",
            url: origin() + "/api/companion/status",
            ...controller.createReadAccess(),
          }),
        ],
        "/api/companion/revoke": [
          "Revoking read-only access",
          () => controller.revokeReadAccess(),
        ],
        "/api/vault/create": [
          "Securing your agent",
          () => {
            limited("unlock", 5, 300000);
            return controller.createVault(input.password);
          },
        ],
        "/api/unlock": [
          "Unlocking your agent",
          () => {
            limited("unlock", 5, 300000);
            return controller.unlock(input.password);
          },
        ],
        "/api/lock": ["Stopping safely and locking", () => controller.lock()],
        "/api/config": [
          "Saving your settings",
          () => controller.saveConfig(input),
        ],
        "/api/settlement-budget": [
          "Saving reviewed settlement budgets",
          () => controller.saveSettlementBudget(input),
        ],
        "/api/rpc": [
          "Encrypting your connection",
          () => controller.saveRPC(input.url, input.verificationURL),
        ],
        "/api/wallet/create": [
          "Creating your dedicated wallet",
          () => controller.wallet("create", input),
        ],
        "/api/wallet/phrase": ["Recovering your seed wallet", () => controller.wallet("phrase", input)],
        "/api/wallet/reveal": ["Opening wallet recovery", () => controller.revealRecovery(input.password)],
        "/api/wallet/confirm": ["Checking your recovery copy", () => controller.confirmRecovery(input)],
        "/api/wallet/import": [
          "Importing your encrypted wallet",
          () => controller.wallet("import", input),
        ],
        "/api/discover": [
          "Checking the creation transaction",
          () => controller.discover(input.transactionHash),
        ],
        "/api/enroll": [
          "Verifying the manager and eight libraries",
          () => controller.enroll(),
        ],
        "/api/check": [
          "Checking your agent’s readiness",
          () => controller.check(),
        ],
        "/api/activation/challenge": [
          "Preparing your authorization",
          () => controller.activationChallenge(),
        ],
        "/api/activate": [
          "Recording your chosen authority",
          () => controller.activate(input),
        ],
        "/api/start": [
          "Starting your agent",
          () => controller.start(input.mode),
        ],
        "/api/stop": ["Stopping safely", () => controller.stop()],
        "/api/resume": ["Checking before resuming", () => controller.resume()],
        "/api/remember": [
          "Updating macOS Keychain",
          () => controller.remember(input.enabled === true),
        ],
        "/api/background": [
          "Updating login preferences",
          () => controller.background(input),
        ],
        "/api/backup": [
          "Stopping safely and encrypting your backup",
          () => controller.backup(input.password, {excludeStudio:input.excludeStudio??false}),
        ],
        "/api/backup/verify": ["Verifying the selected encrypted file (read only)", () => controller.verifyBackup(input.backup,input.password)],
        "/api/preflight": ["Measuring this machine", () => controller.machinePreflight()],
        "/api/diagnostics": ["Preparing sanitized diagnostics", () => controller.diagnostics()],
        "/api/upgrade/check": ["Comparing the public wallet address", () => controller.compareUpgrade(input.expectedAddress)],
        "/api/backup/saved": [
          "Recording your backup confirmation",
          () => controller.acknowledgeBackup(),
        ],
        "/api/restore": [
          "Validating and restoring your backup",
          () =>
            controller.restore(input.backup, input.password, input.acknowledge),
        ],
        "/api/restore/check": [
          "Reconciling restored wallet history",
          () => controller.reconcileRestore(),
        ],
        "/api/reindex": [
          "Preparing a fresh event scan",
          () => controller.reindex(),
        ],
        "/api/lab": [
          "Checking the sample delivery",
          () => controller.lab(input.specification, input.delivery),
        ],
      };
      const action = actions[url.pathname];
      ensure(action, "UNKNOWN_ACTION");
      // AI requests must not prevent the operator from locking or stopping the node.
      json(
        await (["/api/companion/test", "/api/companion/brief", "/api/companion/cancel", "/api/companion/approve-identity", "/api/companion/public-web-commissioning"].includes(
          url.pathname,
        )
          ? action[1]()
          : controller.mutate(action[0], action[1], {operationKind:["/api/successor/prepare","/api/successor/execute"].includes(url.pathname)?"successor-inspection":null,interruptStudio:["/api/lock","/api/stop","/api/studio/cancel","/api/successor/stop"].includes(url.pathname)})),
      );
    } catch (error) {
      const detail = publicError(error),
        status = ["AUTH_REQUIRED", "SESSION_LINK_EXPIRED"].includes(detail.code)
          ? 401
          : /HOST|ORIGIN|CSRF/.test(detail.code)
            ? 403
            : detail.code === "OPERATION_IN_PROGRESS"
              ? 409
              : detail.code === "TOO_MANY_ATTEMPTS"
                ? 429
                : 400;
      json({ error: detail }, status);
    }
  });
  server.requestTimeout = 20000;
  server.headersTimeout = 10000;
  server.maxHeadersCount = 40;
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => {
      actualPort = server.address().port;
      resolve();
    });
  });
  return {
    server,
    port: actualPort,
    launchSecret,
    url: bootstrap(),
    bootstrap,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}
