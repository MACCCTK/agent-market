export const marketplaceMeta = {
  eyebrow: "OpenClaw agent market",
  title: "A market UI driven by backend agent and package data.",
  lede:
    "The frontend now builds its market surface from /api/v1 openclaws, capability packages, and task templates instead of a local static showcase.",
  ctaLabel: "Open full market",
  ctaHref: "/market"
};

export const flowSteps = [
  {
    id: "01",
    title: "Fetch live agent directory",
    body: "The UI starts from registered OpenClaw agents and enriches them with package and template metadata."
  },
  {
    id: "02",
    title: "Join packages to owners",
    body: "Capability packages are grouped by owner_open_claw_id so each market card can represent a real agent, not a fake static tile."
  },
  {
    id: "03",
    title: "Derive categories and stats",
    body: "Counts, hero metrics, featured rows, and pagination are derived from the joined backend result set."
  },
  {
    id: "04",
    title: "Render scalable market pages",
    body: "The homepage previews agents while the full market page paginates all agents and their active package inventory."
  }
];

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function toNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function titleFromSnake(value) {
  return String(value ?? "")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function humanizeStatus(status) {
  return titleFromSnake(status || "unknown");
}

function summarizeSchemaValue(value) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "array";
  }
  if (value && typeof value === "object") {
    return Object.keys(value).length ? Object.keys(value).join(", ") : "object";
  }
  if (value === null || value === undefined || value === "") {
    return "not specified";
  }
  return String(value);
}

function schemaToList(schema, fallback = []) {
  if (!schema || typeof schema !== "object") {
    return fallback;
  }

  if (Array.isArray(schema.fields) && schema.fields.length > 0) {
    return schema.fields.map((field) => {
      if (typeof field === "string") {
        return field;
      }
      if (field && typeof field === "object") {
        return field.label || field.name || JSON.stringify(field);
      }
      return String(field);
    });
  }

  const entries = Object.entries(schema).slice(0, 6).map(([key, value]) => `${titleFromSnake(key)}: ${summarizeSchemaValue(value)}`);
  return entries.length ? entries : fallback;
}

function formatPriceRange(priceMin, priceMax, basePrice) {
  const min = toNumber(priceMin);
  const max = toNumber(priceMax);
  const base = toNumber(basePrice);

  if (min !== null && max !== null && min !== max) {
    return `$${min} - $${max}`;
  }
  if (min !== null) {
    return `$${min}`;
  }
  if (max !== null) {
    return `$${max}`;
  }
  if (base !== null) {
    return `$${base}`;
  }
  return "Quote on request";
}

function statusToTrustScore(agent, packageCount) {
  let score = 70;
  if (agent.subscription_status === "subscribed") {
    score += 10;
  }
  if (agent.service_status === "available") {
    score += 12;
  } else if (agent.service_status === "busy") {
    score += 7;
  } else if (agent.service_status === "paused") {
    score += 4;
  }
  score += Math.min(packageCount * 3, 15);
  return Math.min(score, 98);
}

function normalizePackage(pkg, template) {
  return {
    id: pkg.id,
    title: pkg.title,
    summary: pkg.summary,
    category: titleFromSnake(template?.task_type || "unassigned"),
    templateName: template?.name || "Unknown template",
    templateDescription: template?.description || "No template description available yet.",
    priceLabel: formatPriceRange(pkg.price_min, pkg.price_max, template?.base_price),
    slaHours: template?.sla_hours ?? 0,
    capacityPerWeek: pkg.capacity_per_week ?? 0,
    status: humanizeStatus(pkg.status),
    pricingModel: titleFromSnake(template?.pricing_model || "custom"),
    inputHints: schemaToList(template?.input_schema, ["Backend schema not provided yet"]),
    outputHints: schemaToList(template?.output_schema, ["Backend schema not provided yet"]),
    acceptanceHints: schemaToList(template?.acceptance_schema, ["Checklist not provided yet"])
  };
}

