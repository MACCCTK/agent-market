package com.example.demo.marketplace.v1.api;

import com.example.demo.marketplace.v1.service.V1MarketplaceService;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
@Validated
@Tag(name = "Marketplace V1 API", description = "Task-based OpenClaw marketplace v1 endpoints")
public class V1MarketplaceController {

    private final V1MarketplaceService service;

    public V1MarketplaceController(V1MarketplaceService service) {
        this.service = service;
    }

    @PostMapping("/auth/register")
    @Operation(summary = "Register user", description = "Registers a new user and supports openclaw client registration")
    public V1MarketplaceService.AuthView register(@Valid @RequestBody RegisterRequest request) {
        return service.register(
            request.email(),
            request.password(),
            request.displayName(),
            request.roles(),
            request.clientType()
        );
    }

    @PostMapping("/auth/login")
    @Operation(summary = "Login user", description = "Logs in user and supports openclaw client role validation")
    public V1MarketplaceService.AuthView login(@Valid @RequestBody LoginRequest request) {
        return service.login(request.email(), request.password(), request.asRole(), request.clientType());
    }

    @GetMapping("/openclaws")
    @Operation(summary = "List OpenClaw agents", description = "Lists OpenClaw agents with subscription and service status")
    public List<V1MarketplaceService.OpenClawView> listOpenClaws() {
        return service.listOpenClaws();
    }

    @PostMapping("/openclaws/register")
    @Operation(summary = "Register OpenClaw profile", description = "Registers or updates an OpenClaw-only profile for persistent routing")
    public V1MarketplaceService.OpenClawProfileView registerOpenClaw(@Valid @RequestBody RegisterOpenClawRequest request) {
        return service.registerOpenClaw(
            request.id(),
            request.name(),
            request.capacityPerWeek(),
            request.serviceConfig(),
            request.subscriptionStatus(),
            request.serviceStatus()
        );
    }

    @GetMapping("/openclaws/search")
    @Operation(summary = "Fuzzy search OpenClaw agents", description = "Searches by id, name, subscription status, or service status using case-insensitive partial match")
    public List<V1MarketplaceService.OpenClawView> searchOpenClaws(
        @RequestParam(required = false) String keyword,
        @RequestParam(defaultValue = "0") @Min(0) int page,
        @RequestParam(defaultValue = "20") @Min(1) int size
    ) {
        return service.searchOpenClaws(keyword, page, size);
    }

    @PostMapping("/openclaws/{id}/subscription")
    @Operation(summary = "Update OpenClaw subscription", description = "Changes OpenClaw subscription status when service is subscribed/unsubscribed")
    public V1MarketplaceService.OpenClawView updateOpenClawSubscription(@PathVariable long id, @Valid @RequestBody UpdateSubscriptionRequest request) {
        return service.updateOpenClawSubscription(id, request.subscriptionStatus());
    }

    @PostMapping("/openclaws/{id}/service-status")
    @Operation(summary = "OpenClaw service callback status", description = "OpenClaw service reports runtime status during/after fulfillment")
    public V1MarketplaceService.OpenClawView reportOpenClawServiceStatus(@PathVariable long id, @Valid @RequestBody UpdateServiceStatusRequest request) {
        return service.reportOpenClawServiceStatus(id, request.serviceStatus(), request.activeOrderId());
    }

    @PostMapping("/openclaws/{id}/orders")
    @Operation(summary = "Publish order by OpenClaw", description = "OpenClaw publishes an order as task initiator")
    public V1MarketplaceService.OrderView publishOrderByOpenClaw(@PathVariable long id, @Valid @RequestBody PublishOrderByOpenClawRequest request) {
        return service.publishOrderByOpenClaw(id, request.taskTemplateId(), request.capabilityPackageId(), request.title(), request.requirementPayload());
    }

    @PostMapping("/openclaws/{id}/orders/{orderId}/accept")
    @Operation(summary = "Accept order by OpenClaw", description = "OpenClaw accepts order as fulfillment主体")
    public V1MarketplaceService.OrderView acceptOrderByOpenClaw(@PathVariable long id, @PathVariable long orderId) {
        return service.acceptOrderByOpenClaw(orderId, id);
    }

    @PostMapping("/openclaws/{id}/orders/{orderId}/notify-result-ready")
    @Operation(summary = "Notify result ready", description = "Executor OpenClaw notifies requester OpenClaw that result is ready for acceptance")
    public V1MarketplaceService.OrderView notifyResultReady(@PathVariable long id, @PathVariable long orderId, @Valid @RequestBody NotifyResultReadyRequest request) {
        return service.notifyResultReady(orderId, id, request.resultSummary());
    }

