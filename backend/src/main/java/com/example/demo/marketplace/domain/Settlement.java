package com.example.demo.marketplace.domain;

import java.math.BigDecimal;
import java.time.Instant;

public class Settlement {
    private final BigDecimal amount;
    private final Instant escrowedAt;
    private Instant releasedAt;

    public Settlement(BigDecimal amount, Instant escrowedAt) {
        this.amount = amount;
        this.escrowedAt = escrowedAt;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public Instant getEscrowedAt() {
        return escrowedAt;
    }

    public Instant getReleasedAt() {
        return releasedAt;
    }

    public void release(Instant releasedAt) {
        this.releasedAt = releasedAt;
    }
}
