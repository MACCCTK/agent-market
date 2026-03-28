import { CapabilityPackage, Deliverable, Order, Owner, TaskTemplate, ZeaburSkill } from "./types";

export const templates: TaskTemplate[] = [
  {
    id: "research-brief",
    name: "Research Brief",
    summary: "Synthesize up to five strategic questions into a memo with cited sources.",
    inputs: [
      { id: "topic", label: "Research Topic", type: "text", required: true, helpText: "What domain or product area?" },
      { id: "goalStatement", label: "Goal Statement", type: "textarea", required: true, maxLength: 500 },
      { id: "primaryQuestions", label: "Primary Questions", type: "array", required: true, minItems: 1, maxItems: 5 },
      {
        id: "geography",
        label: "Geography",
        type: "enum",
        required: false,
        options: [
          { value: "global", label: "Global" },
          { value: "namer", label: "North America" },
          { value: "emea", label: "EMEA" },
          { value: "apac", label: "APAC" },
          { value: "latam", label: "LATAM" }
        ]
      },
      {
        id: "formatPreferences",
        label: "Format Preferences",
        type: "enum",
        required: false,
        options: [
          { value: "memo", label: "Memo" },
          { value: "slides", label: "Slide Outline" },
          { value: "table", label: "Comparative Table" }
        ]
      }
    ],
    outputs: ["Structured memo (Markdown/PDF)", "Insight bullets", "Source appendix"],
    slaHours: 48,
    pricing: {
      basePrice: 350,
      currency: "USD",
      adjustments: [
        { condition: "More than 3 primary questions", deltaPercent: 10 },
        { condition: "Rush delivery (<24h)", deltaPercent: 20 }
      ]
    },
    acceptanceChecklist: [
      { id: "coverage", description: "Answers every primary question with citations" },
      { id: "sources", description: "Provides >=5 credible sources with capture dates" },
      { id: "format", description: "Delivers in requested format" },
      { id: "risks", description: "Highlights risks and assumptions" }
    ],
    rejectionNotes: [
      "Missing citations or outdated data",
      "Format mismatch without approval",
      "Insufficient scope coverage"
    ],
    zeaburSkill: { skillId: "skill_research_suite", version: "1.2.0" }
  },
  {
    id: "code-task",
    name: "Code Task",
    summary: "Deliver a bounded engineering fix or automation.",
    inputs: [
      { id: "repositoryUrl", label: "Repository URL", type: "text", required: true },
      { id: "taskDescription", label: "Task Description", type: "textarea", required: true, maxLength: 600 },
      {
        id: "techStack",
        label: "Tech Stack",
        type: "enum",
        required: true,
        options: [
          { value: "python", label: "Python" },
          { value: "node", label: "Node.js" },
          { value: "go", label: "Go" },
          { value: "rust", label: "Rust" },
          { value: "other", label: "Other" }
        ]
      },
      { id: "acceptanceTests", label: "Acceptance Tests", type: "array", required: true, minItems: 1 },
      { id: "constraints", label: "Constraints", type: "textarea", required: false }
    ],
    outputs: ["Patch bundle", "Updated docs", "Test evidence"],
    slaHours: 24,
    pricing: {
      basePrice: 200,
      currency: "USD",
      adjustments: [
        { condition: "Medium complexity", deltaFixed: 150 },
        { condition: "Large complexity", deltaFixed: 300 }
      ]
    },
    acceptanceChecklist: [
      { id: "tests-pass", description: "Acceptance tests pass with proof" },
      { id: "lint", description: "Code meets repo lint/format rules" },
      { id: "security", description: "No new secrets or CVEs" },
      { id: "docs", description: "Docs updated when behavior changes" }
    ],
    rejectionNotes: [
      "Tests failing or missing proof",
      "No reproducible instructions",
      "Regression introduced"
    ],
    zeaburSkill: { skillId: "skill_code_tasker", version: "0.9.5" }
  },
  {
    id: "content-draft",
    name: "Content Draft",
    summary: "Produce on-brand content ready for light editing.",
    inputs: [
      {
        id: "contentType",
        label: "Content Type",
        type: "enum",
        required: true,
        options: [
          { value: "blog", label: "Blog" },
          { value: "announcement", label: "Announcement" },
          { value: "landing", label: "Landing Page" },
          { value: "email", label: "Email" }
        ]
      },
      { id: "audience", label: "Audience Persona", type: "text", required: true },
      { id: "keyMessages", label: "Key Messages", type: "array", required: true, minItems: 3, maxItems: 7 },
      {
        id: "tone",
        label: "Tone",
        type: "enum",
        required: true,
        options: [
          { value: "professional", label: "Professional" },
          { value: "conversational", label: "Conversational" },
          { value: "technical", label: "Technical" },
          { value: "playful", label: "Playful" }
        ]
      },
      {
        id: "length",
        label: "Length",
        type: "enum",
        required: true,
        options: [
          { value: "short", label: "Short (400-600 words)" },
          { value: "medium", label: "Medium (800-1200 words)" },
          { value: "long", label: "Long (1500+ words)" }
        ]
      }
    ],
    outputs: ["Markdown draft", "SEO metadata", "Revision log"],
    slaHours: 36,
    pricing: {
      basePrice: 250,
      currency: "USD",
      adjustments: [
        { condition: "Additional 500 words", deltaFixed: 50 },
        { condition: "Rush 24h delivery", deltaPercent: 20 }
      ]
    },
    acceptanceChecklist: [
      { id: "messages", description: "Includes all key messages" },
      { id: "tone", description: "Matches requested tone and length" },
      { id: "seo", description: "SEO metadata provided when needed" },
      { id: "headlines", description: "At least two alternate headlines" }
    ],
    rejectionNotes: [
      "Tone mismatch",
      "Missing key message or inaccurate references",
      "Length deviation >10%"
    ],
    zeaburSkill: { skillId: "skill_content_crafter", version: "2.1.0" }
  }
];

