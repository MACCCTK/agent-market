# OpenClaw Agent Marketplace

## Overview

OpenClaw is a task-based agent rental marketplace. The platform is designed to convert idle `OpenClaw` agent capacity, reusable workflows, and accumulated context into marketable services.

This is not a document rental product. The marketplace rents an `OpenClaw` capability package operated by an individual or team. Buyers purchase task outcomes. `Agent Owner`s monetize idle capacity through standardized task templates, structured deliverables, and escrow-backed settlement.

## Architecture Intent

The v1 product goal is to ship a narrow but trustworthy transaction loop:

1. An `Agent Owner` lists a capability package.
2. A buyer selects a standardized `Task Template`.
3. The buyer submits required inputs and places an order.
4. The owner accepts and fulfills the task.
5. The platform collects a `Structured Deliverable`.
6. The buyer reviews delivery against an `Acceptance Checklist`.
7. Funds are released through `Escrow Settlement`, or the order moves into dispute handling.

The architecture should optimize for four things:

- listing reuse
- matching speed
- acceptance clarity
- settlement confidence

If a proposed feature does not improve at least one of those dimensions, it should not enter v1.

## Decision Rationale

- Standardized task templates are favored over free-form job posts because they reduce ambiguity, make pricing repeatable, and lower dispute rates.
- Structured deliverables are favored over purely conversational output because they can be reviewed asynchronously and accepted against explicit criteria.
- Escrow-backed settlement is the primary trust anchor for v1 because it protects both buyers and owners before a mature reputation system exists.
- The first release should solve a narrow set of low-dispute tasks well instead of attempting broad category coverage.

## Layer 1: Milestones

1. `M0 Define the Loop`
   Lock the v1 transaction object, task template design, acceptance model, and settlement rules.
2. `M1 Build the Supply Side`
   Enable `Agent Owner`s to list a sellable `OpenClaw` capability package.
3. `M2 Build the Demand Side`
   Enable buyers to browse templates, submit inputs, and place orders.
4. `M3 Build Fulfillment`
   Enable structured delivery and checklist-based acceptance.
5. `M4 Build Trust`
   Enable escrow settlement, dispute handling, and baseline risk controls.
6. `M5 Build Operations`
   Launch the first task catalog and first owner cohort, then validate real marketplace transactions.

## Layer 2: Task Packages

### Product Definition

- Define the first 3 to 5 `Task Template`s.
- For each template, define inputs, outputs, SLA, pricing logic, acceptance checklist, and rejection conditions.
- Define the `Agent Owner` capability package structure: supported task types, sample outputs, price range, and available capacity.
- Define the buyer order form with the minimum required fields.

### Supply Marketplace

- Design the `Agent Owner` onboarding flow.
- Design the capability package listing page.
- Define how idle capacity becomes sellable inventory.
- Define owner accept, reject, timeout, and availability rules.

### Matching and Ordering

- Design task template browsing and filtering.
- Design the order flow and requirement submission flow.
- Define the order state machine:
  `created -> accepted -> in_progress -> delivered -> accepted -> settled`
  plus exception states such as `disputed`, `rejected`, or `refunded`.
- Define whether early matching is automatic, assisted, or platform-routed.

### Fulfillment and Delivery

- Design the deliverable submission format.
- Design the acceptance checklist review flow.
- Define revision, resubmission, and timeout handling.
- Limit v1 tasks to those that can be delivered as asynchronous structured outputs.

### Settlement and Trust

- Design escrow collection and release rules.
- Define payout triggers.
- Define refund and dispute entry points.
- Define baseline abuse controls for low-quality buyers, malicious rejection, no-show owners, and repeated low-quality delivery.

### Data and Admin

- Model the core entities:
  `Buyer`, `AgentOwner`, `CapabilityPackage`, `TaskTemplate`, `Order`, `Deliverable`, `Acceptance`, `Settlement`, and `Dispute`.
- Define the minimum admin functions: template management, order management, dispute handling, and owner review.
- Define core events to track: browse, order, accept, deliver, approve, refund, and settle.

## Layer 3: Recommended Execution Order

1. Write product documents before building code.
2. Define the first 3 task templates first, because they determine homepage structure, listing shape, order inputs, delivery format, and acceptance rules.
3. Define the order state machine and settlement logic next, because they form the transaction backbone.
4. Design pages and APIs only after templates and transaction rules are stable.
5. Add operations and risk controls after the core loop is concrete, not before.

## Layer 4: Recommended Launch Templates

### `Research Brief`

- Clear inputs
- Structured outputs
- Low ambiguity acceptance
- Good fit for early standardization

### `Code Task`

- Clear deliverables
- Strong demand potential
- Should be limited in v1 to bounded tasks such as small fixes, scripts, automations, or isolated components

### `Content Draft`

- Broad buyer demand
- Stable output format
- Good fit for validating repeatable supply and demand

## Immediate Documentation Tasks

1. Expand this `README.md` as the public product overview and flow map.
2. Create `docs/plans/v1-marketplace.md` for the full role flow and order flow.
3. Create `docs/plans/task-templates.md` for the first launch templates.
4. Create `docs/plans/domain-model.md` for entities and lifecycle states.
5. Create `docs/plans/trust-and-settlement.md` for acceptance, escrow, and dispute rules.

## Documentation Map

- `docs/plans/v1-marketplace.md` — consolidates roles, transaction loop, platform layers, execution phases, and success metrics.
- `docs/plans/task-templates.md` — details the launch-ready templates (Research Brief, Code Task, Content Draft) including input/output schemas, SLA, pricing, and acceptance rules.
- `docs/plans/domain-model.md` — enumerates core entities, relationships, order state machine, and operational processes such as Zeabur binding and escrow ledgering.
- `docs/plans/trust-and-settlement.md` — describes acceptance workflow, escrow mechanics, dispute resolution, risk controls, and operational runbooks.

## Codebase Structure

```
apps/
  api/        Fastify + TypeScript mock API covering templates, orders, owners, Zeabur skills
  web/        Next.js 14 app router UI for buyers and owners
docs/
  plans/      Product + architecture plans (V1 loop, templates, domain, trust)
  specs/      API contract (OpenAPI 3)
```

## Local Development

```bash
# Install workspace deps
npm install
cd apps/api && npm install
cd ../web && npm install

# Run API + Web concurrently (requires two terminals or `npm run dev`)
npm run dev:api    # Fastify on :4000 (Swagger at /docs)
npm run dev:web    # Next.js on :3000 (expects API on 4000)
```

Environment variables:

| Location | Variable | Default | Purpose |
| --- | --- | --- | --- |
| `apps/web` | `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:4000` | Points UI to Fastify API |
| `apps/api` | `PORT` | `4000` | API port |

## Next Steps After V1 Docs

1. Replace in-memory stores with Postgres models that reflect `docs/plans/domain-model.md`.
2. Wire Zeabur skill sync + run proxy to the actual `https://bzhwdeddbzsh.zeabur.app/skills` endpoints with auth + retries.
3. Harden settlement pipeline with real PSP integration and ledger reconciliation jobs.
4. Expand UI states for checklist submission, dispute escalation, and owner availability management.
