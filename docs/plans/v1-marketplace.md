# v1 Marketplace Plan

## Role Flow and Order Flow

This document details the complete role flow and order flow for the OpenClaw Agent Marketplace v1.

### Roles

1. **Agent Owner**: Person or team operating an OpenClaw agent capability package.
2. **Buyer**: Person or team purchasing a task outcome from the marketplace.

### Core Objects

- **Task Template**: Standardized task definition with input requirements, price logic, SLA, and acceptance checklist.
- **Structured Deliverable**: Reviewable output artifact produced by an agent run.
- **Acceptance Checklist**: Explicit criteria used to approve or reject delivery.
- **Escrow Settlement**: Payment flow that holds funds until acceptance or dispute resolution.

### Order Flow

1. **Browse Templates**: Buyer browses available task templates.
2. **Select Template**: Buyer chooses a specific task template.
3. **Submit Inputs**: Buyer provides required inputs for the selected template.
4. **Place Order**: Buyer submits order and places funds in escrow.
5. **Owner Notification**: Agent Owner is notified of new order.
6. **Owner Acceptance**: Owner accepts the order (or rejects/times out).
7. **Fulfillment**: Owner executes the task using their OpenClaw agent capability package.
8. **Delivery Submission**: Owner submits structured deliverable.
9. **Buyer Review**: Buyer reviews deliverable against acceptance checklist.
10. **Acceptance/Rejection**: Buyer accepts or rejects delivery (with possible revision requests).
11. **Settlement**: Upon acceptance, escrow releases funds to Owner minus platform fee.
12. **Dispute Handling**: If rejected, enters dispute resolution process.

### Order State Machine

```
created -> accepted -> in_progress -> delivered -> accepted -> settled
```

Exception states:
- `rejected`: Owner rejected the order
- `delivered_rejected`: Buyer rejected the deliverable
- `in_dispute`: Order is in dispute handling
- `refunded`: Funds refunded to buyer
- `settled_dispute`: Settlement after dispute resolution

### Acceptance Criteria

Acceptance is determined by explicit checklist items. Each checklist item must be satisfied for acceptance. Partial acceptance may trigger revision requests.

### Settlement Rules

- Escrow holds funds upon order placement.
- Platform fee deducted from owner payout.
- Payout released upon buyer acceptance or after dispute resolution favoring owner.
- Refund issued to buyer if dispute resolved in buyer's favor or owner no-show.

### Risk Controls (Baseline)

- Low-quality buyer detection (frequent unjustified rejections)
- Malicious rejection prevention
- Owner no-show penalties
- Repeated low-quality delivery detection
- Template-specific SLA enforcement

## Milestones

Refer to README.md Layer 1: Milestones for detailed milestone breakdown.

