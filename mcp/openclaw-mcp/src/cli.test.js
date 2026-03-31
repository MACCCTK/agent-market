import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import {
  SESSION_MISSING_ERROR,
  clearSession,
  loadSession,
  mustUuid,
  runCli
} from "./cli.js";

const VALID_OPENCLAW_ID = "11111111-1111-4111-8111-111111111111";
const VALID_TEMPLATE_ID = "22222222-2222-4222-8222-222222222222";
const VALID_PACKAGE_ID = "33333333-3333-4333-8333-333333333333";
const VALID_ORDER_ID = "44444444-4444-4444-8444-444444444444";

const originalFetch = global.fetch;
const originalSessionFile = process.env.OPENCLAW_SESSION_FILE;
const originalBearerToken = process.env.OPENCLAW_BEARER_TOKEN;

function silentIo() {
  return {
    stdout: () => {}
  };
}

async function withTempSessionFile() {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "marketclaw-cli-"));
  const sessionFile = path.join(tempDir, "session.json");
  process.env.OPENCLAW_SESSION_FILE = sessionFile;
  return { tempDir, sessionFile };
}

test.afterEach(async () => {
  global.fetch = originalFetch;
  if (originalSessionFile === undefined) {
    delete process.env.OPENCLAW_SESSION_FILE;
  } else {
    process.env.OPENCLAW_SESSION_FILE = originalSessionFile;
  }
  if (originalBearerToken === undefined) {
    delete process.env.OPENCLAW_BEARER_TOKEN;
  } else {
    process.env.OPENCLAW_BEARER_TOKEN = originalBearerToken;
  }
  await clearSession();
});

test("auth login stores session from backend response", async () => {
  await withTempSessionFile();
  global.fetch = async () =>
    new Response(
      JSON.stringify({
        access_token: "token-123",
        token_type: "Bearer",
        openclaw: {
          id: VALID_OPENCLAW_ID,
          email: "agent@example.com"
        }
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );

  const stdout = [];
  await runCli(["auth", "login", "--email", "agent@example.com", "--password", "secret"], {
    stdout: (text) => stdout.push(text)
  });

  const session = await loadSession();
  assert.equal(session.access_token, "token-123");
  assert.equal(session.openclaw_id, VALID_OPENCLAW_ID);
  assert.match(stdout.join("\n"), /session_saved/i);
});

test("protected command includes Authorization header from saved session", async () => {
  await withTempSessionFile();
  global.fetch = async (url, options) => {
    if (String(url).endsWith("/auth/login")) {
      return new Response(
        JSON.stringify({
          access_token: "token-abc",
          token_type: "Bearer",
          openclaw: { id: VALID_OPENCLAW_ID, email: "agent@example.com" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    assert.equal(options.headers.Authorization, "Bearer token-abc");
    return new Response("{}", { status: 200 });
  };

  await runCli(["auth", "login", "--email", "agent@example.com", "--password", "secret"], silentIo());
  await runCli([
    "order",
    "create",
    "--requesterOpenclawId",
    VALID_OPENCLAW_ID,
    "--taskTemplateId",
    VALID_TEMPLATE_ID,
    "--capabilityPackageId",
    VALID_PACKAGE_ID,
    "--title",
    "Need research",
    "--requirementPayload",
    "{\"topic\":\"agent market\"}"
  ], silentIo());
});

test("env token overrides stored session token", async () => {
  await withTempSessionFile();
  global.fetch = async () =>
    new Response(
      JSON.stringify({
        access_token: "file-token",
        token_type: "Bearer",
        openclaw: { id: VALID_OPENCLAW_ID, email: "agent@example.com" }
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );

  await runCli(["auth", "login", "--email", "agent@example.com", "--password", "secret"], silentIo());
  process.env.OPENCLAW_BEARER_TOKEN = "env-token";

  global.fetch = async (_url, options) => {
    assert.equal(options.headers.Authorization, "Bearer env-token");
    return new Response("{}", { status: 200 });
  };

  await runCli([
    "usage",
    "create",
    "--orderId",
    VALID_ORDER_ID,
    "--openclawId",
    VALID_OPENCLAW_ID,
    "--provider",
    "openai",
    "--providerRequestId",
    "req_123",
    "--model",
    "gpt-4.1-mini",
    "--promptTokens",
    "120",
    "--completionTokens",
    "80"
  ], silentIo());
});

test("mustUuid accepts UUID and rejects integer-like ids", () => {
  assert.equal(mustUuid({ requesterOpenclawId: VALID_OPENCLAW_ID }, "requesterOpenclawId"), VALID_OPENCLAW_ID);
  assert.throws(() => mustUuid({ requesterOpenclawId: "1" }, "requesterOpenclawId"));
});

test("protected command fails locally when no CLI session exists", async () => {
  const { sessionFile } = await withTempSessionFile();
  await fs.rm(sessionFile, { force: true });

  await assert.rejects(
    () =>
      runCli([
        "order",
        "create",
        "--requesterOpenclawId",
        VALID_OPENCLAW_ID,
        "--taskTemplateId",
        VALID_TEMPLATE_ID,
        "--title",
        "Need research"
      ], silentIo()),
    new RegExp(SESSION_MISSING_ERROR.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
  );
});
