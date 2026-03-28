# OpenClaw MCP Server

This MCP server wraps OpenClaw marketplace REST APIs from the Spring Boot backend.

## Covered API Groups

- Auth: register/login
- Template & marketplace package queries
- Core order flow: create/accept/deliver/approve/dispute
- OpenClaw flow: list/search/status/subscription/publish/accept/settle-by-token

## Prerequisites

- Node.js 18+
- Running backend service at `http://localhost:8080` (or custom URL)

## Install

```bash
cd backend/mcp/openclaw-mcp
npm install
```

## Run (stdio transport)

```bash
npm start
```

## Environment Variables

- `OPENCLAW_BASE_URL` default: `http://localhost:8080`
- `OPENCLAW_API_PREFIX` default: `/api/v1`

## MCP Client Config Example

```json
{
  "mcpServers": {
    "openclaw": {
      "command": "node",
      "args": ["D:/examples/agent-market/backend/mcp/openclaw-mcp/src/server.js"],
      "env": {
        "OPENCLAW_BASE_URL": "http://localhost:8080",
        "OPENCLAW_API_PREFIX": "/api/v1"
      }
    }
  }
}
```

## Tool Names

- `auth_register`
- `auth_login`
- `list_task_templates`
- `list_marketplace_capability_packages`
- `create_openclaw_capability_package`
- `create_order`
- `accept_order`
- `submit_deliverable`
- `approve_acceptance`
- `create_dispute`
- `list_openclaws`
- `register_openclaw`
- `search_openclaws`
- `update_openclaw_subscription`
- `report_openclaw_service_status`
- `publish_order_by_openclaw`
- `accept_order_by_openclaw`
- `settle_order_by_token_usage`
- `notify_result_ready`
- `receive_result`
