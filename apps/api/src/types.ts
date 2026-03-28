export type TemplateInputOption = {
  value: string;
  label: string;
};

export type TemplateInput =
  | {
      id: string;
      label: string;
      type: "text" | "textarea" | "enum" | "multiselect" | "file";
      required: boolean;
      helpText?: string;
      options?: TemplateInputOption[];
      maxLength?: number;
    }
  | {
      id: string;
      label: string;
      type: "array";
      required: boolean;
      helpText?: string;
      minItems?: number;
      maxItems?: number;
    };

export type PricingRule = {
  basePrice: number;
  currency: string;
  adjustments?: Array<{ condition: string; deltaPercent?: number; deltaFixed?: number }>;
};

export type AcceptanceItem = {
  id: string;
  description: string;
};

export type TaskTemplate = {
  id: string;
  name: string;
  summary: string;
  inputs: TemplateInput[];
  outputs: string[];
  slaHours: number;
  pricing: PricingRule;
  acceptanceChecklist: AcceptanceItem[];
  rejectionNotes: string[];
  zeaburSkill: {
    skillId: string;
    version: string;
  };
};

export type CapabilityPackage = {
  id: string;
  ownerId: string;
  title: string;
  description: string;
  supportedTemplateIds: string[];
  skillBindings: { skillId: string; version: string }[];
  capacity: number;
  priceRange: { min: number; max: number; currency: string };
  status: "active" | "paused";
};

export type OrderState =
  | "created"
  | "accepted"
  | "in_progress"
  | "delivered"
  | "rejected"
  | "accepted_final"
  | "settled"
  | "cancelled"
  | "disputed";

export type Order = {
  id: string;
  buyerId: string;
  templateId: string;
  packageId: string;
  inputs: Record<string, unknown>;
  state: OrderState;
  escrowAmount: number;
  currency: string;
  createdAt: string;
  updatedAt: string;
  zeaburRunId?: string;
};

export type Deliverable = {
  id: string;
  orderId: string;
  version: number;
  summary: string;
  artifactUrl: string;
  submittedAt: string;
};

export type Owner = {
  id: string;
  displayName: string;
  avatar?: string;
  capabilityPackages: string[];
  skillIds: string[];
  bio: string;
  timezone: string;
};

export type ZeaburSkill = {
  id: string;
  name: string;
  description: string;
  version: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
};
