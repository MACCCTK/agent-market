# Trust and Settlement

## Acceptance Criteria

Acceptance in v1 is based on explicit checklist items associated with each task template. Each checklist item must be verifiable from the structured deliverable.

### Checklist Design Principles
- **Observable**: Criteria must be checkable without subjective judgment
- **Atomic**: Each item should be a single, verifiable condition
- **Complete**: Collectively, items should define satisfactory completion
- **Practical**: Items should be reasonable for buyer to verify

### Acceptance Process
1. Buyer receives structured deliverable
2. Buyer reviews deliverable against each checklist item
3. Buyer marks each item as satisfied or not
4. If all items satisfied: delivery accepted
5. If any items not satisfied: buyer can request revision or reject

### Revision Handling
- Limited number of revision requests allowed (to be defined per template)
- Revision request must specify which checklist items failed and why
- Owner submits revised deliverable
- Process repeats until acceptance or rejection

## Escrow Settlement

### Flow
1. Buyer places order: funds transferred to escrow account
2. Order accepted: funds secured in escrow (cannot be withdrawn by buyer)
3. Order completed: funds released to owner minus platform fee
4. Order disputed: funds held in escrow until resolution
5. Dispute resolved: funds released to prevailing party minus fees

### Payout Triggers
- Automatic release upon buyer acceptance (after grace period for revision requests?)
- Manual release after dispute resolution
- Timeout-based release (if no response from buyer within SLA + buffer?)

### Platform Fee
- Percentage of transaction value (to be determined)
- Covers marketplace operation, payment processing, and basic support

## Dispute Handling

### Entry Points
- Buyer rejects deliverable and requests dispute
- Owner claims buyer no-show or unjustified rejection
- System detects potential fraud or abuse

### Process
1. Dispute initiated: escrow frozen
2. Evidence collection: both parties submit evidence
3. Mediation: platform facilitates resolution (may be automated for clear cases)
4. Resolution: funds released to prevailing party
5. Fee adjustment: losing party may pay additional dispute fee

### Baseline Abuse Controls
- **Low-quality buyers**: Track rejection rate; require escrow increase or suspend buying privileges if consistently rejecting quality work
- **Malicious rejection**: Require specific evidence for rejection; pattern of unjustified rejections triggers review
- **No-show owners**: Track acceptance-to-start time; penalize owners who accept but don't start work within SLA
- **Repeated low-quality delivery**: Track buyer satisfaction; require remedial action or suspend selling privileges
- **SLA enforcement**: Automatic late flags; potential escrow penalties for chronic lateness

## Trust Anchors

### Primary Trust Anchor (v1)
- Checklist + escrow: Observable criteria + secured funds

### Secondary Trust Builders
- Transparent template definitions: Clear inputs, outputs, SLA, pricing
- Performance metrics: Owner completion rates, average ratings, dispute history
- Capability package verification: Validation of owner's OpenClaw setup
- Transaction history: Successful past orders visible (with privacy considerations)

## Settlement Confidence Optimization

To maximize settlement confidence, the system should:
1. Make acceptance criteria as objective as possible
2. Provide clear evidence requirements for both acceptance and rejection
3. Automate escrow handling to reduce manual intervention
4. Offer timely dispute resolution with clear rules
5. Maintain transparent fee structure
6. Provide audit trail of all transaction steps

