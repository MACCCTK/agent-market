package com.example.demo.marketplace.v1.service;

import com.example.demo.marketplace.v1.error.ApiException;
import com.example.demo.marketplace.v1.model.V1OrderStatus;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class V1MarketplaceService {

    public record UserView(long id, String email, String displayName, String status, List<String> roles, Instant createdAt, Instant updatedAt) {
    }

    public record AuthView(String accessToken, String tokenType, UserView user) {
    }

    public record OpenClawView(
        long id,
        String name,
        String subscriptionStatus,
        String serviceStatus,
        Long activeOrderId,
        Instant updatedAt
    ) {
    }

    public record OpenClawProfileView(
        long id,
        String name,
        int capacityPerWeek,
        Map<String, Object> serviceConfig,
        String subscriptionStatus,
        String serviceStatus,
        Instant updatedAt
    ) {
    }

    public record SettlementFeeView(
        long orderId,
        long openClawId,
        BigDecimal hireFee,
        long tokenUsed,
        BigDecimal tokenFee,
        BigDecimal totalFee,
        String currency,
        Instant settledAt
    ) {
    }

    private static final Set<String> ALLOWED_ROLES = Set.of("openclaw", "admin");
    private static final Set<String> OPENCLAW_SUBSCRIPTION_STATUSES = Set.of("subscribed", "unsubscribed");
    private static final Set<String> OPENCLAW_SERVICE_STATUSES = Set.of("available", "busy", "offline", "paused");
    private static final BigDecimal TOKEN_PRICE_PER_100 = new BigDecimal("1.00");
    private static final String SQLITE_URL = "jdbc:sqlite:data/marketplace.db";

    public record TaskTemplateView(
        long id,
        String code,
        String name,
        String taskType,
        String description,
        Map<String, Object> inputSchema,
        Map<String, Object> outputSchema,
        Map<String, Object> acceptanceSchema,
        String pricingModel,
        BigDecimal basePrice,
        int slaHours,
        String status
    ) {
    }

    public record CapabilityPackageView(
        long id,
        long ownerOpenClawId,
        String title,
        String summary,
        long taskTemplateId,
        Map<String, Object> sampleDeliverables,
        BigDecimal priceMin,
        BigDecimal priceMax,
        int capacityPerWeek,
        String status,
        Instant createdAt,
        Instant updatedAt
    ) {
    }

    public record OrderView(
        long id,
        String orderNo,
        long requesterOpenClawId,
        Long executorOpenClawId,
        long taskTemplateId,
        Long capabilityPackageId,
        String title,
        String status,
        BigDecimal quotedPrice,
        String currency,
        int slaHours,
        Map<String, Object> requirementPayload,
        Instant acceptedAt,
        Instant deliveredAt,
        Instant completedAt,
        Instant cancelledAt,
        Instant createdAt,
        Instant updatedAt
    ) {
    }

    public record DeliverableView(long id, long orderId, int versionNo, String deliveryNote, Map<String, Object> deliverablePayload, long submittedBy, Instant submittedAt) {
    }

    public record DisputeView(long id, long orderId, long openedBy, String reasonCode, String description, String status, Instant createdAt) {
    }

    private static final List<String> FIXED_TASK_TYPES = List.of(
        "research_brief",
        "content_draft",
        "code_fix_small_automation",
        "data_cleanup_analysis",
        "workflow_setup"
    );

    private static final Map<String, BigDecimal> TASK_HIRE_FEES = Map.of(
        "research_brief", new BigDecimal("1.00"),
        "content_draft", new BigDecimal("2.00"),
        "code_fix_small_automation", new BigDecimal("3.00"),
        "data_cleanup_analysis", new BigDecimal("4.00"),
        "workflow_setup", new BigDecimal("5.00")
    );

    private final AtomicLong templateSeq = new AtomicLong(1);
    private final AtomicLong packageSeq = new AtomicLong(1);
    private final AtomicLong orderSeq = new AtomicLong(1);
    private final AtomicLong deliverableSeq = new AtomicLong(1);
    private final AtomicLong disputeSeq = new AtomicLong(1);
    private final AtomicLong userSeq = new AtomicLong(1);
    private final AtomicLong openClawSeq = new AtomicLong(2001);

    private final Map<Long, TaskTemplateView> templates = new LinkedHashMap<>();
    private final Map<Long, CapabilityPackageView> capabilityPackages = new LinkedHashMap<>();
    private final Map<Long, OrderView> orders = new LinkedHashMap<>();
    private final Map<Long, List<DeliverableView>> deliverables = new LinkedHashMap<>();
    private final Map<Long, List<DisputeView>> disputes = new LinkedHashMap<>();
    private final Map<Long, UserView> users = new LinkedHashMap<>();
    private final Map<String, Long> emailToUserId = new LinkedHashMap<>();
    private final Map<Long, String> userPasswordHashes = new LinkedHashMap<>();
    private final Map<Long, OpenClawView> openClaws = new LinkedHashMap<>();
    private final Map<Long, OpenClawProfileView> openClawProfiles = new LinkedHashMap<>();
    private final Map<Long, SettlementFeeView> settlementFeesByOrderId = new LinkedHashMap<>();
    private final ObjectMapper objectMapper = new ObjectMapper();

    public V1MarketplaceService() {
        ensurePersistenceTables();
        seedTemplates();
        seedOpenClaws();
    }

    public AuthView register(String email, String password, String displayName, List<String> roles, String clientType) {
        if (emailToUserId.containsKey(email.toLowerCase())) {
            throw new ApiException("AUTH_EMAIL_EXISTS", HttpStatus.CONFLICT, "Email already exists");
        }

        List<String> normalizedRoles = normalizeRoles(roles);
        if ("openclaw".equalsIgnoreCase(clientType) && !normalizedRoles.contains("openclaw")) {
            normalizedRoles = new ArrayList<>(normalizedRoles);
            normalizedRoles.add("openclaw");
        }

        long userId = userSeq.getAndIncrement();
        Instant now = Instant.now();
        UserView user = new UserView(userId, email.toLowerCase(), displayName, "active", List.copyOf(normalizedRoles), now, now);
        users.put(userId, user);
        emailToUserId.put(user.email(), userId);
        userPasswordHashes.put(userId, hash(password));

        return new AuthView(generateToken(user), "Bearer", user);
    }

    public AuthView login(String email, String password, String asRole, String clientType) {
        Long userId = emailToUserId.get(email.toLowerCase());
        if (userId == null) {
            throw new ApiException("AUTH_INVALID_CREDENTIALS", HttpStatus.UNAUTHORIZED, "Invalid email or password");
        }

        String savedHash = userPasswordHashes.get(userId);
        if (!savedHash.equals(hash(password))) {
            throw new ApiException("AUTH_INVALID_CREDENTIALS", HttpStatus.UNAUTHORIZED, "Invalid email or password");
        }

        UserView user = users.get(userId);
        if (asRole != null && !asRole.isBlank() && user.roles().stream().noneMatch(role -> role.equalsIgnoreCase(asRole))) {
            throw new ApiException("AUTH_ROLE_DENIED", HttpStatus.FORBIDDEN, "User does not have requested role");
        }
        if ("openclaw".equalsIgnoreCase(clientType) && user.roles().stream().noneMatch(role -> role.equalsIgnoreCase("openclaw"))) {
            throw new ApiException("AUTH_ROLE_DENIED", HttpStatus.FORBIDDEN, "OpenClaw access requires openclaw role");
        }

        return new AuthView(generateToken(user), "Bearer", user);
    }

    public List<OpenClawView> listOpenClaws() {
        return new ArrayList<>(openClaws.values());
    }

    public OpenClawProfileView registerOpenClaw(
        Long id,
        String name,
        int capacityPerWeek,
        Map<String, Object> serviceConfig,
        String subscriptionStatus,
        String serviceStatus
    ) {
        long openClawId = id == null ? openClawSeq.getAndIncrement() : id;
        openClawSeq.set(Math.max(openClawSeq.get(), openClawId + 1));

        String normalizedSubscription = normalizeOpenClawSubscriptionStatus(subscriptionStatus);
        String normalizedService = normalizeOpenClawServiceStatus(serviceStatus);
        Instant now = Instant.now();

        OpenClawView openClawView = new OpenClawView(openClawId, name, normalizedSubscription, normalizedService, null, now);
        openClaws.put(openClawId, openClawView);

        OpenClawProfileView profile = new OpenClawProfileView(
            openClawId,
            name,
            capacityPerWeek,
            serviceConfig == null ? Map.of() : Map.copyOf(serviceConfig),
            normalizedSubscription,
            normalizedService,
            now
        );
        openClawProfiles.put(openClawId, profile);
        persistOpenClawProfile(profile);
        return profile;
    }

    public List<OpenClawView> searchOpenClaws(String keyword, int page, int size) {
        String q = keyword == null ? "" : keyword.trim().toLowerCase();
        List<OpenClawView> matched = openClaws
            .values()
            .stream()
            .filter(openClaw -> {
                if (q.isEmpty()) {
                    return true;
                }
                return openClaw.name().toLowerCase().contains(q)
                    || openClaw.subscriptionStatus().toLowerCase().contains(q)
                    || openClaw.serviceStatus().toLowerCase().contains(q)
                    || String.valueOf(openClaw.id()).contains(q);
            })
            .sorted(Comparator.comparingLong(OpenClawView::id))
            .toList();

        int start = Math.max(page, 0) * Math.max(size, 1);
        if (start >= matched.size()) {
            return List.of();
        }
        int end = Math.min(start + Math.max(size, 1), matched.size());
        return matched.subList(start, end);
    }

    public OpenClawView updateOpenClawSubscription(long openClawId, String subscriptionStatus) {
        String status = normalizeOpenClawSubscriptionStatus(subscriptionStatus);
        OpenClawView current = requireOpenClaw(openClawId);
        String serviceStatus = "subscribed".equals(status) ? "available" : "offline";

        OpenClawView updated = new OpenClawView(current.id(), current.name(), status, serviceStatus, null, Instant.now());
        openClaws.put(openClawId, updated);
        persistOpenClawRuntime(updated);
        return updated;
    }

    public OpenClawView reportOpenClawServiceStatus(long openClawId, String serviceStatus, Long activeOrderId) {
        String status = normalizeOpenClawServiceStatus(serviceStatus);
        OpenClawView current = requireOpenClaw(openClawId);

        if (!"subscribed".equals(current.subscriptionStatus())) {
            throw new ApiException("OPENCLAW_NOT_SUBSCRIBED", HttpStatus.CONFLICT, "OpenClaw is not subscribed");
        }

        OpenClawView updated = new OpenClawView(current.id(), current.name(), current.subscriptionStatus(), status, activeOrderId, Instant.now());
        openClaws.put(openClawId, updated);
        persistOpenClawRuntime(updated);
        return updated;
    }

    public OrderView publishOrderByOpenClaw(long openClawId, long taskTemplateId, Long capabilityPackageId, String title, Map<String, Object> requirementPayload) {
        OpenClawView openClaw = requireOpenClaw(openClawId);
        if (!"subscribed".equals(openClaw.subscriptionStatus())) {
            throw new ApiException("OPENCLAW_NOT_SUBSCRIBED", HttpStatus.CONFLICT, "OpenClaw is not subscribed");
        }
        return createOrder(openClawId, taskTemplateId, capabilityPackageId, title, requirementPayload);
    }

    public OrderView acceptOrderByOpenClaw(long orderId, long openClawId) {
        OpenClawView openClaw = requireOpenClaw(openClawId);
        if (!"subscribed".equals(openClaw.subscriptionStatus())) {
            throw new ApiException("OPENCLAW_NOT_SUBSCRIBED", HttpStatus.CONFLICT, "OpenClaw is not subscribed");
        }

        OrderView order = requireOrder(orderId);
        if (!"created".equals(order.status()) && !"submitted".equals(order.status())) {
            throw new ApiException("ORDER_INVALID_STATUS", HttpStatus.CONFLICT, "Order cannot be accepted in current status");
        }

        OrderView updated = new OrderView(
            order.id(),
            order.orderNo(),
            order.requesterOpenClawId(),
            openClawId,
            order.taskTemplateId(),
            order.capabilityPackageId(),
            order.title(),
            V1OrderStatus.ACCEPTED.name().toLowerCase(),
            order.quotedPrice(),
            order.currency(),
            order.slaHours(),
            order.requirementPayload(),
            Instant.now(),
            order.deliveredAt(),
            order.completedAt(),
            order.cancelledAt(),
            order.createdAt(),
            Instant.now()
        );
        orders.put(orderId, updated);
        persistOrderSnapshot(updated);

        OpenClawView runtime = new OpenClawView(openClaw.id(), openClaw.name(), openClaw.subscriptionStatus(), "busy", orderId, Instant.now());
        openClaws.put(openClawId, runtime);
        persistOpenClawRuntime(runtime);
        return updated;
    }

    public SettlementFeeView settleOrderByTokenUsage(long orderId, long openClawId, long tokenUsed) {
        if (tokenUsed < 0) {
            throw new ApiException("TOKEN_USED_INVALID", HttpStatus.BAD_REQUEST, "tokenUsed must be >= 0");
        }

        OpenClawView openClaw = requireOpenClaw(openClawId);
        OrderView order = requireOrder(orderId);

        if (order.executorOpenClawId() == null || order.executorOpenClawId() != openClawId) {
            throw new ApiException("ORDER_OWNER_MISMATCH", HttpStatus.CONFLICT, "Order is not owned by this OpenClaw");
        }

        if (!"delivered".equals(order.status()) && !"approved".equals(order.status()) && !"in_progress".equals(order.status())) {
            throw new ApiException("ORDER_INVALID_STATUS", HttpStatus.CONFLICT, "Order cannot be settled in current status");
        }

        BigDecimal hireFee = order.quotedPrice();
        BigDecimal tokenFee = new BigDecimal(tokenUsed).divide(new BigDecimal("100"), 2, java.math.RoundingMode.HALF_UP).multiply(TOKEN_PRICE_PER_100);
        BigDecimal totalFee = hireFee.add(tokenFee);

        SettlementFeeView settlement = new SettlementFeeView(
            orderId,
            openClawId,
            hireFee,
            tokenUsed,
            tokenFee,
            totalFee,
            order.currency(),
            Instant.now()
        );
        settlementFeesByOrderId.put(orderId, settlement);

        OrderView updated = new OrderView(
            order.id(),
            order.orderNo(),
            order.requesterOpenClawId(),
            order.executorOpenClawId(),
            order.taskTemplateId(),
            order.capabilityPackageId(),
            order.title(),
            V1OrderStatus.SETTLED.name().toLowerCase(),
            order.quotedPrice(),
            order.currency(),
            order.slaHours(),
            order.requirementPayload(),
            order.acceptedAt(),
            order.deliveredAt(),
            Instant.now(),
            order.cancelledAt(),
            order.createdAt(),
            Instant.now()
        );
        orders.put(orderId, updated);
        persistOrderSnapshot(updated);

        OpenClawView runtime = new OpenClawView(openClaw.id(), openClaw.name(), openClaw.subscriptionStatus(), "available", null, Instant.now());
        openClaws.put(openClawId, runtime);
        persistOpenClawRuntime(runtime);
        return settlement;
    }

    public List<TaskTemplateView> listTemplates(int page, int size, String sort) {
        return pageAndSort(new ArrayList<>(templates.values()), page, size, sort, Comparator.comparingLong(TaskTemplateView::id));
    }

    public List<CapabilityPackageView> listMarketplacePackages(int page, int size, String sort) {
        List<CapabilityPackageView> active = capabilityPackages.values().stream().filter(p -> "active".equalsIgnoreCase(p.status())).toList();
        return pageAndSort(active, page, size, sort, Comparator.comparingLong(CapabilityPackageView::id));
    }

    public CapabilityPackageView createOwnerCapabilityPackage(
        long ownerOpenClawId,
        String title,
        String summary,
        long taskTemplateId,
        Map<String, Object> sampleDeliverables,
        BigDecimal priceMin,
        BigDecimal priceMax,
        int capacityPerWeek,
        String status
    ) {
        TaskTemplateView template = templates.get(taskTemplateId);
        if (template == null) {
            throw new ApiException("TASK_TEMPLATE_NOT_FOUND", HttpStatus.NOT_FOUND, "Task template not found");
        }
        if (priceMin != null && priceMax != null && priceMin.compareTo(priceMax) > 0) {
            throw new ApiException("PRICE_RANGE_INVALID", HttpStatus.BAD_REQUEST, "priceMin cannot be greater than priceMax");
        }

        Instant now = Instant.now();
        CapabilityPackageView view = new CapabilityPackageView(
            packageSeq.getAndIncrement(),
            ownerOpenClawId,
            title,
            summary,
            taskTemplateId,
            sampleDeliverables == null ? Map.of() : Map.copyOf(sampleDeliverables),
            priceMin,
            priceMax,
            capacityPerWeek,
            status,
            now,
            now
        );
        capabilityPackages.put(view.id(), view);
        return view;
    }

    public OrderView createOrder(long requesterOpenClawId, long taskTemplateId, Long capabilityPackageId, String title, Map<String, Object> requirementPayload) {
        requireOpenClaw(requesterOpenClawId);
        TaskTemplateView template = templates.get(taskTemplateId);
        if (template == null) {
            throw new ApiException("TASK_TEMPLATE_NOT_FOUND", HttpStatus.NOT_FOUND, "Task template not found");
        }

        BigDecimal hireFee = resolveHireFeeByTaskType(template.taskType());

        Long executorOpenClawId = null;
        if (capabilityPackageId != null) {
            CapabilityPackageView pkg = capabilityPackages.get(capabilityPackageId);
            if (pkg == null) {
                throw new ApiException("CAPABILITY_PACKAGE_NOT_FOUND", HttpStatus.NOT_FOUND, "Capability package not found");
            }
            executorOpenClawId = pkg.ownerOpenClawId();
        }

        long id = orderSeq.getAndIncrement();
        Instant now = Instant.now();
        OrderView view = new OrderView(
            id,
            "OC" + String.format("%08d", id),
            requesterOpenClawId,
            executorOpenClawId,
            taskTemplateId,
            capabilityPackageId,
            title,
            V1OrderStatus.CREATED.name().toLowerCase(),
            hireFee,
            "USD",
            template.slaHours(),
            requirementPayload == null ? Map.of() : Map.copyOf(requirementPayload),
            null,
            null,
            null,
            null,
            now,
            now
        );
        orders.put(id, view);
        persistOrderSnapshot(view);
        return view;
    }

    public OrderView acceptOrder(long orderId) {
        OrderView order = requireOrder(orderId);
        if (!"created".equals(order.status()) && !"submitted".equals(order.status())) {
            throw new ApiException("ORDER_INVALID_STATUS", HttpStatus.CONFLICT, "Order cannot be accepted in current status");
        }

        OrderView updated = new OrderView(
            order.id(),
            order.orderNo(),
            order.requesterOpenClawId(),
            order.executorOpenClawId(),
            order.taskTemplateId(),
            order.capabilityPackageId(),
            order.title(),
            V1OrderStatus.ACCEPTED.name().toLowerCase(),
            order.quotedPrice(),
            order.currency(),
            order.slaHours(),
            order.requirementPayload(),
            Instant.now(),
            order.deliveredAt(),
            order.completedAt(),
            order.cancelledAt(),
            order.createdAt(),
            Instant.now()
        );
        orders.put(orderId, updated);
        persistOrderSnapshot(updated);
        return updated;
    }

    public DeliverableView submitDeliverable(long orderId, String deliveryNote, Map<String, Object> payload, long submittedBy) {
        OrderView order = requireOrder(orderId);
        if (!"accepted".equals(order.status()) && !"in_progress".equals(order.status())) {
            throw new ApiException("ORDER_INVALID_STATUS", HttpStatus.CONFLICT, "Order cannot be delivered in current status");
        }
        if (order.executorOpenClawId() == null || order.executorOpenClawId() != submittedBy) {
            throw new ApiException("ORDER_EXECUTOR_MISMATCH", HttpStatus.CONFLICT, "Only assigned executor OpenClaw can submit deliverable");
        }

        List<DeliverableView> versions = deliverables.computeIfAbsent(orderId, key -> new ArrayList<>());
        DeliverableView deliverable = new DeliverableView(
            deliverableSeq.getAndIncrement(),
            orderId,
            versions.size() + 1,
            deliveryNote,
            payload == null ? Map.of() : Map.copyOf(payload),
            submittedBy,
            Instant.now()
        );
        versions.add(deliverable);

        OrderView updated = new OrderView(
            order.id(),
            order.orderNo(),
            order.requesterOpenClawId(),
            order.executorOpenClawId(),
            order.taskTemplateId(),
            order.capabilityPackageId(),
            order.title(),
            V1OrderStatus.DELIVERED.name().toLowerCase(),
            order.quotedPrice(),
            order.currency(),
            order.slaHours(),
            order.requirementPayload(),
            order.acceptedAt(),
            Instant.now(),
            order.completedAt(),
            order.cancelledAt(),
            order.createdAt(),
            Instant.now()
        );
        orders.put(orderId, updated);
        persistOrderSnapshot(updated);
        persistResultEvent(orderId, submittedBy, "result_delivered", payload);
        return deliverable;
    }

    public OrderView notifyResultReady(long orderId, long executorOpenClawId, Map<String, Object> resultSummary) {
        OrderView order = requireOrder(orderId);
        if (order.executorOpenClawId() == null || order.executorOpenClawId() != executorOpenClawId) {
            throw new ApiException("ORDER_EXECUTOR_MISMATCH", HttpStatus.CONFLICT, "Order executor mismatch");
        }
        if (!"delivered".equals(order.status()) && !"in_progress".equals(order.status()) && !"accepted".equals(order.status())) {
            throw new ApiException("ORDER_INVALID_STATUS", HttpStatus.CONFLICT, "Order cannot notify result in current status");
        }

        OrderView updated = new OrderView(
            order.id(),
            order.orderNo(),
            order.requesterOpenClawId(),
            order.executorOpenClawId(),
            order.taskTemplateId(),
            order.capabilityPackageId(),
            order.title(),
            V1OrderStatus.RESULT_READY.name().toLowerCase(),
            order.quotedPrice(),
            order.currency(),
            order.slaHours(),
            order.requirementPayload(),
            order.acceptedAt(),
            order.deliveredAt(),
            order.completedAt(),
            order.cancelledAt(),
            order.createdAt(),
            Instant.now()
        );
        orders.put(orderId, updated);
        persistOrderSnapshot(updated);
        persistResultEvent(orderId, executorOpenClawId, "result_ready_notified", resultSummary);
        return updated;
    }

    public OrderView receiveResult(long orderId, long requesterOpenClawId, Map<String, Object> checklistResult, String note) {
        return approveAcceptance(orderId, requesterOpenClawId, checklistResult, note);
    }

    public OrderView approveAcceptance(long orderId, long requesterOpenClawId, Map<String, Object> checklistResult, String comment) {
        OrderView order = requireOrder(orderId);
        if (!"delivered".equals(order.status()) && !"result_ready".equals(order.status())) {
            throw new ApiException("ORDER_INVALID_STATUS", HttpStatus.CONFLICT, "Order cannot be approved in current status");
        }
        if (order.requesterOpenClawId() != requesterOpenClawId) {
            throw new ApiException("ORDER_REQUESTER_MISMATCH", HttpStatus.CONFLICT, "Only requester OpenClaw can approve result");
        }

        if (checklistResult == null || checklistResult.isEmpty()) {
            throw new ApiException("CHECKLIST_REQUIRED", HttpStatus.BAD_REQUEST, "checklistResult is required");
        }

        OrderView updated = new OrderView(
            order.id(),
            order.orderNo(),
            order.requesterOpenClawId(),
            order.executorOpenClawId(),
            order.taskTemplateId(),
            order.capabilityPackageId(),
            order.title(),
            V1OrderStatus.APPROVED.name().toLowerCase(),
            order.quotedPrice(),
            order.currency(),
            order.slaHours(),
            order.requirementPayload(),
            order.acceptedAt(),
            order.deliveredAt(),
            Instant.now(),
            order.cancelledAt(),
            order.createdAt(),
            Instant.now()
        );
        orders.put(orderId, updated);
        persistOrderSnapshot(updated);
        persistResultEvent(orderId, requesterOpenClawId, "result_received", Map.of(
            "checklist", checklistResult,
            "note", comment == null ? "" : comment
        ));
        return updated;
    }

    public DisputeView createDispute(long orderId, long openedByOpenClawId, String reasonCode, String description) {
        OrderView order = requireOrder(orderId);
        if ("settled".equals(order.status()) || "refunded".equals(order.status()) || "cancelled".equals(order.status())) {
            throw new ApiException("ORDER_INVALID_STATUS", HttpStatus.CONFLICT, "Order cannot be disputed in current status");
        }

        DisputeView dispute = new DisputeView(disputeSeq.getAndIncrement(), orderId, openedByOpenClawId, reasonCode, description, "open", Instant.now());
        disputes.computeIfAbsent(orderId, key -> new ArrayList<>()).add(dispute);

        OrderView updated = new OrderView(
            order.id(),
            order.orderNo(),
            order.requesterOpenClawId(),
            order.executorOpenClawId(),
            order.taskTemplateId(),
            order.capabilityPackageId(),
            order.title(),
            V1OrderStatus.DISPUTED.name().toLowerCase(),
            order.quotedPrice(),
            order.currency(),
            order.slaHours(),
            order.requirementPayload(),
            order.acceptedAt(),
            order.deliveredAt(),
            order.completedAt(),
            order.cancelledAt(),
            order.createdAt(),
            Instant.now()
        );
        orders.put(orderId, updated);
        persistOrderSnapshot(updated);
        persistResultEvent(orderId, openedByOpenClawId, "order_disputed", Map.of("reason_code", reasonCode, "description", description));

        return dispute;
    }

    private OrderView requireOrder(long orderId) {
        OrderView order = orders.get(orderId);
        if (order == null) {
            throw new ApiException("ORDER_NOT_FOUND", HttpStatus.NOT_FOUND, "Order not found");
        }
        return order;
    }

    private <T> List<T> pageAndSort(List<T> source, int page, int size, String sort, Comparator<T> defaultComparator) {
        List<T> sorted = new ArrayList<>(source);
        sorted.sort(defaultComparator);
        if (sort != null && sort.toLowerCase().endsWith(",desc")) {
            sorted.sort(defaultComparator.reversed());
        }

        int start = Math.max(page, 0) * Math.max(size, 1);
        if (start >= sorted.size()) {
            return List.of();
        }
        int end = Math.min(start + Math.max(size, 1), sorted.size());
        return sorted.subList(start, end);
    }

    private void seedTemplates() {
        createTemplate("research_brief_basic", "Research Brief", "research_brief", "Structured market and product research brief", new BigDecimal("1.00"), 48);
        createTemplate("content_draft_standard", "Content Draft", "content_draft", "Draft SEO/article/content assets", new BigDecimal("2.00"), 24);
        createTemplate("code_fix_small_automation_basic", "Code Fix Small Automation", "code_fix_small_automation", "Small fix, script, or automation", new BigDecimal("3.00"), 48);
        createTemplate("data_cleanup_analysis_basic", "Data Cleanup Analysis", "data_cleanup_analysis", "Data cleaning and structured analysis", new BigDecimal("4.00"), 36);
        createTemplate("workflow_setup_basic", "Workflow Setup", "workflow_setup", "Set up reusable workflow with docs", new BigDecimal("5.00"), 72);
    }

    private void createTemplate(String code, String name, String taskType, String description, BigDecimal basePrice, int slaHours) {
        if (!FIXED_TASK_TYPES.contains(taskType)) {
            throw new IllegalStateException("Unsupported task type: " + taskType);
        }
        long id = templateSeq.getAndIncrement();
        TaskTemplateView view = new TaskTemplateView(
            id,
            code,
            name,
            taskType,
            description,
            Map.of("fields", List.of()),
            Map.of("format", "json"),
            Map.of("checklist", List.of()),
            "fixed",
            basePrice,
            slaHours,
            "active"
        );
        templates.put(id, view);
    }

    private void seedOpenClaws() {
        registerSeedOpenClaw(2001, "OpenClaw-Chen", "subscribed", "available");
        registerSeedOpenClaw(2002, "OpenClaw-Dana", "subscribed", "available");
        registerSeedOpenClaw(4001, "OpenClaw-Agent-Runtime", "subscribed", "available");
    }

    private void registerSeedOpenClaw(long id, String name, String subscriptionStatus, String serviceStatus) {
        Instant now = Instant.now();
        openClawSeq.set(Math.max(openClawSeq.get(), id + 1));
        OpenClawView runtime = new OpenClawView(id, name, subscriptionStatus, serviceStatus, null, now);
        OpenClawProfileView profile = new OpenClawProfileView(id, name, 10, Map.of(), subscriptionStatus, serviceStatus, now);
        openClaws.put(id, runtime);
        openClawProfiles.put(id, profile);
        persistOpenClawRuntime(runtime);
        persistOpenClawProfile(profile);
    }

    private OpenClawView requireOpenClaw(long openClawId) {
        OpenClawView openClaw = openClaws.get(openClawId);
        if (openClaw == null) {
            throw new ApiException("OPENCLAW_NOT_FOUND", HttpStatus.NOT_FOUND, "OpenClaw not found");
        }
        return openClaw;
    }

    private String normalizeOpenClawSubscriptionStatus(String subscriptionStatus) {
        String normalized = subscriptionStatus == null ? "" : subscriptionStatus.trim().toLowerCase();
        if (!OPENCLAW_SUBSCRIPTION_STATUSES.contains(normalized)) {
            throw new ApiException("OPENCLAW_SUBSCRIPTION_STATUS_INVALID", HttpStatus.BAD_REQUEST, "Unsupported subscription status");
        }
        return normalized;
    }

    private String normalizeOpenClawServiceStatus(String serviceStatus) {
        String normalized = serviceStatus == null ? "" : serviceStatus.trim().toLowerCase();
        if (!OPENCLAW_SERVICE_STATUSES.contains(normalized)) {
            throw new ApiException("OPENCLAW_SERVICE_STATUS_INVALID", HttpStatus.BAD_REQUEST, "Unsupported service status");
        }
        return normalized;
    }

    private BigDecimal resolveHireFeeByTaskType(String taskType) {
        BigDecimal fee = TASK_HIRE_FEES.get(taskType);
        if (fee == null) {
            throw new ApiException("TASK_TYPE_UNSUPPORTED", HttpStatus.BAD_REQUEST, "Unsupported task type: " + taskType);
        }
        return fee;
    }

    private void ensurePersistenceTables() {
                executeSql("""
                        CREATE TABLE IF NOT EXISTS openclaws (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            subscription_status TEXT NOT NULL,
                            service_status TEXT NOT NULL,
                            active_order_id INTEGER,
                            token_rate_per_100 NUMERIC NOT NULL DEFAULT 1.00,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                        """);

        executeSql("""
            CREATE TABLE IF NOT EXISTS openclaw_profiles (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              capacity_per_week INTEGER NOT NULL,
              service_config TEXT NOT NULL,
              subscription_status TEXT NOT NULL,
              service_status TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """);

        executeSql("""
            CREATE TABLE IF NOT EXISTS openclaw_task_orders (
              id INTEGER PRIMARY KEY,
              order_no TEXT NOT NULL,
              requester_openclaw_id INTEGER NOT NULL,
              executor_openclaw_id INTEGER,
              task_template_id INTEGER NOT NULL,
              capability_package_id INTEGER,
              title TEXT NOT NULL,
              status TEXT NOT NULL,
              quoted_price NUMERIC NOT NULL,
              currency TEXT NOT NULL,
              sla_hours INTEGER NOT NULL,
              requirement_payload TEXT NOT NULL,
              accepted_at TEXT,
              delivered_at TEXT,
              completed_at TEXT,
              cancelled_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """);

        executeSql("""
            CREATE TABLE IF NOT EXISTS openclaw_task_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              order_id INTEGER NOT NULL,
              actor_openclaw_id INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              event_payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """);
    }

    private void persistOpenClawRuntime(OpenClawView runtime) {
        executeUpdate(
            """
            INSERT INTO openclaws (id, name, subscription_status, service_status, active_order_id, token_rate_per_100, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1.00, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name = excluded.name,
              subscription_status = excluded.subscription_status,
              service_status = excluded.service_status,
              active_order_id = excluded.active_order_id,
              updated_at = excluded.updated_at
            """,
            ps -> {
                ps.setLong(1, runtime.id());
                ps.setString(2, runtime.name());
                ps.setString(3, runtime.subscriptionStatus());
                ps.setString(4, runtime.serviceStatus());
                if (runtime.activeOrderId() == null) {
                    ps.setNull(5, java.sql.Types.INTEGER);
                } else {
                    ps.setLong(5, runtime.activeOrderId());
                }
                ps.setString(6, runtime.updatedAt().toString());
                ps.setString(7, runtime.updatedAt().toString());
            }
        );
    }

    private void persistOpenClawProfile(OpenClawProfileView profile) {
        executeUpdate(
            """
            INSERT INTO openclaw_profiles (id, name, capacity_per_week, service_config, subscription_status, service_status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name = excluded.name,
              capacity_per_week = excluded.capacity_per_week,
              service_config = excluded.service_config,
              subscription_status = excluded.subscription_status,
              service_status = excluded.service_status,
              updated_at = excluded.updated_at
            """,
            ps -> {
                ps.setLong(1, profile.id());
                ps.setString(2, profile.name());
                ps.setInt(3, profile.capacityPerWeek());
                ps.setString(4, toJson(profile.serviceConfig()));
                ps.setString(5, profile.subscriptionStatus());
                ps.setString(6, profile.serviceStatus());
                ps.setString(7, profile.updatedAt().toString());
            }
        );
    }

    private void persistOrderSnapshot(OrderView order) {
        executeUpdate(
            """
            INSERT INTO openclaw_task_orders (
              id, order_no, requester_openclaw_id, executor_openclaw_id, task_template_id, capability_package_id,
              title, status, quoted_price, currency, sla_hours, requirement_payload,
              accepted_at, delivered_at, completed_at, cancelled_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              requester_openclaw_id = excluded.requester_openclaw_id,
              executor_openclaw_id = excluded.executor_openclaw_id,
              task_template_id = excluded.task_template_id,
              capability_package_id = excluded.capability_package_id,
              title = excluded.title,
              status = excluded.status,
              quoted_price = excluded.quoted_price,
              currency = excluded.currency,
              sla_hours = excluded.sla_hours,
              requirement_payload = excluded.requirement_payload,
              accepted_at = excluded.accepted_at,
              delivered_at = excluded.delivered_at,
              completed_at = excluded.completed_at,
              cancelled_at = excluded.cancelled_at,
              updated_at = excluded.updated_at
            """,
            ps -> {
                ps.setLong(1, order.id());
                ps.setString(2, order.orderNo());
                ps.setLong(3, order.requesterOpenClawId());
                if (order.executorOpenClawId() == null) {
                    ps.setNull(4, java.sql.Types.INTEGER);
                } else {
                    ps.setLong(4, order.executorOpenClawId());
                }
                ps.setLong(5, order.taskTemplateId());
                if (order.capabilityPackageId() == null) {
                    ps.setNull(6, java.sql.Types.INTEGER);
                } else {
                    ps.setLong(6, order.capabilityPackageId());
                }
                ps.setString(7, order.title());
                ps.setString(8, order.status());
                ps.setBigDecimal(9, order.quotedPrice());
                ps.setString(10, order.currency());
                ps.setInt(11, order.slaHours());
                ps.setString(12, toJson(order.requirementPayload()));
                ps.setString(13, nullableInstant(order.acceptedAt()));
                ps.setString(14, nullableInstant(order.deliveredAt()));
                ps.setString(15, nullableInstant(order.completedAt()));
                ps.setString(16, nullableInstant(order.cancelledAt()));
                ps.setString(17, order.createdAt().toString());
                ps.setString(18, order.updatedAt().toString());
            }
        );
    }

    private void persistResultEvent(long orderId, long actorOpenClawId, String eventType, Map<String, Object> payload) {
        executeUpdate(
            "INSERT INTO openclaw_task_events (order_id, actor_openclaw_id, event_type, event_payload, created_at) VALUES (?, ?, ?, ?, ?)",
            ps -> {
                ps.setLong(1, orderId);
                ps.setLong(2, actorOpenClawId);
                ps.setString(3, eventType);
                ps.setString(4, toJson(payload == null ? Map.of() : payload));
                ps.setString(5, Instant.now().toString());
            }
        );
    }

    private void executeSql(String sql) {
        try (Connection connection = DriverManager.getConnection(SQLITE_URL); PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new ApiException("PERSISTENCE_ERROR", HttpStatus.INTERNAL_SERVER_ERROR, "Failed to initialize persistence tables");
        }
    }

    private void executeUpdate(String sql, SqlConsumer statementBinder) {
        try (Connection connection = DriverManager.getConnection(SQLITE_URL); PreparedStatement statement = connection.prepareStatement(sql)) {
            statementBinder.accept(statement);
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new ApiException("PERSISTENCE_ERROR", HttpStatus.INTERNAL_SERVER_ERROR, "Persistence write failed");
        }
    }

    private String nullableInstant(Instant instant) {
        return instant == null ? null : instant.toString();
    }

    private String toJson(Map<String, Object> payload) {
        try {
            return objectMapper.writeValueAsString(payload == null ? Map.of() : payload);
        } catch (JsonProcessingException ex) {
            throw new ApiException("JSON_SERIALIZE_FAILED", HttpStatus.INTERNAL_SERVER_ERROR, "Failed to serialize payload");
        }
    }

    @FunctionalInterface
    private interface SqlConsumer {
        void accept(PreparedStatement statement) throws SQLException;
    }

    private List<String> normalizeRoles(List<String> roles) {
        List<String> source = (roles == null || roles.isEmpty()) ? List.of("openclaw") : roles;
        List<String> normalized = new ArrayList<>();
        for (String role : source) {
            String value = role.toLowerCase();
            if (!ALLOWED_ROLES.contains(value)) {
                throw new ApiException("AUTH_ROLE_INVALID", HttpStatus.BAD_REQUEST, "Unsupported role: " + role);
            }
            if (!normalized.contains(value)) {
                normalized.add(value);
            }
        }
        return normalized;
    }

    private String generateToken(UserView user) {
        String raw = user.id() + ":" + user.email() + ":" + Instant.now().toString();
        return Base64.getUrlEncoder().withoutPadding().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    private String hash(String plain) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(plain.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : bytes) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }
}
