package com.example.demo.marketplace.domain;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

public class TaskTemplate {
    private final UUID id;
    private final String name;
    private final String description;
    private final List<String> requiredInputs;
    private final List<String> acceptanceChecklist;
    private final int slaHours;
    private final BigDecimal basePrice;

    public TaskTemplate(
        UUID id,
        String name,
        String description,
        List<String> requiredInputs,
        List<String> acceptanceChecklist,
        int slaHours,
        BigDecimal basePrice
    ) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.requiredInputs = List.copyOf(requiredInputs);
        this.acceptanceChecklist = List.copyOf(acceptanceChecklist);
        this.slaHours = slaHours;
        this.basePrice = basePrice;
    }

    public UUID getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public List<String> getRequiredInputs() {
        return requiredInputs;
    }

    public List<String> getAcceptanceChecklist() {
        return acceptanceChecklist;
    }

    public int getSlaHours() {
        return slaHours;
    }

    public BigDecimal getBasePrice() {
        return basePrice;
    }
}
