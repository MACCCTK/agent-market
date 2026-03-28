package com.example.demo;

import com.example.demo.marketplace.v1.service.V1MarketplaceService;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
class DemoApplicationTests {

	private static final long REQUESTER_ID = 4001L;
	private static final long EXECUTOR_ONE_ID = 2001L;
	private static final long EXECUTOR_TWO_ID = 2002L;

	@Autowired
	private WebApplicationContext webApplicationContext;

	private MockMvc mockMvc;

	@BeforeEach
	void setUpMockMvc() {
		mockMvc = MockMvcBuilders.webAppContextSetup(webApplicationContext).build();
	}

	@Test
	void contextLoads() {
	}

	@Test
	void rootRedirectsToSwaggerUi() throws Exception {
		mockMvc.perform(get("/"))
			.andExpect(status().isFound())
			.andExpect(header().string("Location", "/swagger-ui.html"));
	}

	@Test
	void legacyApiSurfaceIsRemoved() throws Exception {
		mockMvc.perform(get("/api/health"))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("NOT_FOUND"));
	}

	@Test
	void v1TaskTemplatesEndpointRemainsAvailable() throws Exception {
		mockMvc.perform(get("/api/v1/task-templates?page=0&size=5&sort=id,asc"))
			.andExpect(status().isOk());
	}

	@Test
	void newServiceStartsWithoutSeedOpenClaws() {
		V1MarketplaceService service = new V1MarketplaceService();

		org.junit.jupiter.api.Assertions.assertTrue(service.listOpenClaws().isEmpty());
	}

	@Test
	void ordersEndpointSupportsListAndCreate() throws Exception {
		registerDefaultOpenClawsViaHttp();

		MvcResult createResult = mockMvc.perform(post("/api/v1/orders")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"requester_openclaw_id":4001,"task_template_id":1,"title":"HTTP order","requirement_payload":{"brief":"market scan"}}
					"""))
			.andReturn();

		assertEquals(200, createResult.getResponse().getStatus(), createResult.getResponse().getContentAsString());
		org.junit.jupiter.api.Assertions.assertTrue(createResult.getResponse().getContentAsString().contains("\"requester_openclaw_id\":4001"));
		org.junit.jupiter.api.Assertions.assertTrue(createResult.getResponse().getContentAsString().contains("\"task_template_id\":1"));
		org.junit.jupiter.api.Assertions.assertTrue(createResult.getResponse().getContentAsString().contains("\"status\":\"accepted\""));
		org.junit.jupiter.api.Assertions.assertTrue(createResult.getResponse().getContentAsString().contains("\"executor_openclaw_id\":"));

		mockMvc.perform(get("/api/v1/orders"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$").isArray());
	}

	@Test
	void assignedOrderAppearsInOrdersAndOpenClawRuntime() throws Exception {
		registerDefaultOpenClawsViaHttp();

		String created = mockMvc.perform(post("/api/v1/orders")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"requester_openclaw_id":4001,"task_template_id":1,"title":"Assigned HTTP order","requirement_payload":{"brief":"assignment state"}}
					"""))
			.andReturn()
			.getResponse()
			.getContentAsString();

		String orderId = created.replaceAll(".*\"id\":(\\d+).*", "$1");
		String executorId = created.replaceAll(".*\"executor_openclaw_id\":(\\d+).*", "$1");

		mockMvc.perform(get("/api/v1/orders"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[?(@.id==" + orderId + ")].status").value(org.hamcrest.Matchers.hasItem("accepted")))
			.andExpect(jsonPath("$[?(@.id==" + orderId + ")].executor_openclaw_id").value(org.hamcrest.Matchers.hasItem(Integer.parseInt(executorId))))
			.andExpect(jsonPath("$[?(@.id==" + orderId + ")].executor_open_claw_id").value(org.hamcrest.Matchers.hasItem(Integer.parseInt(executorId))));

		mockMvc.perform(get("/api/v1/openclaws"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[?(@.id==" + executorId + ")].active_order_id").value(org.hamcrest.Matchers.hasItem(Integer.parseInt(orderId))));
	}

	@Test
	void registerOpenClawServiceCallSucceeds() {
		V1MarketplaceService service = new V1MarketplaceService();

		V1MarketplaceService.OpenClawProfileView profile = service.registerOpenClaw(
			null,
			"Unit Test OpenClaw",
			3,
			Map.of("mode", "auto"),
			"subscribed",
			"available"
		);

		assertNotNull(profile);
	}

	@Test
	void createOrderAutoAssignsAvailableExecutor() {
		V1MarketplaceService service = new V1MarketplaceService();
		registerDefaultOpenClaws(service);

		V1MarketplaceService.OrderView assigned = service.createOrder(
			REQUESTER_ID,
			1,
			null,
			"Need research",
			Map.of("brief", "market scan")
		);

		assertNotNull(assigned.executorOpenClawId());
		org.junit.jupiter.api.Assertions.assertEquals("accepted", assigned.status());
		org.junit.jupiter.api.Assertions.assertEquals(EXECUTOR_ONE_ID, assigned.executorOpenClawId());
	}

	@Test
	void assignOrderToSpecificExecutor() {
		V1MarketplaceService service = new V1MarketplaceService();
		registerDefaultOpenClaws(service);
		service.heartbeatOpenClaw(EXECUTOR_ONE_ID, "busy");
		service.heartbeatOpenClaw(EXECUTOR_TWO_ID, "busy");

		V1MarketplaceService.OrderView order = service.createOrder(
			REQUESTER_ID,
			2,
			null,
			"Need draft",
			Map.of("topic", "landing page")
		);
		V1MarketplaceService.OpenClawProfileView executor = service.registerOpenClaw(
			null,
			"Specific Executor",
			2,
			Map.of("mode", "manual"),
			"subscribed",
			"available"
		);

		V1MarketplaceService.OrderView assigned = service.assignOrder(order.id(), executor.id());

		org.junit.jupiter.api.Assertions.assertEquals(executor.id(), assigned.executorOpenClawId());
		org.junit.jupiter.api.Assertions.assertEquals("accepted", assigned.status());
	}

	@Test
	void assignOrderCreatesTrackableNotification() {
		V1MarketplaceService service = new V1MarketplaceService();
		registerDefaultOpenClaws(service);
		service.heartbeatOpenClaw(EXECUTOR_ONE_ID, "busy");
		service.heartbeatOpenClaw(EXECUTOR_TWO_ID, "busy");

		V1MarketplaceService.OrderView order = service.createOrder(
			REQUESTER_ID,
			2,
			null,
			"Notify executor",
			Map.of("topic", "send notification")
		);
		V1MarketplaceService.OpenClawProfileView executor = service.registerOpenClaw(
			null,
			"Notification Executor",
			2,
			Map.of("mode", "manual"),
			"subscribed",
			"available"
		);
		service.assignOrder(order.id(), executor.id());

		java.util.List<V1MarketplaceService.NotificationView> notifications = service.listNotifications(executor.id());

		org.junit.jupiter.api.Assertions.assertFalse(notifications.isEmpty());
		org.junit.jupiter.api.Assertions.assertEquals("task_assigned", notifications.get(0).notificationType());
		org.junit.jupiter.api.Assertions.assertEquals(order.id(), notifications.get(0).orderId());
	}

	@Test
	void assignmentNotificationCanBeAcknowledged() {
		V1MarketplaceService service = new V1MarketplaceService();
		registerDefaultOpenClaws(service);
		service.heartbeatOpenClaw(EXECUTOR_ONE_ID, "busy");
		service.heartbeatOpenClaw(EXECUTOR_TWO_ID, "busy");

		V1MarketplaceService.OrderView order = service.createOrder(
			REQUESTER_ID,
			1,
			null,
			"Ack notification",
			Map.of("brief", "ack flow")
		);
		V1MarketplaceService.OpenClawProfileView executor = service.registerOpenClaw(
			null,
			"Ack Executor",
			2,
			Map.of("mode", "manual"),
			"subscribed",
			"available"
		);
		service.assignOrder(order.id(), executor.id());
		V1MarketplaceService.NotificationView notification = service.listNotifications(executor.id()).get(0);

		V1MarketplaceService.NotificationView acked = service.acknowledgeNotification(executor.id(), notification.id());

		org.junit.jupiter.api.Assertions.assertEquals("acked", acked.status());
		org.junit.jupiter.api.Assertions.assertNotNull(acked.ackedAt());
	}

	@Test
	void heartbeatAssignsPendingOrderToIdleOpenClaw() {
		V1MarketplaceService service = new V1MarketplaceService();
		registerDefaultOpenClaws(service);
		service.heartbeatOpenClaw(EXECUTOR_ONE_ID, "busy");
		service.heartbeatOpenClaw(EXECUTOR_TWO_ID, "busy");

		V1MarketplaceService.OrderView order = service.createOrder(
			REQUESTER_ID,
			1,
			null,
			"Heartbeat assignment",
			Map.of("brief", "assign on heartbeat")
		);

		V1MarketplaceService.HeartbeatView heartbeat = service.heartbeatOpenClaw(EXECUTOR_TWO_ID, "available");

		org.junit.jupiter.api.Assertions.assertNotNull(heartbeat.assignedOrder());
		org.junit.jupiter.api.Assertions.assertEquals(order.id(), heartbeat.assignedOrder().id());
		org.junit.jupiter.api.Assertions.assertEquals(EXECUTOR_TWO_ID, heartbeat.assignedOrder().executorOpenClawId());
		org.junit.jupiter.api.Assertions.assertEquals("accepted", heartbeat.assignedOrder().status());
	}

	@Test
	void createOrderKeepsCreatedWhenNoExecutorIsAvailable() {
		V1MarketplaceService service = new V1MarketplaceService();
		registerDefaultOpenClaws(service);
		service.heartbeatOpenClaw(EXECUTOR_ONE_ID, "busy");
		service.heartbeatOpenClaw(EXECUTOR_TWO_ID, "busy");

		V1MarketplaceService.OrderView order = service.createOrder(
			REQUESTER_ID,
			1,
			null,
			"No executor available",
			Map.of("brief", "wait for capacity")
		);

		org.junit.jupiter.api.Assertions.assertEquals("created", order.status());
		org.junit.jupiter.api.Assertions.assertNull(order.executorOpenClawId());
	}

	@Test
	void completeOrderCallbackPromotesOrderToResultReady() {
		V1MarketplaceService service = new V1MarketplaceService();
		registerDefaultOpenClaws(service);

		V1MarketplaceService.OrderView assigned = service.createOrder(
			REQUESTER_ID,
			1,
			null,
			"Callback completion",
			Map.of("brief", "finish work")
		);

		V1MarketplaceService.OrderView completed = service.completeOrderByOpenClaw(
			assigned.id(),
			assigned.executorOpenClawId(),
			"Final delivery",
			Map.of("artifact", "done"),
			Map.of("summary", "completed")
		);

		org.junit.jupiter.api.Assertions.assertEquals("result_ready", completed.status());
		org.junit.jupiter.api.Assertions.assertEquals(assigned.executorOpenClawId(), completed.executorOpenClawId());
	}

	@Test
	void registerOpenClawAcceptsSnakeCasePayload() throws Exception {
		mockMvc.perform(post("/api/v1/openclaws/register")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"name":"Snake OK","capacity_per_week":3,"service_config":{"mode":"auto"},"subscription_status":"subscribed","service_status":"available"}
					"""))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.capacity_per_week").value(3))
			.andExpect(jsonPath("$.service_config.mode").value("auto"))
			.andExpect(jsonPath("$.subscription_status").value("subscribed"))
			.andExpect(jsonPath("$.service_status").value("available"));
	}

	@Test
	void registerOpenClawRejectsCamelCasePayloadWithBadRequest() throws Exception {
		mockMvc.perform(post("/api/v1/openclaws/register")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"name":"Camel Fail","capacityPerWeek":3,"serviceConfig":{"mode":"auto"},"subscriptionStatus":"subscribed","serviceStatus":"available"}
					"""))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
	}

	@Test
	void apiDocsExposeSnakeCaseForRegisterOpenClawSchema() throws Exception {
		mockMvc.perform(get("/api-docs"))
			.andExpect(status().isOk())
			.andExpect(content().string(org.hamcrest.Matchers.containsString("\"RegisterOpenClawRequest\"")))
			.andExpect(content().string(org.hamcrest.Matchers.containsString("\"capacity_per_week\"")))
			.andExpect(content().string(org.hamcrest.Matchers.containsString("\"service_config\"")))
			.andExpect(content().string(org.hamcrest.Matchers.containsString("\"subscription_status\"")))
			.andExpect(content().string(org.hamcrest.Matchers.containsString("\"service_status\"")))
			.andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("\"capacityPerWeek\""))))
			.andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("\"serviceConfig\""))))
			.andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("\"subscriptionStatus\""))))
			.andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("\"serviceStatus\""))));
	}

	private void registerDefaultOpenClaws(V1MarketplaceService service) {
		service.registerOpenClaw(REQUESTER_ID, "Requester", 10, Map.of(), "subscribed", "available");
		service.registerOpenClaw(EXECUTOR_ONE_ID, "Executor One", 10, Map.of(), "subscribed", "available");
		service.registerOpenClaw(EXECUTOR_TWO_ID, "Executor Two", 10, Map.of(), "subscribed", "available");
	}

	private void registerDefaultOpenClawsViaHttp() throws Exception {
		registerOpenClawViaHttp(REQUESTER_ID, "Requester");
		registerOpenClawViaHttp(EXECUTOR_ONE_ID, "Executor One");
		registerOpenClawViaHttp(EXECUTOR_TWO_ID, "Executor Two");
	}

	private void registerOpenClawViaHttp(long id, String name) throws Exception {
		mockMvc.perform(post("/api/v1/openclaws/register")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"id":%d,"name":"%s","capacity_per_week":10,"service_config":{},"subscription_status":"subscribed","service_status":"available"}
					""".formatted(id, name)))
			.andExpect(status().isOk());
	}

}
