package com.example.demo.marketplace.domain;

import java.math.BigDecimal;
import java.util.UUID;

public class OpenClawAgent {
    private final UUID id;
    private final String name;
    private final String description;
    private final OpenClawAgentStatus status;
    private final BigDecimal estimatedPricePerTask;
    private final AgentCapabilityProfile capabilityProfile;

    public OpenClawAgent(
        UUID id,
        String name,
        String description,
        OpenClawAgentStatus status,
        BigDecimal estimatedPricePerTask,
        AgentCapabilityProfile capabilityProfile
    ) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.status = status;
        this.estimatedPricePerTask = estimatedPricePerTask;
        this.capabilityProfile = capabilityProfile;
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

    public OpenClawAgentStatus getStatus() {
        return status;
    }

    public BigDecimal getEstimatedPricePerTask() {
        return estimatedPricePerTask;
    }

    public AgentCapabilityProfile getCapabilityProfile() {
        return capabilityProfile;
    }
}