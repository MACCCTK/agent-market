import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const BASE_URL = process.env.OPENCLAW_BASE_URL || "http://localhost:8080";
const API_PREFIX = process.env.OPENCLAW_API_PREFIX || "/api/v1";

const server = new McpServer({
  name: "openclaw-marketplace-mcp",
  version: "0.1.0"
});

function endpoint(path) {
  return `${BASE_URL}${API_PREFIX}${path}`;
}

async function restGet(path, query = {}) {
  const url = new URL(endpoint(path));
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") {
      url.searchParams.set(k, String(v));
    }
  });
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
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload ?? {})
  });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`POST ${url} failed: ${res.status} ${body}`);
  }
  return body;
}

// Auth
server.tool(
  "auth_register",
  {
    email: z.string().email(),
    password: z.string().min(1),
    displayName: z.string().min(1),
    roles: z.array(z.string()).optional(),
    clientType: z.string().optional()
  },
  async (args) => ({ content: [{ type: "text", text: await restPost("/auth/register", args) }] })
);

server.tool(
  "auth_login",
  {
    email: z.string().email(),
    password: z.string().min(1),
    asRole: z.string().optional(),
    clientType: z.string().optional()
  },
  async (args) => ({ content: [{ type: "text", text: await restPost("/auth/login", args) }] })
);

// Templates & marketplace
server.tool(
  "list_task_templates",
  {
    page: z.number().int().min(0).optional(),
    size: z.number().int().min(1).optional(),
    sort: z.string().optional()
  },
  async (args) => ({ content: [{ type: "text", text: await restGet("/task-templates", args) }] })
);

server.tool(
  "list_marketplace_capability_packages",
  {
    page: z.number().int().min(0).optional(),
    size: z.number().int().min(1).optional(),
    sort: z.string().optional()
  },
  async (args) => ({ content: [{ type: "text", text: await restGet("/marketplace/capability-packages", args) }] })
);

server.tool(
  "create_openclaw_capability_package",
  {
    ownerOpenClawId: z.number().int(),
    title: z.string().min(1),
    summary: z.string().min(1),
    taskTemplateId: z.number().int(),
    sampleDeliverables: z.record(z.any()).optional(),
    priceMin: z.number().optional(),
    priceMax: z.number().optional(),
    capacityPerWeek: z.number().int().min(1),
    status: z.string().min(1)
  },
  async (args) => ({ content: [{ type: "text", text: await restPost("/openclaws/capability-packages", args) }] })
);

// Order core
server.tool(
  "create_order",
  {
    requesterOpenClawId: z.number().int(),
    taskTemplateId: z.number().int(),
    capabilityPackageId: z.number().int().optional(),
    title: z.string().min(1),
    requirementPayload: z.record(z.any())
  },
  async (args) => ({ content: [{ type: "text", text: await restPost("/orders", args) }] })
);

server.tool(
  "accept_order",
  { id: z.number().int() },
  async (args) => ({ content: [{ type: "text", text: await restPost(`/orders/${args.id}/accept`, {}) }] })
);

server.tool(
  "submit_deliverable",
  {
    id: z.number().int(),
    deliveryNote: z.string().min(1),
    deliverablePayload: z.record(z.any()),
    submittedByOpenClawId: z.number().int()
  },
  async (args) => {
    const { id, ...payload } = args;
    return { content: [{ type: "text", text: await restPost(`/orders/${id}/deliverables`, payload) }] };
  }
);

server.tool(
  "approve_acceptance",
  {
    id: z.number().int(),
    requesterOpenClawId: z.number().int(),
    checklistResult: z.record(z.any()),
    comment: z.string().optional()
  },
  async (args) => {
    const { id, ...payload } = args;
    return { content: [{ type: "text", text: await restPost(`/orders/${id}/acceptance/approve`, payload) }] };
  }
);

