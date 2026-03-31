#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const BASE_URL = process.env.OPENCLAW_BASE_URL || "http://localhost:8080";
const API_PREFIX = process.env.OPENCLAW_API_PREFIX || "/api/v1";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const SESSION_MISSING_ERROR =
  "No active CLI session. Run marketclaw auth login or set OPENCLAW_BEARER_TOKEN.";

function endpoint(pathname) {
  return `${BASE_URL}${API_PREFIX}${pathname}`;
}

export function parseArgs(argv) {
  const positionals = [];
  const flags = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      positionals.push(token);
      continue;
    }

    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      flags[key] = true;
      continue;
    }

    flags[key] = next;
    i += 1;
  }

  return { positionals, flags };
}

function currentCommand(positionals) {
  if (!positionals.length) {
    return "help";
  }

  const first = positionals[0];
  if (first.includes(":")) {
    return first;
  }

  const second = positionals[1];
  if (second && !second.startsWith("--")) {
    return `${first}:${second}`;
  }

  return first;
}

function mustInt(flags, key) {
  const raw = flags[key];
  if (raw === undefined) {
    throw new Error(`Missing required flag --${key}`);
  }
  const parsed = Number(raw);
  if (!Number.isInteger(parsed)) {
    throw new Error(`--${key} must be an integer`);
  }
  return parsed;
}

function maybeInt(flags, key) {
  const raw = flags[key];
  if (raw === undefined) {
    return undefined;
  }
  const parsed = Number(raw);
  if (!Number.isInteger(parsed)) {
    throw new Error(`--${key} must be an integer`);
  }
  return parsed;
}

export function mustUuid(flags, key) {
  const raw = flags[key];
  if (raw === undefined || String(raw).trim() === "") {
    throw new Error(`Missing required flag --${key}`);
  }
  const value = String(raw).trim();
  if (!UUID_PATTERN.test(value)) {
    throw new Error(`--${key} must be a UUID`);
  }
  return value;
}

function maybeUuid(flags, key) {
  const raw = flags[key];
  if (raw === undefined || String(raw).trim() === "") {
    return undefined;
  }
  const value = String(raw).trim();
  if (!UUID_PATTERN.test(value)) {
    throw new Error(`--${key} must be a UUID`);
  }
  return value;
}

function mustStr(flags, key) {
  const raw = flags[key];
  if (raw === undefined || String(raw).trim() === "") {
    throw new Error(`Missing required flag --${key}`);
  }
  return String(raw);
}

function maybeJson(flags, key, fallback = {}) {
  const raw = flags[key];
  if (raw === undefined) {
    return fallback;
  }
  try {
    return JSON.parse(String(raw));
  } catch {
    throw new Error(`--${key} must be valid JSON`);
  }
}

function sessionFilePath() {
  return process.env.OPENCLAW_SESSION_FILE || path.join(os.homedir(), ".openclaw", "session.json");
}

