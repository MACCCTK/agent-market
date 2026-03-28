package com.example.demo.marketplace.service;

import com.example.demo.marketplace.domain.Acceptance;
import com.example.demo.marketplace.domain.AgentCapabilityProfile;
import com.example.demo.marketplace.domain.CapabilityPackage;
import com.example.demo.marketplace.domain.Deliverable;
import com.example.demo.marketplace.domain.Dispute;
import com.example.demo.marketplace.domain.OpenClawAgent;
import com.example.demo.marketplace.domain.OpenClawAgentStatus;
import com.example.demo.marketplace.domain.Order;
import com.example.demo.marketplace.domain.OrderStatus;
import com.example.demo.marketplace.domain.Settlement;
import com.example.demo.marketplace.domain.TaskTemplate;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class MarketplaceService {

    private final Map<UUID, TaskTemplate> taskTemplates = new LinkedHashMap<>();
    private final Map<UUID, OpenClawAgent> openClawAgents = new LinkedHashMap<>();
    private final Map<UUID, CapabilityPackage> capabilityPackages = new LinkedHashMap<>();
    private final Map<UUID, Order> orders = new LinkedHashMap<>();

    public MarketplaceService() {
        seedTaskTemplates();
    }

    public synchronized List<TaskTemplate> listTaskTemplates() {
        return taskTemplates.values().stream().toList();
    }

    public synchronized List<CapabilityPackage> listCapabilityPackages() {
        return capabilityPackages.values().stream().toList();
    }

    public synchronized OpenClawAgent createBuyer(
        UUID id,
        String name,
        String description,
        OpenClawAgentStatus status,
        BigDecimal estimatedPricePerTask,
        AgentCapabilityProfile capabilityProfile
    ) {
        return createOpenClawAgent(id, name, description, status, estimatedPricePerTask, capabilityProfile);
    }

    public synchronized OpenClawAgent createOwner(
        UUID id,
        String name,
        String description,
        OpenClawAgentStatus status,
        BigDecimal estimatedPricePerTask,
        AgentCapabilityProfile capabilityProfile
    ) {
        return createOpenClawAgent(id, name, description, status, estimatedPricePerTask, capabilityProfile);
    }

    public synchronized List<OpenClawAgent> listOpenClawAgents() {
        return openClawAgents.values().stream().toList();
    }

    public synchronized List<OpenClawAgent> listListedOpenClawAgents() {
        Set<UUID> listedOwnerIds = capabilityPackages.values().stream().map(CapabilityPackage::getOwnerId).collect(java.util.stream.Collectors.toSet());
        return openClawAgents.values().stream().filter(agent -> listedOwnerIds.contains(agent.getId())).toList();
    }

    public synchronized boolean isOpenClawAgentRented(UUID agentId) {
        if (!openClawAgents.containsKey(agentId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "openclaw agent not found");
        }

        return orders.values().stream().anyMatch(order -> order.getOwnerId().equals(agentId) && isRentalActive(order.getStatus()));
    }

    private OpenClawAgent createOpenClawAgent(
        UUID id,
        String name,
        String description,
        OpenClawAgentStatus status,
        BigDecimal estimatedPricePerTask,
        AgentCapabilityProfile capabilityProfile
    ) {
        UUID agentId = id == null ? UUID.randomUUID() : id;
        if (openClawAgents.containsKey(agentId)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "openclaw agent id already exists");
        }

        OpenClawAgent agent = new OpenClawAgent(agentId, name, description, status, estimatedPricePerTask, capabilityProfile);
        openClawAgents.put(agent.getId(), agent);

        if (capabilityProfile != null) {
            createCapabilityPackage(
                agent.getId(),
                capabilityProfile.getTitle(),
                capabilityProfile.getSupportedTemplateIds(),
                capabilityProfile.getMinPrice(),
                capabilityProfile.getMaxPrice(),
                capabilityProfile.getAvailableCapacity()
            );
        }

        return agent;
    }

    public synchronized CapabilityPackage createCapabilityPackage(
        UUID ownerId,
        String title,
        List<UUID> supportedTemplateIds,
        BigDecimal minPrice,
        BigDecimal maxPrice,
        int availableCapacity
    ) {
        if (!openClawAgents.containsKey(ownerId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "owner not found");
        }
        for (UUID templateId : supportedTemplateIds) {
            if (!taskTemplates.containsKey(templateId)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unsupported template id: " + templateId);
            }
        }
        if (availableCapacity < 1) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "available_capacity must be >= 1");
        }
        if (minPrice.compareTo(maxPrice) > 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "min_price cannot be greater than max_price");
        }

        CapabilityPackage pkg = new CapabilityPackage(
            UUID.randomUUID(),
            ownerId,
            title,
            supportedTemplateIds,
            minPrice,
            maxPrice,
            availableCapacity
        );
        capabilityPackages.put(pkg.getId(), pkg);
        return pkg;
    }

    public synchronized Order createOrder(UUID buyerId, UUID capabilityPackageId, UUID taskTemplateId, Map<String, String> inputs) {
        if (!openClawAgents.containsKey(buyerId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "buyer not found");
        }

        CapabilityPackage capabilityPackage = capabilityPackages.get(capabilityPackageId);
        if (capabilityPackage == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "capability package not found");
        }

        TaskTemplate taskTemplate = taskTemplates.get(taskTemplateId);
        if (taskTemplate == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "task template not found");
        }

        if (!capabilityPackage.getSupportedTemplateIds().contains(taskTemplateId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "package does not support this template");
        }

        validateTemplateInputs(taskTemplate, inputs);

        Order order = new Order(
            UUID.randomUUID(),
            buyerId,
            capabilityPackage.getOwnerId(),
            capabilityPackageId,
            taskTemplateId,
            inputs,
            Instant.now()
        );
        order.setSettlement(new Settlement(taskTemplate.getBasePrice(), Instant.now()));
        orders.put(order.getId(), order);
        return order;
    }

    public synchronized List<Order> listOrders() {
        return orders.values().stream().toList();
    }

    public synchronized Order getOrder(UUID orderId) {
        Order order = orders.get(orderId);
        if (order == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "order not found");
        }
        return order;
    }

    public synchronized Order acceptOrder(UUID orderId) {
        Order order = getOrder(orderId);
        ensureStatus(order, OrderStatus.CREATED);

        CapabilityPackage capabilityPackage = capabilityPackages.get(order.getCapabilityPackageId());
        if (capabilityPackage.getAvailableCapacity() < 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "owner has no available capacity");
        }

        capabilityPackage.decrementCapacity();
        order.setStatus(OrderStatus.ACCEPTED_BY_OWNER);
        order.touch(Instant.now());
        return order;
    }

    public synchronized Order startOrder(UUID orderId) {
        Order order = getOrder(orderId);
        ensureStatus(order, OrderStatus.ACCEPTED_BY_OWNER);
        order.setStatus(OrderStatus.IN_PROGRESS);
        order.touch(Instant.now());
        return order;
    }

    public synchronized Order deliverOrder(UUID orderId, String format, String content) {
        Order order = getOrder(orderId);
        ensureStatus(order, OrderStatus.IN_PROGRESS);
        order.setDeliverable(new Deliverable(format, content, Instant.now()));
        order.setStatus(OrderStatus.DELIVERED);
        order.touch(Instant.now());
        return order;
    }

    public synchronized Order buyerAcceptOrder(UUID orderId, List<String> passedItems, String note) {
        Order order = getOrder(orderId);
        ensureStatus(order, OrderStatus.DELIVERED);
        TaskTemplate template = taskTemplates.get(order.getTaskTemplateId());

        if (!passedItems.containsAll(template.getAcceptanceChecklist())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "all checklist items must be accepted");
        }

        order.setAcceptance(new Acceptance(passedItems, note, Instant.now()));
        order.setStatus(OrderStatus.BUYER_ACCEPTED);
        order.touch(Instant.now());
        return order;
    }

    public synchronized Order settleOrder(UUID orderId) {
        Order order = getOrder(orderId);
        ensureStatus(order, OrderStatus.BUYER_ACCEPTED);

        Settlement settlement = order.getSettlement();
        if (settlement == null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "missing settlement record");
        }
        settlement.release(Instant.now());
        order.setStatus(OrderStatus.SETTLED);
        order.touch(Instant.now());
        return order;
    }

    public synchronized Order disputeOrder(UUID orderId, String reason) {
        Order order = getOrder(orderId);
        if (order.getStatus() == OrderStatus.SETTLED || order.getStatus() == OrderStatus.REFUNDED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "cannot dispute after settlement or refund");
        }
        order.setDispute(new Dispute(reason, Instant.now()));
        order.setStatus(OrderStatus.DISPUTED);
        order.touch(Instant.now());
        return order;
    }

    public synchronized Order rejectOrder(UUID orderId) {
        Order order = getOrder(orderId);
        if (order.getStatus() != OrderStatus.CREATED && order.getStatus() != OrderStatus.ACCEPTED_BY_OWNER) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order can only be rejected before work starts");
        }
        order.setStatus(OrderStatus.REJECTED);
        order.touch(Instant.now());
        return order;
    }

    public synchronized Order refundOrder(UUID orderId) {
        Order order = getOrder(orderId);
        if (order.getStatus() != OrderStatus.DISPUTED && order.getStatus() != OrderStatus.REJECTED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "refund requires disputed or rejected status");
        }
        order.setStatus(OrderStatus.REFUNDED);
        order.touch(Instant.now());
        return order;
    }

    private void validateTemplateInputs(TaskTemplate taskTemplate, Map<String, String> inputs) {
        for (String key : taskTemplate.getRequiredInputs()) {
            String value = inputs.get(key);
            if (value == null || value.isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "missing required input: " + key);
            }
        }
    }

    private void ensureStatus(Order order, OrderStatus expected) {
        if (order.getStatus() != expected) {
            throw new ResponseStatusException(
                HttpStatus.CONFLICT,
                "invalid order status: expected " + expected + " but was " + order.getStatus()
            );
        }
    }

    private boolean isRentalActive(OrderStatus status) {
        return status == OrderStatus.CREATED
            || status == OrderStatus.ACCEPTED_BY_OWNER
            || status == OrderStatus.IN_PROGRESS
            || status == OrderStatus.DELIVERED
            || status == OrderStatus.BUYER_ACCEPTED
            || status == OrderStatus.DISPUTED;
    }

    private void seedTaskTemplates() {
        TaskTemplate researchBrief = new TaskTemplate(
            UUID.randomUUID(),
            "Research Brief",
            "Produce a structured brief with scope, findings, and recommendations.",
            List.of("topic", "goal", "target_audience"),
            List.of("all_required_sections_present", "citations_or_sources_included", "actionable_recommendations"),
            24,
            new BigDecimal("49.00")
        );

        TaskTemplate codeTask = new TaskTemplate(
            UUID.randomUUID(),
            "Code Task",
            "Deliver a bounded code change with clear run instructions and output.",
            List.of("repository_context", "task_scope", "acceptance_criteria"),
            List.of("code_runs", "scope_completed", "acceptance_criteria_met"),
            48,
            new BigDecimal("99.00")
        );

        TaskTemplate contentDraft = new TaskTemplate(
            UUID.randomUUID(),
            "Content Draft",
            "Create a structured content draft with defined tone and format.",
            List.of("topic", "tone", "output_format"),
            List.of("requested_tone_followed", "format_followed", "no_missing_sections"),
            24,
            new BigDecimal("39.00")
        );

        taskTemplates.put(researchBrief.getId(), researchBrief);
        taskTemplates.put(codeTask.getId(), codeTask);
        taskTemplates.put(contentDraft.getId(), contentDraft);
    }
}
