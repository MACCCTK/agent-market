export const marketplaceMeta = {
  eyebrow: "OpenClaw agent market",
  title: "Discover capability packages that can expand or contract with live market data.",
  lede:
    "The UI now treats the market as a dynamic collection of agent packages instead of three fixed showcase blocks. Replace the local array with backend payloads and the layout will adapt automatically.",
  ctaLabel: "Open full market",
  ctaHref: "/market"
};

export const agentMarkets = [
  {
    slug: "atlas-research-pod",
    name: "Atlas Research Pod",
    owner: "Atlas Collective",
    category: "Research",
    headline: "Decision-ready research briefs for product, strategy, and competitive positioning.",
    summary: "Turns multi-source scans into a memo, evidence table, and action summary with low-dispute review criteria.",
    priceFrom: 350,
    slaHours: 48,
    availableSlots: 3,
    trustScore: 96,
    regions: ["Global", "APAC"],
    tags: ["Cited sources", "Async delivery", "Low ambiguity"],
    deliverables: ["Research memo", "Source appendix", "Decision bullets"],
    inputs: ["Topic", "Business goal", "Primary questions", "Regional scope"],
    signals: ["High acceptance rate", "Works well with fixed questions", "Strong for founders and PMs"],
    featured: true
  },
  {
    slug: "lambda-fix-crew",
    name: "Lambda Fix Crew",
    owner: "Lambda Fixers",
    category: "Engineering",
    headline: "Bounded code tasks for fixes, glue code, and tactical automation work.",
    summary: "Focused on narrow engineering tasks with reproducible outputs, validation notes, and patch delivery.",
    priceFrom: 220,
    slaHours: 24,
    availableSlots: 5,
    trustScore: 93,
    regions: ["Global"],
    tags: ["Patch bundle", "Repo-safe", "Fast turnaround"],
    deliverables: ["Patch or branch", "Test evidence", "Usage note"],
    inputs: ["Repository URL", "Task brief", "Acceptance tests", "Constraints"],
    signals: ["Good for small backlog items", "Clear proof-based acceptance", "Strong reuse potential"],
    featured: true
  },
  {
    slug: "northstar-content-lab",
    name: "Northstar Content Lab",
    owner: "Northstar Studio",
    category: "Content",
    headline: "On-brand content packages for launch pages, blogs, and product announcements.",
    summary: "Designed for teams that need repeatable messaging with tone control and reviewable asset bundles.",
    priceFrom: 260,
    slaHours: 36,
    availableSlots: 4,
    trustScore: 91,
    regions: ["Global", "EMEA"],
    tags: ["Brand-safe", "Headline variants", "SEO-ready"],
    deliverables: ["Draft copy", "SEO pack", "Revision note"],
    inputs: ["Audience", "Key messages", "Tone", "Length"],
    signals: ["Useful for marketing ops", "Stable output format", "Easy async review"],
    featured: true
  },
  {
    slug: "harbor-ops-monitor",
    name: "Harbor Ops Monitor",
    owner: "Harbor Automation",
    category: "Operations",
    headline: "Daily monitoring and triage packages for dashboards, alerts, and exception queues.",
    summary: "Summarizes incidents or queue changes into predictable operating reports for async handoff.",
    priceFrom: 180,
    slaHours: 18,
    availableSlots: 6,
    trustScore: 90,
    regions: ["NAMER", "EMEA"],
    tags: ["Queue triage", "Operations report", "Repeatable cadence"],
    deliverables: ["Ops summary", "Priority list", "Escalation notes"],
    inputs: ["Source dashboards", "Alert rules", "Severity policy"],
    signals: ["Strong for recurring work", "Operational reuse is high", "Low coordination overhead"],
    featured: false
  },
  {
    slug: "quartz-data-forge",
    name: "Quartz Data Forge",
    owner: "Quartz Studio",
    category: "Data",
    headline: "Data cleanup and structured extraction packages for messy source material.",
    summary: "Handles extraction, normalization, and delivery into reviewable CSV or JSON formats.",
    priceFrom: 240,
    slaHours: 30,
    availableSlots: 4,
    trustScore: 92,
    regions: ["Global"],
    tags: ["Structured export", "CSV/JSON", "Schema-aware"],
    deliverables: ["Cleaned dataset", "Field map", "Quality report"],
    inputs: ["Source files", "Target schema", "Validation rules"],
    signals: ["High leverage for operations", "Strong artifact clarity", "Useful for repeat imports"],
    featured: false
  },
  {
    slug: "helix-growth-radar",
    name: "Helix Growth Radar",
    owner: "Helix Lab",
    category: "Research",
    headline: "Competitive tracking packages for launches, pricing moves, and market changes.",
    summary: "Optimized for recurring scans where buyers need deltas instead of one-off long reports.",
    priceFrom: 320,
    slaHours: 42,
    availableSlots: 2,
    trustScore: 94,
    regions: ["Global", "LATAM"],
    tags: ["Delta tracking", "Competitor watch", "Recurring insight"],
    deliverables: ["Change log", "Impact summary", "Reference links"],
    inputs: ["Watchlist", "Tracking rules", "Decision lens"],
    signals: ["Good for weekly updates", "Tight change reporting", "Clear buyer expectation"],
    featured: false
  },
  {
    slug: "ember-design-sprint",
    name: "Ember Design Sprint",
    owner: "Ember Works",
    category: "Design",
    headline: "UI concept packages for bounded screens, flows, and market-facing assets.",
    summary: "Provides polished screens and rationale for targeted interfaces without drifting into open-ended design work.",
    priceFrom: 300,
    slaHours: 40,
    availableSlots: 3,
    trustScore: 89,
    regions: ["Global"],
    tags: ["UI concepts", "Flow framing", "Bounded scope"],
    deliverables: ["Screen set", "Interaction notes", "Review rationale"],
    inputs: ["Target flow", "Constraints", "Reference patterns"],
    signals: ["Best for scoped UI tasks", "Deliverables are visual and reviewable", "Fits async feedback loops"],
    featured: false
  },
  {
    slug: "summit-finance-ops",
    name: "Summit Finance Ops",
    owner: "Summit Systems",
    category: "Operations",
    headline: "Finance and reconciliation packages for structured reporting and variance review.",
    summary: "Converts recurring spreadsheet work into fixed-format reconciliations with explicit exception handling.",
    priceFrom: 210,
    slaHours: 20,
    availableSlots: 5,
    trustScore: 95,
    regions: ["NAMER", "APAC"],
    tags: ["Variance review", "Structured finance ops", "Exception tracking"],
    deliverables: ["Reconciliation summary", "Variance table", "Follow-up list"],
    inputs: ["Source sheet", "Target format", "Threshold rules"],
    signals: ["Strong for repeat close tasks", "Clear pass/fail criteria", "High operational fit"],
    featured: false
  },
  {
    slug: "orbit-support-router",
    name: "Orbit Support Router",
    owner: "Orbit Support",
    category: "Support",
    headline: "Support ticket classification and escalation packages for growing product teams.",
    summary: "Packages inbound issues into prioritized queues, reusable tags, and handoff-ready summaries.",
    priceFrom: 170,
    slaHours: 16,
    availableSlots: 7,
    trustScore: 88,
    regions: ["Global"],
    tags: ["Ticket routing", "Priority tagging", "Support ops"],
    deliverables: ["Tagged queue", "Escalation summary", "Pattern notes"],
    inputs: ["Ticket feed", "Severity rules", "Escalation policy"],
    signals: ["Useful for overflow coverage", "Good inventory for idle capacity", "Simple acceptance"],
    featured: false
  }
];

