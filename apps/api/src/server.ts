import Fastify from "fastify";
import cors from "@fastify/cors";
import swagger from "@fastify/swagger";
import swaggerUI from "@fastify/swagger-ui";
import { registerTemplateRoutes } from "./routes/templates";
import { registerOrderRoutes } from "./routes/orders";
import { registerOwnerRoutes } from "./routes/owners";
import { registerZeaburRoutes } from "./routes/zeabur";

const port = Number(process.env.PORT ?? 4000);

async function bootstrap() {
  const app = Fastify({ logger: true });

  await app.register(cors, { origin: "*" });
  await app.register(swagger, {
    openapi: {
      info: {
        title: "OpenClaw Agent Marketplace API",
        version: "0.1.0"
      }
    }
  });
  await app.register(swaggerUI, {
    routePrefix: "/docs",
    uiConfig: {
      docExpansion: "list"
    }
  });

  await app.register(async (instance) => {
    await registerTemplateRoutes(instance);
    await registerOrderRoutes(instance);
    await registerOwnerRoutes(instance);
    await registerZeaburRoutes(instance);
  });

  try {
    await app.listen({ port, host: "0.0.0.0" });
    app.log.info(`API ready on http://localhost:${port}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

bootstrap();
