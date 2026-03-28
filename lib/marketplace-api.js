import { cache } from "react";
import { buildMarketplaceViewModel } from "../data/market";

const API_BASE_URL = process.env.MARKETPLACE_API_BASE_URL ?? "http://43.155.185.40:8080/api/v1";

async function requestJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store"
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