export const flowSteps = [
  {
    id: "01",
    title: "Ingest live agent inventory",
    body: "The frontend should accept a backend array of agent packages and derive cards, counts, filters, and sections from that array."
  },
  {
    id: "02",
    title: "Rank or feature a subset",
    body: "Featured rows are just a projection of the same source list, so new agents can appear without rewriting the layout."
  },
  {
    id: "03",
    title: "Route into the full market",
    body: "A dedicated market page lists all packages with pagination so the catalog can scale beyond the homepage preview."
  },
  {
    id: "04",
    title: "Open detail pages on demand",
    body: "Each card links to a detail view generated from the same payload shape, ready to swap to backend data later."
  }
];

export function getMarketStats(items = agentMarkets) {
  const totalSlots = items.reduce((sum, item) => sum + item.availableSlots, 0);
  const averageTrust = Math.round(items.reduce((sum, item) => sum + item.trustScore, 0) / items.length);
  const categories = new Set(items.map((item) => item.category)).size;
  return [
    { label: "Live packages", value: String(items.length) },
    { label: "Open capacity", value: String(totalSlots) },
    { label: "Market categories", value: String(categories) },
    { label: "Average trust", value: `${averageTrust}%` }
  ];
}

export function getCategorySummary(items = agentMarkets) {
  return [...items.reduce((map, item) => {
    const entry = map.get(item.category) ?? { label: item.category, count: 0 };
    entry.count += 1;
    map.set(item.category, entry);
    return map;
  }, new Map()).values()].sort((left, right) => right.count - left.count);
}

export function getFeaturedMarkets(items = agentMarkets, limit = 4) {
  return items.filter((item) => item.featured).slice(0, limit);
}

export function getMarketBySlug(slug) {
  return agentMarkets.find((item) => item.slug === slug);
}

export function paginateMarkets(page, pageSize = 6, items = agentMarkets) {
  const currentPage = Number.isFinite(page) && page > 0 ? page : 1;
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    currentPage: safePage,
    totalPages,
    items: items.slice(start, start + pageSize)
  };
}
