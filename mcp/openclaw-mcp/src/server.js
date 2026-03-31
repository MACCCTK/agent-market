import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import http from "node:http";
import { pathToFileURL } from "node:url";
import { z } from "zod";

const BASE_URL = process.env.OPENCLAW_BASE_URL || "http://localhost:8080";
const API_PREFIX = process.env.OPENCLAW_API_PREFIX || "/api/v1";
const MCP_TRANSPORT = (process.env.MCP_TRANSPORT || "stdio").toLowerCase();
const MCP_HOST = process.env.MCP_HOST || "127.0.0.1";
const MCP_PORT = Number(process.env.MCP_PORT || 8787);

export const MISSING_TOKEN_ERROR = "No bearer token loaded. Call auth_login or auth_set_token first.";
export const uuidSchema = z.string().uuid();

const sessionState = {
  accessToken: null,
  tokenType: null,
  openclawId: null,
  email: null
};

function endpoint(path) {
  return `${BASE_URL}${API_PREFIX}${path}`;
}

function toSnakeKey(key) {
  return key.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
}

function toSnakeCase(value) {
  if (Array.isArray(value)) {
    return value.map(toSnakeCase);
  }
  if (value && typeof value === "object" && value.constructor === Object) {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [toSnakeKey(key), toSnakeCase(nestedValue)])
    );
  }
  return value;
}

function textContent(text) {
  return { content: [{ type: "text", text }] };
}

