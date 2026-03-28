import { FastifyInstance } from "fastify";
import { templates } from "../data";

export async function registerTemplateRoutes(app: FastifyInstance) {
  app.get("/templates", async () => ({
    data: templates
  }));

  app.get("/templates/:id", async (request, reply) => {
    const { id } = request.params as { id: string };
    const template = templates.find((tpl) => tpl.id === id);
    if (!template) {
      return reply.code(404).send({ error: { code: "NOT_FOUND", message: "Template not found" } });
    }
    return { data: template };
  });
}
