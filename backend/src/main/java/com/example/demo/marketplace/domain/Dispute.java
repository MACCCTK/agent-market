package com.example.demo.marketplace.domain;

import java.time.Instant;

public class Dispute {
    private final String reason;
    private final Instant createdAt;

    public Dispute(String reason, Instant createdAt) {
        this.reason = reason;
        this.createdAt = createdAt;
    }

    public String getReason() {
        return reason;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