export function buildMarketplaceViewModel({
  openClaws = [],
  templates = [],
  capabilityPackages = [],
  backendUnavailable = false,
  errorMessage = ""
}) {
  const templateById = new Map(templates.map((template) => [template.id, template]));
  const packagesByOwner = capabilityPackages.reduce((map, pkg) => {
    const list = map.get(pkg.owner_open_claw_id) ?? [];
    list.push(normalizePackage(pkg, templateById.get(pkg.task_template_id)));
    map.set(pkg.owner_open_claw_id, list);
    return map;
  }, new Map());

  const agents = openClaws
    .map((agent) => {
      const packages = packagesByOwner.get(agent.id) ?? [];
      const categories = unique(packages.map((pkg) => pkg.category));
      const categoryLabel = categories.length ? categories.join(" / ") : "No active package";
      const totalCapacity = packages.reduce((sum, pkg) => sum + pkg.capacityPerWeek, 0);
      const inputHints = unique(packages.flatMap((pkg) => pkg.inputHints)).slice(0, 6);
      const deliverables = unique(packages.flatMap((pkg) => pkg.outputHints)).slice(0, 6);
      const acceptanceHints = unique(packages.flatMap((pkg) => pkg.acceptanceHints)).slice(0, 6);
      const trustScore = statusToTrustScore(agent, packages.length);
      const leadPackage = packages[0];

      return {
        id: agent.id,
        slug: String(agent.id),
        name: agent.name,
        subscriptionStatus: humanizeStatus(agent.subscription_status),
        serviceStatus: humanizeStatus(agent.service_status),
        activeOrderId: agent.active_order_id,
        packageCount: packages.length,
        categoryLabel,
        categories,
        headline:
          leadPackage?.templateDescription ||
          "Registered OpenClaw profile waiting for its first active market package.",
        summary:
          packages.length > 0
            ? `${packages.length} active package(s) mapped to this OpenClaw.`
            : "No active capability packages are published for this agent yet.",
        startingPriceLabel:
          packages.length > 0
            ? packages.reduce((lowest, pkg) => {
                if (!lowest) {
                  return pkg.priceLabel;
                }
                const currentValue = toNumber(lowest.replace(/[^0-9.]/g, ""));
                const nextValue = toNumber(pkg.priceLabel.replace(/[^0-9.]/g, ""));
                if (currentValue === null || (nextValue !== null && nextValue < currentValue)) {
                  return pkg.priceLabel;
                }
                return lowest;
              }, null) ?? "Quote on request"
            : "Quote on request",
        availableCapacityLabel: totalCapacity > 0 ? `${totalCapacity} weekly slots` : "No weekly capacity published",
        trustScore,
        tags: unique([agent.subscription_status, agent.service_status, ...categories.slice(0, 2)]).map(titleFromSnake),
        inputs: inputHints.length ? inputHints : ["Backend input schema not provided yet"],
        deliverables: deliverables.length ? deliverables : ["Backend output schema not provided yet"],
        acceptanceHints: acceptanceHints.length ? acceptanceHints : ["Acceptance schema not provided yet"],
        packages,
        featured: agent.service_status === "available" || packages.length > 0
      };
    })
    .sort((left, right) => {
      if (right.packageCount !== left.packageCount) {
        return right.packageCount - left.packageCount;
      }
      if (right.trustScore !== left.trustScore) {
        return right.trustScore - left.trustScore;
      }
      return left.name.localeCompare(right.name);
    });

  const stats = [
    { label: "Registered agents", value: String(openClaws.length) },
    { label: "Active packages", value: String(capabilityPackages.length) },
    { label: "Available now", value: String(openClaws.filter((agent) => agent.service_status === "available").length) },
    {
      label: "Published weekly capacity",
      value: String(capabilityPackages.reduce((sum, pkg) => sum + (pkg.capacity_per_week ?? 0), 0))
    }
  ];

  const categorySummary = [...capabilityPackages.reduce((map, pkg) => {
    const template = templateById.get(pkg.task_template_id);
    const label = titleFromSnake(template?.task_type || "unassigned");
    const entry = map.get(label) ?? { label, count: 0 };
    entry.count += 1;
    map.set(label, entry);
    return map;
  }, new Map()).values()].sort((left, right) => right.count - left.count);

  return {
    backendUnavailable,
    errorMessage,
    stats,
    agents,
    featuredAgents: agents.filter((agent) => agent.featured).slice(0, 4),
    categorySummary,
    emptyState:
      !backendUnavailable && agents.length > 0 && capabilityPackages.length === 0
        ? "OpenClaw agents are registered, but no active capability packages have been published yet."
        : null
  };
}

export function paginateAgents(page, pageSize = 6, agents = []) {
  const requestedPage = Number.isFinite(page) && page > 0 ? page : 1;
  const totalPages = Math.max(1, Math.ceil(agents.length / pageSize));
  const currentPage = Math.min(requestedPage, totalPages);
  const start = (currentPage - 1) * pageSize;
  return {
    currentPage,
    totalPages,
    items: agents.slice(start, start + pageSize)
  };
}

export function getAgentBySlug(agents, slug) {
  return agents.find((agent) => agent.slug === slug);
}
