package com.example.demo.marketplace.domain;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

public class Order {
    private final UUID id;
    private final UUID buyerId;
    private final UUID ownerId;
    private final UUID capabilityPackageId;
    private final UUID taskTemplateId;
    private final Map<String, String> inputs;
    private final Instant createdAt;
    private Instant updatedAt;
    private OrderStatus status;
    private Deliverable deliverable;
    private Acceptance acceptance;
    private Settlement settlement;
    private Dispute dispute;

    public Order(
        UUID id,
        UUID buyerId,
        UUID ownerId,
        UUID capabilityPackageId,
        UUID taskTemplateId,
        Map<String, String> inputs,
        Instant createdAt
    ) {
        this.id = id;
        this.buyerId = buyerId;
        this.ownerId = ownerId;
        this.capabilityPackageId = capabilityPackageId;
        this.taskTemplateId = taskTemplateId;
        this.inputs = Map.copyOf(inputs);
        this.createdAt = createdAt;
        this.updatedAt = createdAt;
        this.status = OrderStatus.CREATED;
    }

    public UUID getId() {
        return id;
    }

    public UUID getBuyerId() {
        return buyerId;
    }

    public UUID getOwnerId() {
        return ownerId;
    }

    public UUID getCapabilityPackageId() {
        return capabilityPackageId;
    }

    public UUID getTaskTemplateId() {
        return taskTemplateId;
    }

    public Map<String, String> getInputs() {
        return inputs;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void touch(Instant now) {
        this.updatedAt = now;
    }

    public OrderStatus getStatus() {
        return status;
    }

    public void setStatus(OrderStatus status) {
        this.status = status;
    }

    public Deliverable getDeliverable() {
        return deliverable;
    }

    public void setDeliverable(Deliverable deliverable) {
        this.deliverable = deliverable;
    }

    public Acceptance getAcceptance() {
        return acceptance;
    }

    public void setAcceptance(Acceptance acceptance) {
        this.acceptance = acceptance;
    }

    public Settlement getSettlement() {
        return settlement;
    }

    public void setSettlement(Settlement settlement) {
        this.settlement = settlement;
    }

    public Dispute getDispute() {
        return dispute;
    }

    public void setDispute(Dispute dispute) {
        this.dispute = dispute;
    }
}