    @PostMapping("/openclaws/{id}/orders/{orderId}/receive-result")
    @Operation(summary = "Receive result by requester", description = "Requester OpenClaw accepts executor result and completes A<-B handoff")
    public V1MarketplaceService.OrderView receiveResult(@PathVariable long id, @PathVariable long orderId, @Valid @RequestBody ReceiveResultRequest request) {
        return service.receiveResult(orderId, id, request.checklistResult(), request.note());
    }

    @PostMapping("/openclaws/{id}/orders/{orderId}/settle")
    @Operation(summary = "Settle by token usage", description = "Settles fee with hire fee + actual token consumption (100 token = 1 SGD)")
    public V1MarketplaceService.SettlementFeeView settleOrderByTokenUsage(
        @PathVariable long id,
        @PathVariable long orderId,
        @Valid @RequestBody SettleByTokenUsageRequest request
    ) {
        return service.settleOrderByTokenUsage(orderId, id, request.tokenUsed());
    }

    @GetMapping("/task-templates")
    @Operation(summary = "List task templates", description = "Lists v1 task templates with pagination")
    public List<V1MarketplaceService.TaskTemplateView> listTaskTemplates(
        @RequestParam(defaultValue = "0") @Min(0) int page,
        @RequestParam(defaultValue = "20") @Min(1) int size,
        @RequestParam(defaultValue = "id,asc") String sort
    ) {
        return service.listTemplates(page, size, sort);
    }

    @GetMapping("/marketplace/capability-packages")
    @Operation(summary = "List marketplace capability packages", description = "Lists active capability packages with pagination")
    public List<V1MarketplaceService.CapabilityPackageView> listMarketplaceCapabilityPackages(
        @RequestParam(defaultValue = "0") @Min(0) int page,
        @RequestParam(defaultValue = "20") @Min(1) int size,
        @RequestParam(defaultValue = "id,asc") String sort
    ) {
        return service.listMarketplacePackages(page, size, sort);
    }

    @PostMapping("/openclaws/capability-packages")
    @Operation(summary = "Create OpenClaw capability package", description = "Creates capability package under OpenClaw profile")
    public V1MarketplaceService.CapabilityPackageView createOwnerCapabilityPackage(@Valid @RequestBody CreateCapabilityPackageRequest request) {
        return service.createOwnerCapabilityPackage(
            request.ownerOpenClawId(),
            request.title(),
            request.summary(),
            request.taskTemplateId(),
            request.sampleDeliverables(),
            request.priceMin(),
            request.priceMax(),
            request.capacityPerWeek(),
            request.status()
        );
    }

    @PostMapping("/orders")
    @Operation(summary = "Create order", description = "Creates requester OpenClaw order from task template and optional capability package")
    public V1MarketplaceService.OrderView createOrder(@Valid @RequestBody CreateOrderRequest request) {
        return service.createOrder(
            request.requesterOpenClawId(),
            request.taskTemplateId(),
            request.capabilityPackageId(),
            request.title(),
            request.requirementPayload()
        );
    }

    @PostMapping("/orders/{id}/accept")
    @Operation(summary = "Accept order", description = "Executor OpenClaw accepts an order")
    public V1MarketplaceService.OrderView acceptOrder(@PathVariable long id) {
        return service.acceptOrder(id);
    }

    @PostMapping("/orders/{id}/assign")
    @Operation(summary = "Assign order", description = "Assigns an order to a target OpenClaw or auto-picks an available executor")
    public V1MarketplaceService.OrderView assignOrder(@PathVariable long id, @Valid @RequestBody AssignOrderRequest request) {
        return service.assignOrder(id, request.executorOpenClawId());
    }

    @PostMapping("/orders/{id}/deliverables")
    @Operation(summary = "Submit deliverable", description = "Submits a new deliverable version for order")
    public V1MarketplaceService.DeliverableView submitDeliverable(@PathVariable long id, @Valid @RequestBody SubmitDeliverableRequest request) {
        return service.submitDeliverable(id, request.deliveryNote(), request.deliverablePayload(), request.submittedByOpenClawId());
    }

    @PostMapping("/orders/{id}/acceptance/approve")
    @Operation(summary = "Approve acceptance", description = "Requester OpenClaw approves delivered work with checklist result")
    public V1MarketplaceService.OrderView approveAcceptance(@PathVariable long id, @Valid @RequestBody ApproveAcceptanceRequest request) {
        return service.approveAcceptance(id, request.requesterOpenClawId(), request.checklistResult(), request.comment());
    }

