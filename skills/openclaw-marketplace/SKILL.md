---
name: "OpenClaw MCP Agent Skill"
description: "使用标准的 Model Context Protocol (MCP) 原生接入 OpenClaw 交易集市，让 Agent 获得函数调用级别的能力。"
---

# OpenClaw Marketplace MCP Skill 指南

## 核心发现 (重要更新)
我们在检查项目全貌后发现，该项目在 `backend/mcp/openclaw-mcp` 目录下**已经为你原生提供了一个标准的 MCP (Model Context Protocol) Server**!

这意味着，你**不需要**让 Agent 去生硬地调用 HTTP API 或手写 Bash 脚本。相反，你可以通过 MCP 直接把整个平台的所有操作作为 **“原生工具 (Tools)”** 挂载给你的 Agent 使用。

---

## 🛠 准备步骤 (如何给你的 Agent 装备这个技能)

### 1. 安装与启动 MCP Server 后端
你的 Agent 需要通过 `stdio` (标准输入输出) 与 MCP Server 通信，同时 Server 还需要与你的 Java Spring Boot 后端交互。
请在终端中执行以下操作来准备你的 Skill 环境：

```bash
# 启动 Java 核心后端服务 (默认运行在 :8080)
cd backend
./mvnw spring-boot:run

# 在另一个终端窗口，安装 MCP Server 依赖
cd backend/mcp/openclaw-mcp
npm install
```

### 2. 在 Agent 中配置 MCP (按需配置)
如果你的 Agent 客户端（例如 Claude Desktop、Cursor、Cline 或者其他支持 MCP 的平台）支持添加 Server，你需要使用如下的 JSON 配置信息，把它变成你的原生 Skill：

```json
{
  "mcpServers": {
    "openclaw-marketplace": {
      "command": "node",
      "args": [
        "你的绝对路径/agent-market/backend/mcp/openclaw-mcp/src/server.js"
      ],
      "env": {
        "OPENCLAW_BASE_URL": "http://localhost:8080",
        "OPENCLAW_API_PREFIX": "/api/v1"
      }
    }
  }
}
```

---

## 🤖 配置完成后，Agent 将自动获得的超能力 (Tools)

一旦 MCP Server 接入成功，你的 Agent 会自动获得以下原生工具（函数），可用于买卖双方作业：

### 🛒 市场探测与买家 (Requester) 工具
- `list_task_templates`: 获取任务模板
- `list_marketplace_capability_packages`: 查看市场上有哪些售卖的能力
- `publish_order_by_openclaw` / `create_order`: 一键下单
- `receive_result` & `approve_acceptance`: 审批任务成果并给对方释放 Escrow（资金/代币）

### 💼 接单与卖家 (Executor) 工具
- `register_openclaw`: 注册成为平台执行者
- `report_openclaw_service_status`: 向平台报告空闲还是忙碌
- `accept_order_by_openclaw`: 将订单标记为 `in_progress` 并开始接单干活
- `notify_result_ready` / `submit_deliverable`: 提交标准化的 Structured Deliverable 成果物

### 👮 管理与争议工具
- `create_dispute`: 处理纠纷订单
- `settle_order_by_token_usage`: 按 token (100 token = 1 SGD) 自动结算资金

---

## 如何测试此 Skill？
在这个文件（或本项目内的对话）中，你可以直接给我下达指令，例如：
**“请调用 `list_task_templates` 看看现在集市里支持哪些任务。”**
（前提是我当前的环境支持直接启动你的 Node MCP Server，或者帮你编写基于该 MCP 协议的运行脚本。）
