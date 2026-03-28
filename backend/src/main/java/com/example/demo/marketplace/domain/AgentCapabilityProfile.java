package com.example.demo.marketplace.domain;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

public class AgentCapabilityProfile {
    private final String title;
    private final List<UUID> supportedTemplateIds;
    private final BigDecimal minPrice;
    private final BigDecimal maxPrice;
    private final int availableCapacity;

    public AgentCapabilityProfile(
        String title,
        List<UUID> supportedTemplateIds,
        BigDecimal minPrice,
        BigDecimal maxPrice,
        int availableCapacity
    ) {
        this.title = title;
        this.supportedTemplateIds = List.copyOf(supportedTemplateIds);
        this.minPrice = minPrice;
        this.maxPrice = maxPrice;
        this.availableCapacity = availableCapacity;
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
}