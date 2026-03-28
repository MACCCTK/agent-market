package com.example.demo;

import com.example.demo.marketplace.v1.service.V1MarketplaceService;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

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
