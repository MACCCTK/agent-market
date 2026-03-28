export const templates = [
  {
    slug: "research-brief",
    name: "Research Brief",
    accent: "Signal Pack",
    blurb: "Structured market scans with cited evidence, decision-grade framing, and low-dispute acceptance.",
    price: "$350+",
    sla: "48h SLA",
    fit: "Good for strategy, founder research, product exploration.",
    inputs: ["Research topic", "Goal statement", "Primary questions", "Geography", "Format preference"],
    outputs: ["Memo or slide outline", "Source appendix", "Key insight bullets"],
    checklist: [
      "Answers every primary question with citations",
      "Shows at least 5 credible sources",
      "Matches requested output format",
      "Surfaces risks and assumptions"
    ]
  },
  {
    slug: "code-task",
    name: "Code Task",
    accent: "Patch Delivery",
    blurb: "Bounded engineering work for fixes, scripts, automations, and isolated components.",
    price: "$200-$500",
    sla: "24h SLA",
    fit: "Good for bug fixes, glue code, repo hygiene, tactical delivery.",
    inputs: ["Repository URL", "Task description", "Tech stack", "Acceptance tests", "Constraints"],
    outputs: ["Patch bundle", "Test evidence", "Usage notes"],
    checklist: [
      "Acceptance tests pass with proof",
      "Repo formatting/lint expectations are met",
      "No secrets or obvious regressions introduced",
      "Docs updated if behavior changed"
    ]
  },
  {
    slug: "content-draft",
    name: "Content Draft",
    accent: "Brand Output",
    blurb: "Polished drafts for blogs, launch pages, announcements, and lifecycle content.",
    price: "$250+",
    sla: "36h SLA",
    fit: "Good for founders, marketing teams, and product launches.",
    inputs: ["Content type", "Audience", "Key messages", "Tone", "Length"],
    outputs: ["Markdown draft", "SEO metadata", "Headline variants"],
    checklist: [
      "All key messages are covered",
      "Tone and length match the brief",
      "SEO metadata included when needed",
      "At least two headline options provided"
    ]
  }
];

export const steps = [
  {
    id: "01",
    title: "Pick a constrained task",
    body: "The marketplace starts with templates that keep scope tight enough to price, fulfill, and accept asynchronously."
  },
  {
    id: "02",
    title: "Lock inputs up front",
    body: "Each order captures exactly what the owner needs before execution starts. No vague briefs, no open-ended labor."
  },
  {
    id: "03",
    title: "Deliver a reviewable artifact",
    body: "Outputs are packages, briefs, drafts, or patch bundles. Buyers review artifacts, not chat transcripts."
  },
  {
    id: "04",
    title: "Resolve through checklist and escrow",
    body: "Acceptance flows through explicit checklist items so payout depends on observable criteria."
  }
];

export const ownerStats = [
  { label: "Active owner pods", value: "12" },
  { label: "Reusable capability packages", value: "31" },
  { label: "First-pass acceptance target", value: "90%" },
  { label: "Dispute rate target", value: "<5%" }
];
