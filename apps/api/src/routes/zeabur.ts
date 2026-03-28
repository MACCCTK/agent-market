import { FastifyInstance } from "fastify";
import { randomUUID } from "node:crypto";
import { zeaburSkills } from "../data";

export async function registerZeaburRoutes(app: FastifyInstance) {
  app.get("/zeabur/skills", async () => ({ data: zeaburSkills }));

  app.post("/zeabur/run", async (request) => {
    const body = request.body as { skillId: string; payload: Record<string, unknown> };
    return {
      data: {
        runId: `run_${body.skillId}_${randomUUID().slice(0, 8)}`,
        status: "queued",
        receivedAt: new Date().toISOString(),
        payloadEcho: body.payload
      }
    };
  });
}
