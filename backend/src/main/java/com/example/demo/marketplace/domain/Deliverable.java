package com.example.demo.marketplace.domain;

import java.time.Instant;

public class Deliverable {
    private final String format;
    private final String content;
    private final Instant submittedAt;

    public Deliverable(String format, String content, Instant submittedAt) {
        this.format = format;
        this.content = content;
        this.submittedAt = submittedAt;
    }

    public String getFormat() {
        return format;
    }

    public String getContent() {
        return content;
    }

    public Instant getSubmittedAt() {
        return submittedAt;
    }
}
