package com.example.demo;

import com.example.demo.marketplace.v1.service.V1MarketplaceService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class DemoApplicationTests {

	@LocalServerPort
	private int port;

	@Test
	void contextLoads() {
	}

	@Test
	void rootRedirectsToSwaggerUi() throws Exception {
		HttpURLConnection connection = openConnection("/");

		assertEquals(302, connection.getResponseCode());
		assertTrue(connection.getHeaderField("Location").endsWith("/swagger-ui.html"));
	}

	@Test
	void legacyApiSurfaceIsRemoved() throws Exception {
		HttpURLConnection connection = openConnection("/api/health");

		assertEquals(404, connection.getResponseCode());
	}

	@Test
	void v1TaskTemplatesEndpointRemainsAvailable() throws Exception {
		HttpURLConnection connection = openConnection("/api/v1/task-templates?page=0&size=5&sort=id,asc");

		assertEquals(200, connection.getResponseCode());
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
	void registerOpenClawAcceptsSnakeCasePayload() throws Exception {
		HttpURLConnection connection = openJsonConnection(
			"/api/v1/openclaws/register",
			"""
			{"name":"Snake OK","capacity_per_week":3,"service_config":{"mode":"auto"},"subscription_status":"subscribed","service_status":"available"}
			"""
		);

		assertEquals(200, connection.getResponseCode());
	}

	@Test
	void registerOpenClawRejectsCamelCasePayloadWithBadRequest() throws Exception {
		HttpURLConnection connection = openJsonConnection(
			"/api/v1/openclaws/register",
			"""
			{"name":"Camel Fail","capacityPerWeek":3,"serviceConfig":{"mode":"auto"},"subscriptionStatus":"subscribed","serviceStatus":"available"}
			"""
		);

		assertEquals(400, connection.getResponseCode());
	}

	private HttpURLConnection openConnection(String path) throws Exception {
		HttpURLConnection connection = (HttpURLConnection) new URL(
			"http://127.0.0.1:" + port + path
		).openConnection();
		connection.setInstanceFollowRedirects(false);
		connection.setRequestMethod("GET");
		connection.setRequestProperty("Accept-Charset", StandardCharsets.UTF_8.name());
		return connection;
	}

	private HttpURLConnection openJsonConnection(String path, String json) throws Exception {
		HttpURLConnection connection = openConnection(path);
		connection.setRequestMethod("POST");
		connection.setRequestProperty("Content-Type", "application/json");
		connection.setDoOutput(true);
		connection.getOutputStream().write(json.getBytes(StandardCharsets.UTF_8));
		return connection;
	}

}
