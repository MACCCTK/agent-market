const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:4000";

type FetchOptions = {
  cache?: RequestCache;
  revalidate?: number;
};

async function request<T>(path: string, options?: RequestInit & FetchOptions): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    },
    next: options?.revalidate ? { revalidate: options.revalidate } : undefined,
    cache: options?.cache
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listTemplates: () => request<{ data: TemplateSummary[] }>("/templates", { cache: "no-store" }),
  getTemplate: (id: string) => request<{ data: TemplateDetail }>(`/templates/${id}`, { cache: "no-store" }),
  listOrders: () => request<{ data: OrderSummary[] }>("/orders", { cache: "no-store" }),
  getOrder: (id: string) => request<{ data: OrderDetail }>(`/orders/${id}`, { cache: "no-store" }),
  listOwners: () => request<{ data: OwnerSummary[] }>("/owners", { cache: "no-store" }),
  listPackages: () => request<{ data: CapabilityPackageSummary[] }>("/capability-packages", { cache: "no-store" }),
  listSkills: () => request<{ data: ZeaburSkillSummary[] }>("/zeabur/skills", { cache: "no-store" })
};

export type TemplateSummary = {
  id: string;
  name: string;
  summary: string;
  slaHours: number;
  pricing: { basePrice: number; currency: string };
};

export type TemplateDetail = TemplateSummary & {
  inputs: Array<{ id: string; label: string; type: string; required: boolean }>;
  outputs: string[];
  acceptanceChecklist: Array<{ id: string; description: string }>;
  rejectionNotes: string[];
  zeaburSkill: { skillId: string; version: string };
};

export type OrderSummary = {
  id: string;
  templateId: string;
  state: string;
  escrowAmount: number;
  currency: string;
  updatedAt: string;
};

export type OrderDetail = OrderSummary & {
  packageId: string;
  buyerId: string;
  deliverables?: Array<{ id: string; summary: string; artifactUrl: string }>;
};

export type OwnerSummary = {
  id: string;
  displayName: string;
  bio: string;
  timezone: string;
  capabilityPackages: string[];
};

export type CapabilityPackageSummary = {
  id: string;
  ownerId: string;
  title: string;
  description: string;
  capacity: number;
  supportedTemplateIds: string[];
  priceRange: { min: number; max: number; currency: string };
  skillBindings: Array<{ skillId: string; version: string }>;
};

export type ZeaburSkillSummary = {
  id: string;
  name: string;
  description: string;
  version: string;
};
