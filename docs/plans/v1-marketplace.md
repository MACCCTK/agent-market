# OpenClaw Agent Marketplace – V1 Execution Plan

## Purpose

Establish a narrow, repeatable transaction loop that lets Buyers rent curated OpenClaw capability packages (via Zeabur-hosted skills) with predictable delivery, clear acceptance, and escrow-backed settlement. This document aligns product, engineering, and operations teams on scope, flows, and sequencing.

## Roles & Responsibilities

- **Buyer** – chooses a launch template, submits required inputs, funds escrow, reviews structured deliverables against the acceptance checklist, and triggers settlement or dispute.
- **Agent Owner** – lists capability packages, binds them to Zeabur skill IDs, accepts work within their capacity, produces deliverables, and responds to revisions/disputes.
- **Marketplace Operations** – curates templates, monitors supply-demand balance, arbitrates disputes, approves payouts, and manages abuse controls.
- **Platform Services** – provide APIs, back office tooling, monitoring, auditing, and integration with Zeabur skill executions.

## Transaction Loop Overview

1. **Template Discovery** – Buyers browse standardized Task Templates and inspect SLA, price, required inputs, and acceptance checklist.
2. **Order Creation** – Buyer selects a template, fills inputs, and authorizes payment into escrow.
3. **Owner Acceptance** – Owner reviews queued orders, accepts if capacity matches, and Zeabur run is scheduled.
4. **Fulfillment** – Zeabur skill executes with captured inputs; Owner curates/edits outputs into the required Structured Deliverable format.
5. **Delivery & Review** – Deliverable uploaded, checklist presented to Buyer for asynchronous review.
6. **Settlement** – Acceptance releases escrow to Owner; rejection routes to revision or dispute; unresolved cases escalate to operations.

## Platform Layers

| Layer | Goal | Key Deliverables |
| --- | --- | --- |
| Product Definition | Lock templates, order form, checklist model | Template specs, onboarding scripts |
| Supply Marketplace | Convert Owner capacity into listings | Capability package CRUD, capacity tracking, Zeabur skill binding |
| Demand Marketplace | Help Buyers find/submit orders fast | Template browse APIs, order wizard, pricing transparency |
| Fulfillment & Delivery | Ensure structured outputs | Deliverable storage, versioning, SLA timers |
| Trust & Settlement | Protect both parties | Escrow ledger, payout triggers, dispute tooling |
| Ops & Data | Observe and intervene | Admin console, metrics, alerts, audit trail |

## Execution Phases

1. **Documentation First** – Produce the four companion plans (task templates, domain model, settlement, order flow) plus API sketches.
2. **Domain & API Skeleton** – Model core tables/entities, expose read-only template + listing APIs to unblock front-end.
3. **Order Backbone** – Implement state machine, escrow ledger, Zeabur integration, and owner acceptance UI.
4. **Delivery Experience** – Checklist UI, deliverable viewer, revision handling, notification channels.
5. **Trust & Ops** – Dispute workflows, admin overrides, abuse heuristics, monitoring & logging.
6. **Pilot & Iterate** – Launch with limited Owners/templates, capture feedback, iterate on pricing and SLAs.

## Cross-Cutting Requirements

- All templates must specify input schema, output schema, SLA, acceptance checklist, and rejection fallbacks.
- Every Zeabur run must be traceable via `runId -> orderId` and logged with request/response payload hashes.
- Escrow actions (hold, release, refund) require immutable event logging and reconciliation with payment provider.
- Notifications must cover Buyer/Owner email + future web push/SSE for order state changes.

## Non-Goals for V1

- No open-ended job posts or auction mechanics.
- No real-time chat-based fulfillment; focus on asynchronous structured delivery.
- No generalized subscription/time-block rentals.
- No manual Zeabur skill editing from within the marketplace (owners manage skill code in Zeabur separately).

## Success Metrics

- Median time from order creation to owner acceptance under 2 hours.
- ≥90% of deliveries accepted on first submission for launch templates.
- Dispute rate under 5% of total orders.
- ≥80% of listings keep capacity updated weekly.

## Dependencies & Risks

- Zeabur availability and API compatibility (skill schemas, run execution, webhooks).
- Accurate template scoping; oversized templates will break SLAs and acceptance clarity.
- Payment/escrow provider readiness; interim mock ledger must be swappable without schema churn.
- Operations staffing for dispute resolution once >10 concurrent orders exist.