export const owners: Owner[] = [
  {
    id: "owner_1",
    displayName: "Atlas Research Collective",
    capabilityPackages: ["pkg_research_global"],
    skillIds: ["skill_research_suite"],
    bio: "B2B + macro trend research pod operating 3 tuned OpenClaw agents.",
    timezone: "UTC+0"
  },
  {
    id: "owner_2",
    displayName: "Lambda Fixers",
    capabilityPackages: ["pkg_code_fixes"],
    skillIds: ["skill_code_tasker"],
    bio: "Senior automation engineers specializing in repo triage and fixes.",
    timezone: "UTC-8"
  }
];

export const capabilityPackages: CapabilityPackage[] = [
  {
    id: "pkg_research_global",
    ownerId: "owner_1",
    title: "Global Research Pod",
    description: "Handles research briefs with 48h SLA.",
    supportedTemplateIds: ["research-brief"],
    skillBindings: [{ skillId: "skill_research_suite", version: "1.2.0" }],
    capacity: 3,
    priceRange: { min: 350, max: 600, currency: "USD" },
    status: "active"
  },
  {
    id: "pkg_code_fixes",
    ownerId: "owner_2",
    title: "Code Fix Crew",
    description: "Small code fixes and automations.",
    supportedTemplateIds: ["code-task"],
    skillBindings: [{ skillId: "skill_code_tasker", version: "0.9.5" }],
    capacity: 4,
    priceRange: { min: 200, max: 550, currency: "USD" },
    status: "active"
  }
];

export const zeaburSkills: ZeaburSkill[] = [
  {
    id: "skill_research_suite",
    name: "Research Suite",
    description: "Multi-source research agent tuned for market scans.",
    version: "1.2.0",
    inputSchema: { topic: "string", questions: "string[]" },
    outputSchema: { memo: "markdown", insights: "string[]" }
  },
  {
    id: "skill_code_tasker",
    name: "Code Tasker",
    description: "Applies patches to repos with built-in testing harness.",
    version: "0.9.5",
    inputSchema: { repo: "url", task: "string" },
    outputSchema: { patch: "diff", tests: "log" }
  },
  {
    id: "skill_content_crafter",
    name: "Content Crafter",
    description: "Creates on-brand marketing content.",
    version: "2.1.0",
    inputSchema: { type: "enum", tone: "enum" },
    outputSchema: { markdown: "string", seo: "object" }
  }
];

const now = new Date().toISOString();

export const orders: Order[] = [
  {
    id: "ord_demo_1",
    buyerId: "buyer_demo",
    templateId: "research-brief",
    packageId: "pkg_research_global",
    inputs: { topic: "AI Agent Marketplaces", primaryQuestions: ["Who are top 5 players?"] },
    state: "delivered",
    escrowAmount: 350,
    currency: "USD",
    createdAt: now,
    updatedAt: now,
    zeaburRunId: "run_rb_001"
  }
];

export const deliverables: Deliverable[] = [
  {
    id: "deliv_demo_1",
    orderId: "ord_demo_1",
    version: 1,
    summary: "Market scan with five vendors and SLA/risk highlights.",
    artifactUrl: "https://files.example.com/ord_demo_1/v1.pdf",
    submittedAt: now
  }
];
