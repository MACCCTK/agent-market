import { cache } from "react";
import { buildMarketplaceViewModel } from "../data/market";

const API_BASE_URL = process.env.MARKETPLACE_API_BASE_URL ?? "http://43.155.185.40:8080/api/v1";

function toNonNegativeInt(value) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number) || number < 0) {
    return 0;
  }
  return Math.floor(number);
}

function ensureUsageIntegrity(usage) {
  if (!usage.providerRequestId) {
    throw new Error("providerRequestId is required");
  }
  if (!usage.model) {
    throw new Error("model is required");
  }
  if (usage.totalTokens !== usage.promptTokens + usage.completionTokens) {
    throw new Error("totalTokens must equal promptTokens + completionTokens");
  }
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...options
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json();
}

export const getMarketplaceViewModel = cache(async () => {
  try {
    const [openClaws, templates, capabilityPackages] = await Promise.all([
      requestJson("/openclaws"),
      requestJson("/task-templates?page=0&size=200&sort=id,asc"),
      requestJson("/marketplace/capability-packages?page=0&size=200&sort=id,asc")
    ]);

    return buildMarketplaceViewModel({
      openClaws,
      templates,
      capabilityPackages
    });
  } catch (error) {
    return buildMarketplaceViewModel({
      backendUnavailable: true,
      errorMessage: error instanceof Error ? error.message : "Unknown backend error"
    });
  }
});

// OpenAI Chat Completions + Responses API compatible usage normalizer.
export function normalizeOpenAIUsage(response) {
  const usage = response?.usage || {};
  const promptTokens = toNonNegativeInt(usage.prompt_tokens ?? usage.input_tokens);
  const completionTokens = toNonNegativeInt(usage.completion_tokens ?? usage.output_tokens);
  const totalTokens = toNonNegativeInt(usage.total_tokens ?? promptTokens + completionTokens);

  const normalized = {
    provider: "openai",
    providerRequestId: String(response?.id || ""),
    model: String(response?.model || ""),
    promptTokens,
    completionTokens,
    totalTokens,
    measuredAt: new Date().toISOString()
  };

  ensureUsageIntegrity(normalized);
  return normalized;
}

export function normalizeAnthropicUsage(response) {
  const usage = response?.usage || {};
  const promptTokens = toNonNegativeInt(usage.input_tokens);
  const completionTokens = toNonNegativeInt(usage.output_tokens);
  const totalTokens = promptTokens + completionTokens;

  const normalized = {
    provider: "anthropic",
    providerRequestId: String(response?.id || ""),
    model: String(response?.model || ""),
    promptTokens,
    completionTokens,
    totalTokens,
    measuredAt: new Date().toISOString()
  };

  ensureUsageIntegrity(normalized);
  return normalized;
}

export async function createTokenUsageReceipt(orderId, openclawId, usage) {
  return requestJson(`/orders/${orderId}/usage-receipts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      openclaw_id: openclawId,
      provider: usage.provider,
      provider_request_id: usage.providerRequestId,
      model: usage.model,
      prompt_tokens: usage.promptTokens,
      completion_tokens: usage.completionTokens,
      measured_at: usage.measuredAt
    })
  });
}

export async function settleOrderByUsageReceipt(openclawId, orderId, usageReceiptId) {
  return requestJson(`/openclaws/${openclawId}/orders/${orderId}/settle`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      usage_receipt_id: usageReceiptId
    })
  });
}
