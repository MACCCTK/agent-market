package com.example.demo.marketplace.api;

import com.example.demo.marketplace.domain.CapabilityPackage;
import com.example.demo.marketplace.domain.AgentCapabilityProfile;
import com.example.demo.marketplace.domain.OpenClawAgent;
import com.example.demo.marketplace.domain.OpenClawAgentStatus;
import com.example.demo.marketplace.domain.Order;
import com.example.demo.marketplace.domain.TaskTemplate;
import com.example.demo.marketplace.service.MarketplaceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@Validated
@Tag(name = "Marketplace Legacy API", description = "Initial in-memory marketplace endpoints")
public class MarketplaceController {

    private final MarketplaceService marketplaceService;

    public MarketplaceController(MarketplaceService marketplaceService) {
        this.marketplaceService = marketplaceService;
    }

    @GetMapping("/health")
    @Operation(summary = "Service health check", description = "Returns backend health and service identifier")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "openclaw-marketplace-backend");
    }

    @GetMapping("/task-templates")
    @Operation(summary = "List task templates", description = "Lists seeded task templates")
    public List<TaskTemplate> listTaskTemplates() {
        return marketplaceService.listTaskTemplates();
    }

    @GetMapping("/capability-packages")
    @Operation(summary = "List capability packages", description = "Lists all capability packages")
    public List<CapabilityPackage> listCapabilityPackages() {
        return marketplaceService.listCapabilityPackages();
    }

    @GetMapping("/openclaw-agents")
    @Operation(summary = "List OpenClaw agents", description = "Lists all registered OpenClaw agents")
    public List<OpenClawAgent> listOpenClawAgents() {
        return marketplaceService.listOpenClawAgents();
    }

    @GetMapping("/openclaw-agents/listed")
    @Operation(summary = "List listed OpenClaw agents", description = "Lists agents that currently have at least one capability listing")
    public List<OpenClawAgent> listListedOpenClawAgents() {
        return marketplaceService.listListedOpenClawAgents();
    }

    @GetMapping("/openclaw-agents/{agentId}/rental-status")
    @Operation(summary = "Query agent rental status", description = "Checks whether a given agent is currently rented by active orders")
    public RentalStatusResponse getOpenClawAgentRentalStatus(@PathVariable UUID agentId) {
        return new RentalStatusResponse(agentId, marketplaceService.isOpenClawAgentRented(agentId));
    }

    @PostMapping("/buyers")
    @Operation(summary = "Create buyer agent", description = "Creates an OpenClaw agent as buyer profile")
    public OpenClawAgent createBuyer(@Valid @RequestBody CreateOpenClawAgentRequest request) {
        return marketplaceService.createBuyer(
            request.id(),
            request.name(),
            request.description(),
            request.status(),
            request.estimatedPricePerTask(),
            toDomainCapabilityProfile(request.capabilityProfile())
        );
    }

    @PostMapping("/agent-owners")
    @Operation(summary = "Create owner agent", description = "Creates an OpenClaw agent as owner profile")
    public OpenClawAgent createOwner(@Valid @RequestBody CreateOpenClawAgentRequest request) {
        return marketplaceService.createOwner(
            request.id(),
            request.name(),
            request.description(),
            request.status(),
            request.estimatedPricePerTask(),
            toDomainCapabilityProfile(request.capabilityProfile())
        );
    }

    @PostMapping("/orders")
    @Operation(summary = "Create order", description = "Creates an order from buyer to a capability package")
    public Order createOrder(@Valid @RequestBody CreateOrderRequest request) {
        return marketplaceService.createOrder(
            request.buyerId(),
            request.capabilityPackageId(),
            request.taskTemplateId(),
            request.inputs()
        );
    }

    @GetMapping("/orders")
    @Operation(summary = "List orders", description = "Lists all orders")
    public List<Order> listOrders() {
        return marketplaceService.listOrders();
    }

    @GetMapping("/orders/{orderId}")
    @Operation(summary = "Get order by id", description = "Fetches a single order by order id")
    public Order getOrder(@PathVariable UUID orderId) {
        return marketplaceService.getOrder(orderId);
    }

    @PostMapping("/orders/{orderId}/accept")
    @Operation(summary = "Accept order", description = "Owner accepts an order and reserves capacity")
    public Order acceptOrder(@PathVariable UUID orderId) {
        return marketplaceService.acceptOrder(orderId);
    }

    @PostMapping("/orders/{orderId}/start")
    @Operation(summary = "Start order", description = "Moves order into in-progress state")
    public Order startOrder(@PathVariable UUID orderId) {
        return marketplaceService.startOrder(orderId);
    }

    @PostMapping("/orders/{orderId}/deliver")
    @Operation(summary = "Deliver order", description = "Submits structured deliverable for an order")
    public Order deliverOrder(@PathVariable UUID orderId, @Valid @RequestBody DeliverOrderRequest request) {
        return marketplaceService.deliverOrder(orderId, request.format(), request.content());
    }

    @PostMapping("/orders/{orderId}/buyer-accept")
    @Operation(summary = "Buyer accept order", description = "Buyer approves all acceptance checklist items")
    public Order buyerAcceptOrder(@PathVariable UUID orderId, @Valid @RequestBody BuyerAcceptOrderRequest request) {
        return marketplaceService.buyerAcceptOrder(orderId, request.passedItems(), request.note());
    }

    @PostMapping("/orders/{orderId}/settle")
    @Operation(summary = "Settle order", description = "Releases escrow and settles accepted order")
    public Order settleOrder(@PathVariable UUID orderId) {
        return marketplaceService.settleOrder(orderId);
    }

    @PostMapping("/orders/{orderId}/dispute")
    @Operation(summary = "Dispute order", description = "Opens a dispute for an order")
    public Order disputeOrder(@PathVariable UUID orderId, @Valid @RequestBody DisputeOrderRequest request) {
        return marketplaceService.disputeOrder(orderId, request.reason());
    }

    @PostMapping("/orders/{orderId}/reject")
    @Operation(summary = "Reject order", description = "Rejects an order before work starts")
    public Order rejectOrder(@PathVariable UUID orderId) {
        return marketplaceService.rejectOrder(orderId);
    }

    @PostMapping("/orders/{orderId}/refund")
    @Operation(summary = "Refund order", description = "Refunds an order in rejected or disputed status")
    public Order refundOrder(@PathVariable UUID orderId) {
        return marketplaceService.refundOrder(orderId);
    }

    public record CreateOpenClawAgentRequest(
        @Schema(description = "Optional agent id. If absent, backend generates one") UUID id,
        @Schema(description = "Agent display name", example = "OpenClaw Alpha") @NotBlank String name,
        @Schema(description = "Agent profile description", example = "General purpose coding and research") @NotBlank String description,
        @Schema(description = "Agent service status", example = "ACTIVE") @NotNull OpenClawAgentStatus status,
        @Schema(description = "Estimated price per task", example = "99.00") @NotNull @DecimalMin("0.01") BigDecimal estimatedPricePerTask,
        @Schema(description = "Optional capability profile for listing") @Valid CapabilityProfileRequest capabilityProfile
    ) {
    }

    public record CapabilityProfileRequest(
        @Schema(description = "Capability package title", example = "Research Package") @NotBlank String title,
        @Schema(description = "Supported task template ids") @NotEmpty List<UUID> supportedTemplateIds,
        @Schema(description = "Minimum price", example = "50.00") @NotNull @DecimalMin("0.01") BigDecimal minPrice,
        @Schema(description = "Maximum price", example = "200.00") @NotNull @DecimalMin("0.01") BigDecimal maxPrice,
        @Schema(description = "Available capacity", example = "3") @Min(1) int availableCapacity
    ) {
    }

    public record CreateOrderRequest(
        @Schema(description = "Buyer agent id") @NotNull UUID buyerId,
        @Schema(description = "Capability package id") @NotNull UUID capabilityPackageId,
        @Schema(description = "Task template id") @NotNull UUID taskTemplateId,
        @Schema(description = "Input payload map") @NotNull Map<String, String> inputs
    ) {
    }

    public record DeliverOrderRequest(
        @Schema(description = "Deliverable format", example = "markdown") @NotBlank String format,
        @Schema(description = "Deliverable content") @NotBlank String content
    ) {
    }

    public record BuyerAcceptOrderRequest(
        @Schema(description = "Accepted checklist items") @NotEmpty List<String> passedItems,
        @Schema(description = "Optional buyer note") String note
    ) {
    }

    public record DisputeOrderRequest(@Schema(description = "Dispute reason") @NotBlank String reason) {
    }

    public record RentalStatusResponse(
        @Schema(description = "Agent id") UUID agentId,
        @Schema(description = "Whether the agent is rented") boolean rented
    ) {
    }

    private AgentCapabilityProfile toDomainCapabilityProfile(CapabilityProfileRequest request) {
        if (request == null) {
            return null;
        }
        return new AgentCapabilityProfile(
            request.title(),
            request.supportedTemplateIds(),
            request.minPrice(),
            request.maxPrice(),
            request.availableCapacity()
        );
    }
}
