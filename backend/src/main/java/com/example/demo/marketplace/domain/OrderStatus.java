package com.example.demo.marketplace.domain;

public enum OrderStatus {
    CREATED,
    ACCEPTED_BY_OWNER,
    IN_PROGRESS,
    DELIVERED,
    BUYER_ACCEPTED,
    SETTLED,
    DISPUTED,
    REJECTED,
    REFUNDED
}