export async function loadSession() {
  try {
    const raw = await fs.readFile(sessionFilePath(), "utf8");
    return JSON.parse(raw);
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

export async function saveSession(session) {
  const target = sessionFilePath();
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.writeFile(
    target,
    JSON.stringify(
      {
        ...session,
        saved_at: new Date().toISOString()
      },
      null,
      2
    ),
    "utf8"
  );
}

export async function clearSession() {
  await fs.rm(sessionFilePath(), { force: true });
}

async function getAuthContext() {
  const envToken = process.env.OPENCLAW_BEARER_TOKEN;
  const session = await loadSession();
  if (envToken) {
    return {
      token: envToken,
      tokenType: "Bearer",
      source: "env",
      session
    };
  }
  if (session?.access_token) {
    return {
      token: session.access_token,
      tokenType: session.token_type || "Bearer",
      source: "session",
      session
    };
  }
  throw new Error(SESSION_MISSING_ERROR);
}

function parseJson(raw, context) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${context} returned invalid JSON: ${raw}`, { cause: error });
  }
}

async function restGet(pathname, query = {}, options = {}) {
  const url = new URL(endpoint(pathname));
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const headers = {};
  if (options.authRequired) {
    const auth = await getAuthContext();
    headers.Authorization = `${auth.tokenType} ${auth.token}`;
  }

  const res = await fetch(url, { method: "GET", headers });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`GET ${url} failed: ${res.status} ${body}`);
  }
  return body;
}

async function restPost(pathname, payload, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (options.authRequired) {
    const auth = await getAuthContext();
    headers.Authorization = `${auth.tokenType} ${auth.token}`;
  }

  const res = await fetch(endpoint(pathname), {
    method: "POST",
    headers,
    body: JSON.stringify(payload ?? {})
  });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`POST ${endpoint(pathname)} failed: ${res.status} ${body}`);
  }
  return body;
}

function printHelp(output = console.log) {
  const lines = [
    "marketclaw CLI",
    "",
    "Usage:",
    "  npm run marketclaw -- <group> <action> [flags]",
    "  marketclaw <group> <action> [flags]",
    "",
    "Commands:",
    "  auth login --email <string> --password <string>",
    "  auth logout",
    "  auth whoami",
    "",
    "  templates list",
    "    Optional: --page 0 --size 20 --sort id,asc",
    "",
    "  openclaws list",
    "",
    "  order create",
    "    Required: --requesterOpenclawId <uuid> --taskTemplateId <uuid> --title <string>",
    "    Optional: --capabilityPackageId <uuid> --requirementPayload '{\"k\":\"v\"}'",
    "",
    "  usage create",
    "    Required: --orderId <uuid> --openclawId <uuid> --provider <string> --providerRequestId <string>",
    "              --model <string> --promptTokens <int> --completionTokens <int>",
    "    Optional: --measuredAt <iso_time>",
    "",
    "  order settle",
    "    Required: --openclawId <uuid> --orderId <uuid>",
    "    Optional: --usageReceiptId <uuid> --tokenUsed <int>",
    "",
    "Legacy commands still work:",
    "  auth:login, auth:logout, auth:whoami, templates:list, openclaws:list, order:create, usage:create, order:settle",
    "",
    "Environment:",
    "  OPENCLAW_BASE_URL (default: http://localhost:8080)",
    "  OPENCLAW_API_PREFIX (default: /api/v1)",
    "  OPENCLAW_BEARER_TOKEN (overrides stored session)",
    "  OPENCLAW_SESSION_FILE (custom session file path)"
  ];
  output(lines.join("\n"));
}

async function authWhoAmI() {
  const session = await loadSession();
  return {
    authenticated: Boolean(process.env.OPENCLAW_BEARER_TOKEN || session?.access_token),
    token_source: process.env.OPENCLAW_BEARER_TOKEN ? "env" : session?.access_token ? "session" : "none",
    openclaw_id: session?.openclaw_id ?? null,
    email: session?.email ?? null,
    session_file: sessionFilePath(),
    env_override: Boolean(process.env.OPENCLAW_BEARER_TOKEN)
  };
}

export async function runCli(argv, io = {}) {
  const stdout = io.stdout || ((text) => console.log(text));
  const { positionals, flags } = parseArgs(argv);
  const command = currentCommand(positionals);

  if (command === "help" || command === "--help" || command === "-h") {
    printHelp(stdout);
    return;
  }

  if (command === "auth:login") {
    const email = mustStr(flags, "email");
    const password = mustStr(flags, "password");
    const raw = await restPost("/auth/login", { email, password });
    const payload = parseJson(raw, "auth login");
    if (typeof payload.access_token !== "string" || payload.access_token.length === 0) {
      throw new Error(`auth login response missing access_token: ${raw}`);
    }

    await saveSession({
      access_token: payload.access_token,
      token_type: typeof payload.token_type === "string" ? payload.token_type : "Bearer",
      openclaw_id: payload?.openclaw?.id ?? null,
      email: payload?.openclaw?.email ?? email
    });

    stdout(
      JSON.stringify(
        {
          login_succeeded: true,
          session_saved: true,
          openclaw_id: payload?.openclaw?.id ?? null,
          email: payload?.openclaw?.email ?? email,
          session_file: sessionFilePath()
        },
        null,
        2
      )
    );
    return;
  }

  if (command === "auth:logout") {
    await clearSession();
    stdout(
      JSON.stringify(
        {
          session_cleared: true,
          session_file: sessionFilePath()
        },
        null,
        2
      )
    );
    return;
  }

  if (command === "auth:whoami") {
    stdout(JSON.stringify(await authWhoAmI(), null, 2));
    return;
  }

  if (command === "templates:list") {
    const body = await restGet("/task-templates", {
      page: maybeInt(flags, "page"),
      size: maybeInt(flags, "size"),
      sort: flags.sort
    });
    stdout(body);
    return;
  }

  if (command === "openclaws:list") {
    const body = await restGet("/openclaws");
    stdout(body);
    return;
  }

  if (command === "order:create") {
    const payload = {
      requester_openclaw_id: mustUuid(flags, "requesterOpenclawId"),
      task_template_id: mustUuid(flags, "taskTemplateId"),
      capability_package_id: maybeUuid(flags, "capabilityPackageId"),
      title: mustStr(flags, "title"),
      requirement_payload: maybeJson(flags, "requirementPayload", {})
    };
    const body = await restPost("/orders", payload, { authRequired: true });
    stdout(body);
    return;
  }

  if (command === "usage:create") {
    const orderId = mustUuid(flags, "orderId");
    const payload = {
      openclaw_id: mustUuid(flags, "openclawId"),
      provider: mustStr(flags, "provider"),
      provider_request_id: mustStr(flags, "providerRequestId"),
      model: mustStr(flags, "model"),
      prompt_tokens: mustInt(flags, "promptTokens"),
      completion_tokens: mustInt(flags, "completionTokens"),
      measured_at: flags.measuredAt
    };
    const body = await restPost(`/orders/${orderId}/usage-receipts`, payload, { authRequired: true });
    stdout(body);
    return;
  }

  if (command === "order:settle") {
    const openclawId = mustUuid(flags, "openclawId");
    const orderId = mustUuid(flags, "orderId");
    const usageReceiptId = maybeUuid(flags, "usageReceiptId");
    const tokenUsed = maybeInt(flags, "tokenUsed");
    if (usageReceiptId === undefined && tokenUsed === undefined) {
      throw new Error("order:settle requires --usageReceiptId or --tokenUsed");
    }

    const payload = {
      usage_receipt_id: usageReceiptId,
      token_used: tokenUsed
    };
    const body = await restPost(`/openclaws/${openclawId}/orders/${orderId}/settle`, payload, { authRequired: true });
    stdout(body);
    return;
  }

  throw new Error(`Unknown command: ${command}`);
}

function isMainModule() {
  if (!process.argv[1]) {
    return false;
  }
  return import.meta.url === pathToFileURL(process.argv[1]).href;
}

if (isMainModule()) {
  runCli(process.argv.slice(2)).catch((error) => {
    const message = error instanceof Error ? error.message : String(error);
    console.error(message);
    process.exit(1);
  });
}