function parseJson(raw, context) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${context} returned invalid JSON: ${raw}` , { cause: error });
  }
}

function authorizationHeaderValue() {
  if (!sessionState.accessToken) {
    throw new Error(MISSING_TOKEN_ERROR);
  }
  return `${sessionState.tokenType || "Bearer"} ${sessionState.accessToken}`;
}

export function clearAuthSession() {
  sessionState.accessToken = null;
  sessionState.tokenType = null;
  sessionState.openclawId = null;
  sessionState.email = null;
}

export function setAuthSession({
  accessToken,
  tokenType = "Bearer",
  openclawId = null,
  email = null
}) {
  sessionState.accessToken = accessToken;
  sessionState.tokenType = tokenType || "Bearer";
  sessionState.openclawId = openclawId;
  sessionState.email = email;
}

export function getAuthSession() {
  return {
    authenticated: Boolean(sessionState.accessToken),
    tokenType: sessionState.tokenType,
    openclawId: sessionState.openclawId,
    email: sessionState.email
  };
}

function sessionSummaryText(extra = {}) {
  return JSON.stringify({ ...getAuthSession(), ...extra }, null, 2);
}

export async function restGet(path, query = {}, options = {}) {
  const url = new URL(endpoint(path));
  Object.entries(toSnakeCase(query)).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  const headers = {};
  if (options.authRequired) {
    headers.Authorization = authorizationHeaderValue();
  }

  const res = await fetch(url, {
    method: "GET",
    headers
  });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`GET ${url} failed: ${res.status} ${body}`);
  }
  return body;
}

export async function restPost(path, payload, options = {}) {
  const url = endpoint(path);
  const headers = {
    "Content-Type": "application/json"
  };
  if (options.authRequired) {
    headers.Authorization = authorizationHeaderValue();
  }

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(toSnakeCase(payload ?? {}))
  });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`POST ${url} failed: ${res.status} ${body}`);
  }
  return body;
}

export async function loginAndCacheSession(args) {
  const raw = await restPost("/auth/login", args);
  const payload = parseJson(raw, "auth_login");
  if (typeof payload.access_token !== "string" || payload.access_token.length === 0) {
    throw new Error(`auth_login response missing access_token: ${raw}`);
  }

  setAuthSession({
    accessToken: payload.access_token,
    tokenType: typeof payload.token_type === "string" ? payload.token_type : "Bearer",
    openclawId: payload?.openclaw?.id ?? null,
    email: payload?.openclaw?.email ?? args.email
  });

  return JSON.stringify({ ...payload, session_cached: true }, null, 2);
}

export const toolSchemas = {
  auth_register: {
    email: z.string().email(),
    password: z.string().min(1),
    displayName: z.string().min(1),
    roles: z.array(z.string()).optional(),
    clientType: z.string().optional()
  },
  auth_login: {
    email: z.string().email(),
    password: z.string().min(1),
    asRole: z.string().optional(),
    clientType: z.string().optional()
  },
  auth_set_token: {
    accessToken: z.string().min(1),
    tokenType: z.string().min(1).optional(),
    openclawId: uuidSchema.optional(),
    email: z.string().min(1).optional()
  },
  list_task_templates: {
    page: z.number().int().min(0).optional(),
    size: z.number().int().min(1).optional(),
    sort: z.string().optional()
  },
  list_marketplace_capability_packages: {
    page: z.number().int().min(0).optional(),
    size: z.number().int().min(1).optional(),
    sort: z.string().optional()
  },
  create_openclaw_capability_package: {
    ownerOpenClawId: uuidSchema,
    title: z.string().min(1),
    summary: z.string().min(1),
    taskTemplateId: uuidSchema,
    sampleDeliverables: z.record(z.any()).optional(),
    priceMin: z.number().optional(),
    priceMax: z.number().optional(),
    capacityPerWeek: z.number().int().min(1),
    status: z.string().min(1)
  },
  create_order: {
    requesterOpenClawId: uuidSchema,
    taskTemplateId: uuidSchema,
    capabilityPackageId: uuidSchema.optional(),
    title: z.string().min(1),
    requirementPayload: z.record(z.any())
  },
  accept_order: {
    id: uuidSchema
  },
  submit_deliverable: {
    id: uuidSchema,
    deliveryNote: z.string().min(1),
    deliverablePayload: z.record(z.any()),
    submittedByOpenClawId: uuidSchema
  },
  approve_acceptance: {
    id: uuidSchema,
    requesterOpenClawId: uuidSchema,
    checklistResult: z.record(z.any()),
    comment: z.string().optional()
  },
  create_dispute: {
    id: uuidSchema,
    openedByOpenClawId: uuidSchema,
    reasonCode: z.string().min(1),
    description: z.string().min(1)
  },
  register_openclaw: {
    id: uuidSchema.optional(),
    name: z.string().min(1),
    capacityPerWeek: z.number().int().min(1),
    serviceConfig: z.record(z.any()),
    subscriptionStatus: z.enum(["subscribed", "unsubscribed"]),
    serviceStatus: z.enum(["available", "busy", "offline", "paused"])
  },
  search_openclaws: {
    keyword: z.string().optional(),
    page: z.number().int().min(0).optional(),
    size: z.number().int().min(1).optional()
  },
  update_openclaw_subscription: {
    id: uuidSchema,
    subscriptionStatus: z.enum(["subscribed", "unsubscribed"])
  },
  report_openclaw_service_status: {
    id: uuidSchema,
    serviceStatus: z.enum(["available", "busy", "offline", "paused"]),
    activeOrderId: uuidSchema.optional()
  },
  publish_order_by_openclaw: {
    id: uuidSchema,
    taskTemplateId: uuidSchema,
    capabilityPackageId: uuidSchema.optional(),
    title: z.string().min(1),
    requirementPayload: z.record(z.any())
  },
  accept_order_by_openclaw: {
    id: uuidSchema,
    orderId: uuidSchema
  },
  settle_order_by_token_usage: {
    id: uuidSchema,
    orderId: uuidSchema,
    tokenUsed: z.number().int().min(0).optional(),
    usageReceiptId: uuidSchema.optional()
  },
  create_token_usage_receipt: {
    orderId: uuidSchema,
    openclawId: uuidSchema,
    provider: z.string().min(1),
    providerRequestId: z.string().min(1),
    model: z.string().min(1),
    promptTokens: z.number().int().min(0),
    completionTokens: z.number().int().min(0),
    measuredAt: z.string().optional()
  },
  notify_result_ready: {
    id: uuidSchema,
    orderId: uuidSchema,
    resultSummary: z.record(z.any())
  },
  receive_result: {
    id: uuidSchema,
    orderId: uuidSchema,
    checklistResult: z.record(z.any()),
    note: z.string().optional()
  }
};

const server = new McpServer({
  name: "openclaw-marketplace-mcp",
  version: "0.1.0"
});

server.tool(
  "auth_register",
  toolSchemas.auth_register,
  async (args) => textContent(await restPost("/auth/register", args))
);

server.tool(
  "auth_login",
  toolSchemas.auth_login,
  async (args) => textContent(await loginAndCacheSession(args))
);

server.tool(
  "auth_set_token",
  toolSchemas.auth_set_token,
  async (args) => {
    setAuthSession(args);
    return textContent(sessionSummaryText({ session_updated: true }));
  }
);

server.tool("auth_current_session", {}, async () => textContent(sessionSummaryText()));

server.tool(
  "auth_clear_token",
  {},
  async () => {
    clearAuthSession();
    return textContent(sessionSummaryText({ session_cleared: true }));
  }
);

server.tool(
  "list_task_templates",
  toolSchemas.list_task_templates,
  async (args) => textContent(await restGet("/task-templates", args))
);

server.tool(
  "list_marketplace_capability_packages",
  toolSchemas.list_marketplace_capability_packages,
  async (args) => textContent(await restGet("/marketplace/capability-packages", args))
);

server.tool(
  "create_openclaw_capability_package",
  toolSchemas.create_openclaw_capability_package,
  async (args) => textContent(await restPost("/openclaws/capability-packages", args, { authRequired: true }))
);

server.tool(
  "create_order",
  toolSchemas.create_order,
  async (args) => textContent(await restPost("/orders", args, { authRequired: true }))
);

server.tool(
  "accept_order",
  toolSchemas.accept_order,
  async (args) => textContent(await restPost(`/orders/${args.id}/accept`, {}, { authRequired: true }))
);

server.tool(
  "submit_deliverable",
  toolSchemas.submit_deliverable,
  async (args) => {
    const { id, ...payload } = args;
    return textContent(await restPost(`/orders/${id}/deliverables`, payload, { authRequired: true }));
  }
);

server.tool(
  "approve_acceptance",
  toolSchemas.approve_acceptance,
  async (args) => {
    const { id, ...payload } = args;
    return textContent(await restPost(`/orders/${id}/acceptance/approve`, payload, { authRequired: true }));
  }
);

server.tool(
  "create_dispute",
  toolSchemas.create_dispute,
  async (args) => {
    const { id, ...payload } = args;
    return textContent(await restPost(`/orders/${id}/disputes`, payload, { authRequired: true }));
  }
);

server.tool("list_openclaws", {}, async () => textContent(await restGet("/openclaws")));

server.tool(
  "register_openclaw",
  toolSchemas.register_openclaw,
  async (args) => textContent(await restPost("/openclaws/register", args))
);

server.tool(
  "search_openclaws",
  toolSchemas.search_openclaws,
  async (args) => textContent(await restGet("/openclaws/search", args))
);

server.tool(
  "update_openclaw_subscription",
  toolSchemas.update_openclaw_subscription,
  async (args) => {
    const { id, ...payload } = args;
    return textContent(await restPost(`/openclaws/${id}/subscription`, payload, { authRequired: true }));
  }
);

server.tool(
  "report_openclaw_service_status",
  toolSchemas.report_openclaw_service_status,
  async (args) => {
    const { id, ...payload } = args;
    return textContent(await restPost(`/openclaws/${id}/service-status`, payload, { authRequired: true }));
  }
);

server.tool(
  "publish_order_by_openclaw",
  toolSchemas.publish_order_by_openclaw,
  async (args) => {
    const { id, ...payload } = args;
    return textContent(await restPost(`/openclaws/${id}/orders`, payload, { authRequired: true }));
  }
);

server.tool(
  "accept_order_by_openclaw",
  toolSchemas.accept_order_by_openclaw,
  async (args) => textContent(await restPost(`/openclaws/${args.id}/orders/${args.orderId}/accept`, {}, { authRequired: true }))
);

server.tool(
  "settle_order_by_token_usage",
  toolSchemas.settle_order_by_token_usage,
  async (args) => {
    const { id, orderId, tokenUsed, usageReceiptId } = args;
    if (tokenUsed === undefined && usageReceiptId === undefined) {
      throw new Error("tokenUsed or usageReceiptId is required");
    }

    const payload = {};
    if (tokenUsed !== undefined) {
      payload.tokenUsed = tokenUsed;
    }
    if (usageReceiptId !== undefined) {
      payload.usageReceiptId = usageReceiptId;
    }
    return textContent(await restPost(`/openclaws/${id}/orders/${orderId}/settle`, payload, { authRequired: true }));
  }
);

server.tool(
  "create_token_usage_receipt",
  toolSchemas.create_token_usage_receipt,
  async (args) => {
    const { orderId, ...payload } = args;
    return textContent(await restPost(`/orders/${orderId}/usage-receipts`, payload, { authRequired: true }));
  }
);

server.tool(
  "notify_result_ready",
  toolSchemas.notify_result_ready,
  async (args) => {
    const { id, orderId, resultSummary } = args;
    return textContent(
      await restPost(`/openclaws/${id}/orders/${orderId}/notify-result-ready`, { resultSummary }, { authRequired: true })
    );
  }
);

server.tool(
  "receive_result",
  toolSchemas.receive_result,
  async (args) => {
    const { id, orderId, checklistResult, note } = args;
    return textContent(
      await restPost(`/openclaws/${id}/orders/${orderId}/receive-result`, { checklistResult, note }, { authRequired: true })
    );
  }
);

async function startStdio() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

async function startHttp() {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined
  });

  await server.connect(transport);

  const httpServer = http.createServer(async (req, res) => {
    const reqUrl = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);

    if (reqUrl.pathname !== "/mcp") {
      res.statusCode = 404;
      res.end("Not Found");
      return;
    }

    if (req.method !== "GET" && req.method !== "POST") {
      res.statusCode = 405;
      res.setHeader("Allow", "GET, POST");
      res.end("Method Not Allowed");
      return;
    }

    try {
      await transport.handleRequest(req, res);
    } catch (error) {
      if (!res.headersSent) {
        res.statusCode = 500;
      }
      res.end(error instanceof Error ? error.message : String(error));
    }
  });

  httpServer.listen(MCP_PORT, MCP_HOST, () => {
    console.error(`OpenClaw MCP server listening on http://${MCP_HOST}:${MCP_PORT}/mcp`);
  });
}

function isMainModule() {
  if (!process.argv[1]) {
    return false;
  }
  return import.meta.url === pathToFileURL(process.argv[1]).href;
}

if (isMainModule()) {
  if (["http", "streamable-http", "sse"].includes(MCP_TRANSPORT)) {
    await startHttp();
  } else {
    await startStdio();
  }
}

export { server };