    @PostMapping("/orders/{id}/disputes")
    @Operation(summary = "Create dispute", description = "Opens dispute for an order")
    public V1MarketplaceService.DisputeView createDispute(@PathVariable long id, @Valid @RequestBody CreateDisputeRequest request) {
        return service.createDispute(id, request.openedByOpenClawId(), request.reasonCode(), request.description());
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record RegisterOpenClawRequest(
        @Schema(description = "Optional OpenClaw id") Long id,
        @Schema(description = "OpenClaw display name") @NotBlank String name,
        @Schema(description = "Declared weekly capacity") @Min(1) int capacityPerWeek,
        @Schema(description = "Service configuration payload") @NotNull Map<String, Object> serviceConfig,
        @Schema(description = "Subscription status", example = "subscribed") @NotBlank String subscriptionStatus,
        @Schema(description = "Service status", example = "available") @NotBlank String serviceStatus
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record CreateCapabilityPackageRequest(
        @Schema(description = "Owner OpenClaw id") @NotNull Long ownerOpenClawId,
        @Schema(description = "Package title") @NotBlank String title,
        @Schema(description = "Package summary") @NotBlank String summary,
        @Schema(description = "Task template id") @NotNull Long taskTemplateId,
        @Schema(description = "Sample deliverables payload") Map<String, Object> sampleDeliverables,
        @Schema(description = "Minimum package price") @DecimalMin("0.00") BigDecimal priceMin,
        @Schema(description = "Maximum package price") @DecimalMin("0.00") BigDecimal priceMax,
        @Schema(description = "Weekly capacity") @Min(1) int capacityPerWeek,
        @Schema(description = "Package status", example = "active") @NotBlank String status
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record CreateOrderRequest(
        @Schema(description = "Requester OpenClaw id") @NotNull Long requesterOpenClawId,
        @Schema(description = "Task template id") @NotNull Long taskTemplateId,
        @Schema(description = "Optional capability package id") Long capabilityPackageId,
        @Schema(description = "Order title") @NotBlank String title,
        @Schema(description = "Requirement payload") @NotNull Map<String, Object> requirementPayload
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record AssignOrderRequest(
        @Schema(description = "Optional executor OpenClaw id. If omitted, the service auto-picks an available executor") Long executorOpenClawId
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record SubmitDeliverableRequest(
        @Schema(description = "Delivery note") @NotBlank String deliveryNote,
        @Schema(description = "Deliverable payload") @NotNull Map<String, Object> deliverablePayload,
        @Schema(description = "Executor OpenClaw id") @NotNull Long submittedByOpenClawId
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record ApproveAcceptanceRequest(
        @Schema(description = "Requester OpenClaw id") @NotNull Long requesterOpenClawId,
        @Schema(description = "Checklist result") @NotNull Map<String, Object> checklistResult,
        @Schema(description = "Optional review comment") String comment
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record NotifyResultReadyRequest(
        @Schema(description = "Result summary payload") @NotNull Map<String, Object> resultSummary
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record ReceiveResultRequest(
        @Schema(description = "Checklist result by requester") @NotNull Map<String, Object> checklistResult,
        @Schema(description = "Optional note") String note
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record CreateDisputeRequest(
        @Schema(description = "Dispute opener OpenClaw id") @NotNull Long openedByOpenClawId,
        @Schema(description = "Reason code", example = "quality_not_met") @NotBlank String reasonCode,
        @Schema(description = "Dispute description") @NotBlank String description
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record RegisterRequest(
        @Schema(description = "Email") @NotBlank String email,
        @Schema(description = "Plain password for demo", example = "secret123") @NotBlank String password,
        @Schema(description = "Display name") @NotBlank String displayName,
        @Schema(description = "Roles list, supports openclaw") List<String> roles,
        @Schema(description = "Client type, set openclaw for OpenClaw login/register") String clientType
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record LoginRequest(
        @Schema(description = "Email") @NotBlank String email,
        @Schema(description = "Plain password for demo", example = "secret123") @NotBlank String password,
        @Schema(description = "Optional role to login as", example = "openclaw") String asRole,
        @Schema(description = "Client type, set openclaw for OpenClaw") String clientType
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record UpdateSubscriptionRequest(
        @Schema(description = "Subscription status: subscribed/unsubscribed", example = "subscribed") @NotBlank String subscriptionStatus
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record UpdateServiceStatusRequest(
        @Schema(description = "Service status: available/busy/offline/paused", example = "busy") @NotBlank String serviceStatus,
        @Schema(description = "Current active order id") Long activeOrderId
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record PublishOrderByOpenClawRequest(
        @Schema(description = "Task template id") @NotNull Long taskTemplateId,
        @Schema(description = "Optional capability package id") Long capabilityPackageId,
        @Schema(description = "Order title") @NotBlank String title,
        @Schema(description = "Requirement payload") @NotNull Map<String, Object> requirementPayload
    ) {
    }

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record SettleByTokenUsageRequest(
        @Schema(description = "Actual consumed token count", example = "860") @NotNull Long tokenUsed
    ) {
    }
}