server.tool(
  "create_dispute",
  {
    id: z.number().int(),
    openedByOpenClawId: z.number().int(),
    reasonCode: z.string().min(1),
    description: z.string().min(1)
  },
  async (args) => {
    const { id, ...payload } = args;
    return { content: [{ type: "text", text: await restPost(`/orders/${id}/disputes`, payload) }] };
  }
);

// OpenClaw domain
server.tool("list_openclaws", {}, async () => ({ content: [{ type: "text", text: await restGet("/openclaws") }] }));

server.tool(
  "register_openclaw",
  {
    id: z.number().int().optional(),
    name: z.string().min(1),
    capacityPerWeek: z.number().int().min(1),
    serviceConfig: z.record(z.any()),
    subscriptionStatus: z.enum(["subscribed", "unsubscribed"]),
    serviceStatus: z.enum(["available", "busy", "offline", "paused"])
  },
  async (args) => ({ content: [{ type: "text", text: await restPost("/openclaws/register", args) }] })
);

server.tool(
  "search_openclaws",
  {
    keyword: z.string().optional(),
    page: z.number().int().min(0).optional(),
    size: z.number().int().min(1).optional()
  },
  async (args) => ({ content: [{ type: "text", text: await restGet("/openclaws/search", args) }] })
);

server.tool(
  "update_openclaw_subscription",
  {
    id: z.number().int(),
    subscriptionStatus: z.enum(["subscribed", "unsubscribed"])
  },
  async (args) => {
    const { id, ...payload } = args;
    return { content: [{ type: "text", text: await restPost(`/openclaws/${id}/subscription`, payload) }] };
  }
);

server.tool(
  "report_openclaw_service_status",
  {
    id: z.number().int(),
    serviceStatus: z.enum(["available", "busy", "offline", "paused"]),
    activeOrderId: z.number().int().optional()
  },
  async (args) => {
    const { id, ...payload } = args;
    return { content: [{ type: "text", text: await restPost(`/openclaws/${id}/service-status`, payload) }] };
  }
);

server.tool(
  "publish_order_by_openclaw",
  {
    id: z.number().int(),
    taskTemplateId: z.number().int(),
    capabilityPackageId: z.number().int().optional(),
    title: z.string().min(1),
    requirementPayload: z.record(z.any())
  },
  async (args) => {
    const { id, ...payload } = args;
    return { content: [{ type: "text", text: await restPost(`/openclaws/${id}/orders`, payload) }] };
  }
);

server.tool(
  "accept_order_by_openclaw",
  {
    id: z.number().int(),
    orderId: z.number().int()
  },
  async (args) => ({ content: [{ type: "text", text: await restPost(`/openclaws/${args.id}/orders/${args.orderId}/accept`, {}) }] })
);

server.tool(
  "settle_order_by_token_usage",
  {
    id: z.number().int(),
    orderId: z.number().int(),
    tokenUsed: z.number().int().min(0)
  },
  async (args) => {
    const { id, orderId, tokenUsed } = args;
    return { content: [{ type: "text", text: await restPost(`/openclaws/${id}/orders/${orderId}/settle`, { tokenUsed }) }] };
  }
);

server.tool(
  "notify_result_ready",
  {
    id: z.number().int(),
    orderId: z.number().int(),
    resultSummary: z.record(z.any())
  },
  async (args) => {
    const { id, orderId, resultSummary } = args;
    return { content: [{ type: "text", text: await restPost(`/openclaws/${id}/orders/${orderId}/notify-result-ready`, { resultSummary }) }] };
  }
);

server.tool(
  "receive_result",
  {
    id: z.number().int(),
    orderId: z.number().int(),
    checklistResult: z.record(z.any()),
    note: z.string().optional()
  },
  async (args) => {
    const { id, orderId, checklistResult, note } = args;
    return { content: [{ type: "text", text: await restPost(`/openclaws/${id}/orders/${orderId}/receive-result`, { checklistResult, note }) }] };
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
