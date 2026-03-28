# Domain Model

## Core Entities

### Buyer
- Person or team purchasing a task outcome
- Attributes: id, contact info, preferences, order history, reputation score (if applicable)

### Agent Owner
- Person or team operating an OpenClaw agent capability package
- Attributes: id, contact info, capability package details, availability, performance metrics, payout info

### Capability Package
- The sellable unit: OpenClaw agent capability package operated by an individual or team
- Attributes: id, owner_id, supported_task_types, sample_outputs, price_range, available_capacity, description

### Task Template
- Standardized task definition
- Attributes: id, slug, name, description, inputs_schema, outputs_schema, sla_hours, pricing_logic, acceptance_checklist, fit_description, accent, blurb

### Order
- Represents a buyer's request for a specific task template
- Attributes: id, buyer_id, template_id, status, submitted_inputs, escrow_amount, placed_at, accepted_at, started_at, delivered_at, accepted_at, settled_at

### Structured Deliverable
- Reviewable output artifact produced by an agent run
- Attributes: id, order_id, submission_data, submitted_at, format_type, size

### Acceptance Record
- Record of buyer's review against acceptance checklist
- Attributes: id, deliverable_id, buyer_id, accepted_at, revision_requests, checklist_results

### Settlement
- Payment flow record
- Attributes: id, order_id, escrow_in, platform_fee, owner_payout, refund_amount, settled_at, dispute_resolution

### Dispute
- Record of dispute handling process
- Attributes: id, order_id, initiated_by, reason, evidence, resolution, resolved_at

## Entity Relationships

- Buyer 1:N Order
- Agent Owner 1:N Capability Package
- Capability Package 1:N Task Template (through supported types)
- Order 1:1 Task Template
- Order 1:N Structured Deliverable (usually 1)
- Structured Deliverable 1:N Acceptance Record (usually 1)
- Order 1:N Settlement (usually 1)
- Order 0:N Dispute (usually 0 or 1)

## Lifecycle States

### Order Status
- `created`: Order placed, escrow pending
- `accepted`: Owner accepted, escrow secured
- `in_progress`: Owner working on task
- `delivered`: Owner submitted deliverable
- `delivered_rejected`: Buyer rejected deliverable (may trigger revision)
- `in_dispute`: Order in dispute handling
- `accepted`: Buyer accepted deliverable (note: same name as order accepted? Might need different naming)
- `settled`: Funds released to owner
- `refunded`: Funds returned to buyer
- `settled_dispute`: Settlement after dispute resolution

### Better Order Status Flow:
1. `order_created` (buyer placed order, escrow pending)
2. `order_accepted` (owner accepted)
3. `order_in_progress` (owner working)
4. `order_delivered` (owner submitted deliverable)
5. `order_delivered_accepted` (buyer accepted) -> leads to settlement
6. `order_delivered_rejected` (buyer rejected) -> may go to revision or dispute
7. `order_in_dispute` (dispute handling)
8. `order_settled` (funds released)
9. `order_refunded` (funds returned)
10. `order_settled_after_dispute` (settlement post-dispute)

## Data and Admin

### Minimum Admin Functions
- Template management (create, update, deprecate)
- Order management (view, filter, intervene)
- Dispute handling (mediation, resolution)
- Owner review (performance monitoring, capability package verification)

### Core Events to Track
- browse_template
- order_created
- order_accepted
- order_in_progress
- order_delivered
- order_delivered_accepted
- order_delivered_rejected
- order_in_dispute
- order_settled
- order_refunded
- order_settled_after_dispute

## Storage Considerations

- Use relational database for structured data (PostgreSQL/MySQL)
- Consider object storage for large deliverable artifacts (if applicable)
- Index frequently queried fields: order status, template id, timestamps
- Implement soft deletes for audit trail
- GDPR/privacy considerations for personal data

