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
	void ordersEndpointSupportsListAndCreate() throws Exception {
		MvcResult createResult = mockMvc.perform(post("/api/v1/orders")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"requester_openclaw_id":4001,"task_template_id":1,"title":"HTTP order","requirement_payload":{"brief":"market scan"}}
					"""))
			.andReturn();

		assertEquals(200, createResult.getResponse().getStatus(), createResult.getResponse().getContentAsString());
		org.junit.jupiter.api.Assertions.assertTrue(createResult.getResponse().getContentAsString().contains("\"requester_openclaw_id\":4001"));
		org.junit.jupiter.api.Assertions.assertTrue(createResult.getResponse().getContentAsString().contains("\"task_template_id\":1"));
		org.junit.jupiter.api.Assertions.assertTrue(createResult.getResponse().getContentAsString().contains("\"status\":\"created\""));

		mockMvc.perform(get("/api/v1/orders"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$").isArray());
	}

	@Test
	void assignedOrderAppearsInOrdersAndOpenClawRuntime() throws Exception {
		String created = mockMvc.perform(post("/api/v1/orders")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"requester_openclaw_id":4001,"task_template_id":1,"title":"Assigned HTTP order","requirement_payload":{"brief":"assignment state"}}
					"""))
			.andReturn()
			.getResponse()
			.getContentAsString();

		String orderId = created.replaceAll(".*\"id\":(\\d+).*", "$1");

		mockMvc.perform(post("/api/v1/orders/" + orderId + "/assign")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{"executor_openclaw_id":2002}
					"""))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.executor_openclaw_id").value(2002));

		mockMvc.perform(get("/api/v1/orders"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[?(@.id==" + orderId + ")].executor_openclaw_id").value(org.hamcrest.Matchers.hasItem(2002)))
			.andExpect(jsonPath("$[?(@.id==" + orderId + ")].executor_open_claw_id").value(org.hamcrest.Matchers.hasItem(2002)));

		mockMvc.perform(get("/api/v1/openclaws"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[?(@.id==2002)].active_order_id").value(org.hamcrest.Matchers.hasItem(Integer.parseInt(orderId))));
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
	void assignOrderAutoPicksAvailableExecutor() {
		V1MarketplaceService service = new V1MarketplaceService();

		V1MarketplaceService.OrderView order = service.createOrder(
			4001,
			1,
			null,
			"Need research",
			Map.of("brief", "market scan")
		);

		V1MarketplaceService.OrderView assigned = service.assignOrder(order.id(), null);

		assertNotNull(assigned.executorOpenClawId());
		org.junit.jupiter.api.Assertions.assertEquals("accepted", assigned.status());
		org.junit.jupiter.api.Assertions.assertEquals(2001L, assigned.executorOpenClawId());
	}

	@Test
	void assignOrderToSpecificExecutor() {
		V1MarketplaceService service = new V1MarketplaceService();

		V1MarketplaceService.OrderView order = service.createOrder(
			4001,
			2,
			null,
			"Need draft",
			Map.of("topic", "landing page")
		);

		V1MarketplaceService.OrderView assigned = service.assignOrder(order.id(), 2002L);

		org.junit.jupiter.api.Assertions.assertEquals(2002L, assigned.executorOpenClawId());
		org.junit.jupiter.api.Assertions.assertEquals("accepted", assigned.status());
	}

	@Test
	void assignOrderCreatesTrackableNotification() {
		V1MarketplaceService service = new V1MarketplaceService();

		V1MarketplaceService.OrderView order = service.createOrder(
			4001,
			2,
			null,
			"Notify executor",
			Map.of("topic", "send notification")
		);
		service.assignOrder(order.id(), 2002L);

		java.util.List<V1MarketplaceService.NotificationView> notifications = service.listNotifications(2002L);

		org.junit.jupiter.api.Assertions.assertFalse(notifications.isEmpty());
		org.junit.jupiter.api.Assertions.assertEquals("task_assigned", notifications.get(0).notificationType());
		org.junit.jupiter.api.Assertions.assertEquals(order.id(), notifications.get(0).orderId());
	}

	@Test
	void assignmentNotificationCanBeAcknowledged() {
		V1MarketplaceService service = new V1MarketplaceService();

		V1MarketplaceService.OrderView order = service.createOrder(
			4001,
			1,
			null,
			"Ack notification",
			Map.of("brief", "ack flow")
		);
		service.assignOrder(order.id(), 2002L);
		V1MarketplaceService.NotificationView notification = service.listNotifications(2002L).get(0);

		V1MarketplaceService.NotificationView acked = service.acknowledgeNotification(2002L, notification.id());

		org.junit.jupiter.api.Assertions.assertEquals("acked", acked.status());
		org.junit.jupiter.api.Assertions.assertNotNull(acked.ackedAt());
	}

	@Test
	void heartbeatAssignsPendingOrderToIdleOpenClaw() {
		V1MarketplaceService service = new V1MarketplaceService();

		V1MarketplaceService.OrderView order = service.createOrder(
			4001,
			1,
			null,
			"Heartbeat assignment",
			Map.of("brief", "assign on heartbeat")
		);

		V1MarketplaceService.HeartbeatView heartbeat = service.heartbeatOpenClaw(2002L, "available");

		org.junit.jupiter.api.Assertions.assertNotNull(heartbeat.assignedOrder());
		org.junit.jupiter.api.Assertions.assertEquals(order.id(), heartbeat.assignedOrder().id());
		org.junit.jupiter.api.Assertions.assertEquals(2002L, heartbeat.assignedOrder().executorOpenClawId());
		org.junit.jupiter.api.Assertions.assertEquals("accepted", heartbeat.assignedOrder().status());
	}

	@Test
	void completeOrderCallbackPromotesOrderToResultReady() {
		V1MarketplaceService service = new V1MarketplaceService();

		V1MarketplaceService.OrderView order = service.createOrder(
			4001,
			1,
			null,
			"Callback completion",
			Map.of("brief", "finish work")
		);
		V1MarketplaceService.OrderView assigned = service.assignOrder(order.id(), 2002L);

		V1MarketplaceService.OrderView completed = service.completeOrderByOpenClaw(
			assigned.id(),
			2002L,
			"Final delivery",
			Map.of("artifact", "done"),
			Map.of("summary", "completed")
		);

		org.junit.jupiter.api.Assertions.assertEquals("result_ready", completed.status());
		org.junit.jupiter.api.Assertions.assertEquals(2002L, completed.executorOpenClawId());
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

}
