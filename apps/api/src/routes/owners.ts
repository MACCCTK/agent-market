import { FastifyInstance } from "fastify";
import { capabilityPackages, owners } from "../data";

export async function registerOwnerRoutes(app: FastifyInstance) {
  app.get("/owners", async () => ({ data: owners }));

  app.get("/owners/:id", async (request, reply) => {
    const { id } = request.params as { id: string };
    const owner = owners.find((item) => item.id === id);
    if (!owner) {
      return reply.code(404).send({ error: { code: "NOT_FOUND", message: "Owner not found" } });
    }
    const packages = capabilityPackages.filter((pkg) => pkg.ownerId === id);
    return { data: { ...owner, packages } };
  });

  app.get("/capability-packages", async () => ({ data: capabilityPackages }));
}
