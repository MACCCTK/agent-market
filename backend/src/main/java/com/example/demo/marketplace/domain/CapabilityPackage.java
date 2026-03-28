package com.example.demo.marketplace.domain;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

public class CapabilityPackage {
    private final UUID id;
    private final UUID ownerId;
    private final String title;
    private final List<UUID> supportedTemplateIds;
    private final BigDecimal minPrice;
    private final BigDecimal maxPrice;
    private int availableCapacity;

    public CapabilityPackage(
        UUID id,
        UUID ownerId,
        String title,
        List<UUID> supportedTemplateIds,
        BigDecimal minPrice,
        BigDecimal maxPrice,
        int availableCapacity
    ) {
        this.id = id;
        this.ownerId = ownerId;
        this.title = title;
        this.supportedTemplateIds = List.copyOf(supportedTemplateIds);
        this.minPrice = minPrice;
        this.maxPrice = maxPrice;
        this.availableCapacity = availableCapacity;
    }

    public UUID getId() {
        return id;
    }

    public UUID getOwnerId() {
        return ownerId;
    }

    public String getTitle() {
        return title;
    }

    public List<UUID> getSupportedTemplateIds() {
        return supportedTemplateIds;
    }

    public BigDecimal getMinPrice() {
        return minPrice;
    }

    public BigDecimal getMaxPrice() {
        return maxPrice;
    }

    public int getAvailableCapacity() {
        return availableCapacity;
    }

    public void decrementCapacity() {
        this.availableCapacity -= 1;
    }
}
