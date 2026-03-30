#!/usr/bin/env node

const BASE_URL = process.env.OPENCLAW_BASE_URL || "http://localhost:8080";
const API_PREFIX = process.env.OPENCLAW_API_PREFIX || "/api/v1";

function endpoint(path) {
  return `${BASE_URL}${API_PREFIX}${path}`;
}

function parseArgs(argv) {
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

async function restGet(path, query = {}) {
  const url = new URL(endpoint(path));
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  const res = await fetch(url, { method: "GET" });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`GET ${url} failed: ${res.status} ${body}`);
  }
  return body;
}

async function restPost(path, payload) {
  const url = endpoint(path);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`POST ${url} failed: ${res.status} ${body}`);
  }
  return body;
}

function printHelp() {
  const lines = [
    "marketclaw CLI",
    "",
    "Usage:",
    "  npm run marketclaw -- <group> <action> [flags]",
    "  marketclaw <group> <action> [flags]",
    "",
    "Commands:",
    "  templates list",
    "    Optional: --page 0 --size 20 --sort id,asc",
    "",
    "  openclaws list",
    "",
    "  order create",
    "    Required: --requesterOpenclawId <int> --taskTemplateId <int> --title <string>",
    "    Optional: --capabilityPackageId <int> --requirementPayload '{\"k\":\"v\"}'",
    "",
    "  usage create",
    "    Required: --orderId <int> --openclawId <int> --provider <string> --providerRequestId <string>",
    "              --model <string> --promptTokens <int> --completionTokens <int>",
    "    Optional: --measuredAt <iso_time>",
    "",
    "  order settle",
    "    Required: --openclawId <int> --orderId <int>",
    "    Optional: --usageReceiptId <int> --tokenUsed <int>",
    "",
    "Legacy commands still work:",
    "  templates:list, openclaws:list, order:create, usage:create, order:settle",
    "",
    "Environment:",
    "  OPENCLAW_BASE_URL (default: http://localhost:8080)",
    "  OPENCLAW_API_PREFIX (default: /api/v1)"
  ];
  console.log(lines.join("\n"));
}

async function run() {
  const { positionals, flags } = parseArgs(process.argv.slice(2));
  const command = (() => {
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
  })();

  if (command === "help" || command === "--help" || command === "-h") {
    printHelp();
    return;
  }

  if (command === "templates:list") {
    const body = await restGet("/task-templates", {
      page: maybeInt(flags, "page"),
      size: maybeInt(flags, "size"),
      sort: flags.sort
    });
    console.log(body);
    return;
  }

  if (command === "openclaws:list") {
    const body = await restGet("/openclaws");
    console.log(body);
    return;
  }

  if (command === "order:create") {
    const payload = {
      requester_openclaw_id: mustInt(flags, "requesterOpenclawId"),
      task_template_id: mustInt(flags, "taskTemplateId"),
      capability_package_id: maybeInt(flags, "capabilityPackageId"),
      title: mustStr(flags, "title"),
      requirement_payload: maybeJson(flags, "requirementPayload", {})
    };
    const body = await restPost("/orders", payload);
    console.log(body);
    return;
  }

  if (command === "usage:create") {
    const orderId = mustInt(flags, "orderId");
    const payload = {
      openclaw_id: mustInt(flags, "openclawId"),
      provider: mustStr(flags, "provider"),
      provider_request_id: mustStr(flags, "providerRequestId"),
      model: mustStr(flags, "model"),
      prompt_tokens: mustInt(flags, "promptTokens"),
      completion_tokens: mustInt(flags, "completionTokens"),
      measured_at: flags.measuredAt
    };
    const body = await restPost(`/orders/${orderId}/usage-receipts`, payload);
    console.log(body);
    return;
  }

  if (command === "order:settle") {
    const openclawId = mustInt(flags, "openclawId");
    const orderId = mustInt(flags, "orderId");
    const usageReceiptId = maybeInt(flags, "usageReceiptId");
    const tokenUsed = maybeInt(flags, "tokenUsed");
    if (usageReceiptId === undefined && tokenUsed === undefined) {
      throw new Error("order:settle requires --usageReceiptId or --tokenUsed");
    }

    const payload = {
      usage_receipt_id: usageReceiptId,
      token_used: tokenUsed
    };
    const body = await restPost(`/openclaws/${openclawId}/orders/${orderId}/settle`, payload);
    console.log(body);
    return;
  }

  throw new Error(`Unknown command: ${command}`);
}

run().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(message);
  process.exit(1);
});
