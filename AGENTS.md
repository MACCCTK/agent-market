# AGENTS.md

## Mission
- Build `OpenClaw` as an agent rental marketplace, not a document rental marketplace.
- Convert idle agent capacity, reusable workflows, and accumulated context into marketable task services.
- Optimize for fast, trustworthy task fulfillment between buyers and `Agent Owner`s.
- Reject features that increase scope without improving matching, delivery clarity, or settlement safety.

## Product Definition
- The rented asset is an `OpenClaw` agent capability package operated by an individual or team.
- The primary marketplace model for v1 is task-based rental.
- Buyers submit work through standardized task templates instead of fully free-form job posts.
- `Agent Owner`s list idle capacity and accept tasks that fit their capability package.
- Default deliverables are structured outputs such as documents, code, reports, asset bundles, or other reviewable artifacts.
- Trust in v1 comes from template-based acceptance criteria and escrow-style settlement, not from heavy manual review or complex reputation systems.

## V1 Boundaries
- In scope: task templates, agent listings, buyer ordering flow, structured delivery, acceptance checklist, escrow settlement, basic dispute handling.
- In scope: supply-demand balance decisions that improve both buyer confidence and owner monetization.
- Out of scope: seat subscriptions, time-slot rentals, logistics-heavy offline fulfillment, generic social community features, and unconstrained task posting.
- Out of scope: building for every task type at once; start with a narrow catalog that can be priced, delivered, and accepted consistently.

## Core Objects
- `Agent Owner`: person or team operating an `OpenClaw` agent capability package.
- `Buyer`: person or team purchasing a task outcome from the marketplace.
- `Task Template`: standardized task definition with input requirements, price logic, SLA, and acceptance checklist.
- `Structured Deliverable`: reviewable output artifact produced by an agent run.
- `Acceptance Checklist`: explicit criteria used to approve or reject delivery.
- `Escrow Settlement`: payment flow that holds funds until acceptance or dispute resolution.

## Decision Rules
- Prefer standardization before flexibility.
- Prefer low-dispute task types before broad task coverage.
- Prefer deliverables that can be reviewed asynchronously.
- Prefer features that raise listing reuse, matching speed, acceptance clarity, or settlement confidence.
- If a proposal does not improve at least one of those four dimensions, defer it from v1.
- When discussing new work, explicitly state whether it primarily helps supply, demand, or trust.

## Delivery Principles
- Keep workflows short enough that an idle `Agent Owner` can list and fulfill without extra operations overhead.
- Make every task template include required inputs, delivery format, acceptance criteria, and settlement trigger.
- Treat unclear acceptance as a product bug, not as a support problem.
- Design for reusable capability packages so the same agent setup can fulfill repeated demand with minimal manual retuning.
- Track where context or outputs can be safely reused across tasks to reduce idle waste.

## Communication
- Speak to the user in Chinese unless they ask for another language.
- Keep responses concise by default and expand only when needed.
- Write code, schemas, commit messages, and repository documentation in English.
- Challenge vague product ideas early if they blur the v1 marketplace model.

## Execution Workflow
- Declare target paths and excluded areas before making changes.
- Inspect first with read-only commands before editing.
- Use the global worklog scripts to keep `docs/todo.md` and `docs/daily/` synchronized.
- Execute work in small verifiable batches and show evidence before claiming completion.
- Update architecture-facing docs in the same turn as architecture-level changes.

## Documentation Rules
- Treat this file as the source of truth for project framing and v1 scope.
- Keep product terms consistent with the core objects defined above.
- Do not describe the project as a generic document marketplace.
- If the product model changes, update this file before or alongside implementation.
