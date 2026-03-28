# Trust, Acceptance, and Settlement Plan

This document specifies how OpenClaw V1 maintains trust between Buyers and Agent Owners through acceptance controls, escrow-backed settlement, and dispute handling. The guidance applies to all launch templates and Zeabur-integrated workflows.

## Trust Pillars

1. **Template Clarity** – Every task has explicit inputs, outputs, SLA, and acceptance checklist.
2. **Structured Deliverables** – Outputs are versioned artifacts with provenance (Zeabur run ID, checksum).
3. **Escrow Settlement** – Funds are held until acceptance or dispute resolution; neither party can unilaterally clear settlement.
4. **Transparent Lifecycle** – Order states, timers, and events are visible to both parties with notifications.
5. **Audit & Compliance** – Immutable logs allow post-mortem review and regulatory compliance.

## Acceptance Workflow

1. Owner submits deliverable (upload + metadata). System records `Deliverable` and notifies Buyer.
2. Buyer reviews deliverable within SLA (default 24h) using acceptance checklist.
3. Buyer must mark each checklist item pass/fail and optionally add evidence or revision notes.
4. Outcomes:
   - **Accepted** – all items pass; system triggers settlement release.
   - **Rejected** – at least one item fails; order returns to `in_progress`, requiring owner revision.
   - **No Response** – if Buyer does not respond before an auto-accept deadline (configurable per template), system can auto-accept or escalate to ops review.

## Escrow Mechanics

- **Hold**: When Buyer creates an order, payment processor captures funds and places them in escrow (`Settlement: hold`). Order cannot start without confirmation.
- **Release**: On acceptance, marketplace triggers payout (`Settlement: release`). Funds route to Owner minus platform fee; transaction ID stored.
- **Refund**: If dispute resolves in Buyer favor or order is cancelled pre-acceptance, log `Settlement: refund` and release funds back to Buyer.
- **Partial Settlement**: Future enhancement; not in scope for V1 to limit complexity.

### Ledger Requirements

- Double-entry style records per order (debit escrow, credit owner).
- Reconciliation job compares ledger totals with payment provider payout reports.
- All settlement actions emit `AuditEvent` entries for traceability.

## Dispute Handling

1. Either party can escalate to dispute from `delivered` or `rejected` states, providing structured reasoning (failed checklist items, evidence).
2. Operations receives notification via admin console, reviews deliverables, communication history, SLA events, and Zeabur logs.
3. Outcomes:
   - **Buyer Favor** – issue refund, optionally compensate Owner partially if work was acceptable but mis-scoped.
   - **Owner Favor** – force acceptance and release escrow.
   - **Mutual Resolution** – request revision with new SLA and update order notes.
4. All dispute communications stay in-platform; no direct email threads to preserve auditability.

## Risk & Abuse Controls

- **Owner No-Show**: If owner fails to move `accepted -> in_progress` within `graceHours` (default 4h), order auto-cancels and refunds Buyer; strike recorded.
- **Buyer Abuse**: Buyers with repeated rejections without evidence accrue risk score; high-risk accounts require manual approval before new orders.
- **Deliverable Integrity**: Automated scans for malware/secrets on uploaded artifacts; fails block delivery and alert ops.
- **Zeabur Health**: Monitor skill execution latency and failure rates; degrade templates tied to unhealthy skills.

## Notifications & Transparency

- Email + in-app notifications for each state transition and approaching deadlines.
- Owner dashboard shows queued orders, SLA timers, and escrow status.
- Buyer dashboard shows escrow amount, checklist progress, and dispute links.

## Compliance & Logging

- Log every API call impacting settlement or disputes with user ID, IP, timestamp, payload hash.
- Retain acceptance checklist responses for at least 12 months for audit/regulatory review.
- Encrypt PII and payment references; redact before exporting logs.

## Operational Runbooks

- **Dispute Triage**: Triage queue sorted by oldest SLA breach first. Response SLA ≤ 12h.
- **Refund Approval**: Two-person approval for refunds > $1,000 to prevent fraud.
- **Template Updates**: When acceptance rules change, version templates and prompt owners to re-acknowledge; keep old rules attached to existing orders.

## Future Enhancements (Post-V1)

- Reputation scores and automatic trust tiers.
- Partial escrow releases for multi-milestone tasks.
- Federated identity/KYC for high-value Owners and Buyers.
- Automated dispute resolution suggestions powered by deliverable analysis.
