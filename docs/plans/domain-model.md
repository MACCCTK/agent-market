# Domain Model & Lifecycle States

This document outlines the primary entities, attributes, and relationships required for the OpenClaw Agent Marketplace V1. It also details the order state machine and supporting events.

## Entity Overview

| Entity | Description | Key Attributes |
| --- | --- | --- |
| `Buyer` | Marketplace customer placing orders | `id`, `accountId`, `contact`, `company`, `paymentMethodId`, `riskScore` |
| `AgentOwner` | Individual/team operating OpenClaw capability packages | `id`, `userId`, `bio`, `capabilities[]`, `availability`, `rating`, `complianceStatus` |
| `CapabilityPackage` | Sellable bundle tied to Zeabur skills | `id`, `ownerId`, `title`, `description`, `skillBindings[{skillId,version}]`, `supportedTemplates[]`, `priceRange`, `capacity`, `leadTimeHours`, `status` |
| `TaskTemplate` | Standardized task definition | `id`, `name`, `summary`, `inputSchema`, `outputSchema`, `acceptanceChecklist`, `slaHours`, `basePrice`, `allowedAdjustments` |
| `Order` | Transaction between Buyer and Owner | `id`, `buyerId`, `templateId`, `selectedPackageId`, `inputs`, `state`, `slaDeadline`, `escrowAmount`, `currency`, `createdAt`, `updatedAt` |
| `Deliverable` | Structured output for an order | `id`, `orderId`, `version`, `artifactUrl`, `summary`, `zeaburRunId`, `submittedAt`, `checksum` |
| `AcceptanceChecklist` | Evaluations per template/order | `id`, `orderId`, `items[{label,passed,evidence}]`, `submittedBy`, `submittedAt` |
| `Settlement` | Escrow ledger entries | `id`, `orderId`, `type` (hold/release/refund), `amount`, `currency`, `processorTxnId`, `status`, `timestamp` |
| `Dispute` | Escalation record | `id`, `orderId`, `reason`, `details`, `openedBy`, `status`, `resolution`, `resolvedAt` |
| `AuditEvent` | Immutable log for compliance | `id`, `entityType`, `entityId`, `action`, `payload`, `actor`, `timestamp` |

## Relationships

- `Buyer` 1..* `Order`
- `AgentOwner` 1..* `CapabilityPackage`
- `CapabilityPackage` many-to-many `TaskTemplate` (via support table)
- `Order` belongs to one `TaskTemplate` and references one `CapabilityPackage`
- `Order` 1..* `Deliverable` (versions), 0..1 `AcceptanceChecklist`, 0..1 `Dispute`
- `Order` 1..* `Settlement` events
- `Deliverable` references `ZeaburRun` metadata (logical link, no separate table unless needed)

## Order State Machine

```
created
  -> accepted (owner accepts)
  -> cancelled (buyer cancels pre-accept)

accepted
  -> in_progress (zeabur run launched)
  -> cancelled (owner timeout or manual abort)

in_progress
  -> delivered (deliverable submitted)
  -> disputed (owner misses SLA or buyer flags issue)

delivered
  -> accepted (buyer approves checklist)
  -> rejected (buyer requests revision)
  -> disputed (buyer escalates)

rejected
  -> in_progress (owner reworks)
  -> disputed (either party escalates)

accepted
  -> settled (escrow released)

disputed
  -> settled (ops resolves and pays owner)
  -> refunded (ops resolves in buyer favor)
```

Each transition triggers audit events and, when relevant, settlement ledger entries or SLA timers.

## Key Processes

### Zeabur Skill Binding
1. Owner imports skill catalog via `GET /api/zeabur/skills`.
2. Owner selects skill IDs and versions when creating a Capability Package.
3. Platform validates compatibility between template input schema and skill schema.

### Escrow Ledger
1. On order creation, record `Settlement(type=hold)`.
2. On acceptance, record `Settlement(type=release)` along with payout instructions.
3. On refund/dispute resolution, record `Settlement(type=refund)` with processor reference.

### SLA & Capacity
- `capacity` defines concurrent orders allowed; accepting an order decrements capacity until delivery or cancellation.
- SLA deadline = `acceptedAt + template.slaHours`.
- Background job monitors deadlines to auto-trigger reminders or move orders to dispute.

## Data Storage Considerations

- Use UUIDs for external references; store short ULIDs for URLs when needed.
- Encrypt sensitive Buyer notes and payment tokens (vaulted via PSP).
- Store deliverable artifacts in object storage; persist checksums and MIME type in DB.
- Ensure AuditEvents append-only (e.g., PostgreSQL partitioned table) with tamper-evident hash chain if needed later.

## Reporting & Analytics

- Core metrics: template-level acceptance rate, average delivery time, owner utilization, dispute outcomes.
- Maintain derived tables or views for dashboard queries; avoid running heavy aggregations on OLTP tables in production hours.
