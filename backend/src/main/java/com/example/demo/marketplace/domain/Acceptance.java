package com.example.demo.marketplace.domain;

import java.time.Instant;
import java.util.List;

public class Acceptance {
    private final List<String> passedItems;
    private final String note;
    private final Instant reviewedAt;

    public Acceptance(List<String> passedItems, String note, Instant reviewedAt) {
        this.passedItems = List.copyOf(passedItems);
        this.note = note;
        this.reviewedAt = reviewedAt;
    }

    public List<String> getPassedItems() {
        return passedItems;
    }

    public String getNote() {
        return note;
    }

    public Instant getReviewedAt() {
        return reviewedAt;
    }
}
