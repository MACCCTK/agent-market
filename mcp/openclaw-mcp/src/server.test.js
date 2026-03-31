import test from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";

import {
  MISSING_TOKEN_ERROR,
  clearAuthSession,
  getAuthSession,
  loginAndCacheSession,
  restPost,
  setAuthSession,
  toolSchemas
} from "./server.js";

const VALID_OPENCLAW_ID = "11111111-1111-4111-8111-111111111111";
const VALID_TEMPLATE_ID = "22222222-2222-4222-8222-222222222222";
const VALID_PACKAGE_ID = "33333333-3333-4333-8333-333333333333";

const originalFetch = global.fetch;

test.afterEach(() => {
  clearAuthSession();
  global.fetch = originalFetch;
});

test("auth_login caches token and session metadata", async () => {
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

  const text = await loginAndCacheSession({
    email: "agent@example.com",
    password: "secret"
  });

  assert.deepEqual(getAuthSession(), {
    authenticated: true,
    tokenType: "Bearer",
    openclawId: VALID_OPENCLAW_ID,
    email: "agent@example.com"
  });
  assert.equal(JSON.parse(text).session_cached, true);
});

test("protected requests attach Authorization header", async () => {
  let authorizationHeader = null;
  setAuthSession({
    accessToken: "token-xyz",
    openclawId: VALID_OPENCLAW_ID
  });

  global.fetch = async (_url, options) => {
    authorizationHeader = options.headers.Authorization;
    return new Response("{}", { status: 200 });
  };

  await restPost(
    "/orders",
    {
      requesterOpenClawId: VALID_OPENCLAW_ID,
      taskTemplateId: VALID_TEMPLATE_ID,
      capabilityPackageId: VALID_PACKAGE_ID,
      title: "Need research",
      requirementPayload: { topic: "agent market" }
    },
    { authRequired: true }
  );

  assert.equal(authorizationHeader, "Bearer token-xyz");
});

test("protected requests fail locally when token is missing", async () => {
  let called = false;
  global.fetch = async () => {
    called = true;
    return new Response("{}", { status: 200 });
  };

  await assert.rejects(
    () => restPost("/orders", {}, { authRequired: true }),
    new RegExp(MISSING_TOKEN_ERROR.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
  );
  assert.equal(called, false);
});

test("create_order schema requires UUID strings", () => {
  const createOrderSchema = z.object(toolSchemas.create_order);

  assert.throws(() =>
    createOrderSchema.parse({
      requesterOpenClawId: 1,
      taskTemplateId: VALID_TEMPLATE_ID,
      title: "Need research",
      requirementPayload: {}
    })
  );

  assert.doesNotThrow(() =>
    createOrderSchema.parse({
      requesterOpenClawId: VALID_OPENCLAW_ID,
      taskTemplateId: VALID_TEMPLATE_ID,
      capabilityPackageId: VALID_PACKAGE_ID,
      title: "Need research",
      requirementPayload: {}
    })
  );
});
