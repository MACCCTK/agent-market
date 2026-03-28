import { FastifyInstance } from "fastify";
import { deliverables, orders } from "../data";
import { OrderService } from "../services/orderService";
import { OrderState } from "../types";

export async function registerOrderRoutes(app: FastifyInstance) {
  app.get("/orders", async () => ({ data: orders }));

  app.get("/orders/:id", async (request, reply) => {
    const { id } = request.params as { id: string };
    const order = OrderService.get(id);
    if (!order) {
      return reply.code(404).send({ error: { code: "NOT_FOUND", message: "Order not found" } });
    }
    const orderDeliverables = deliverables.filter((item) => item.orderId === id);
    return { data: { ...order, deliverables: orderDeliverables } };
  });

  app.post("/orders", async (request) => {
    const body = request.body as {
      templateId: string;
      packageId: string;
      buyerId?: string;
      inputs: Record<string, unknown>;
      currency?: string;
      escrowAmount?: number;
    };
    const order = OrderService.create({
      templateId: body.templateId,
      packageId: body.packageId,
      buyerId: body.buyerId ?? "buyer_demo",
      inputs: body.inputs,
      currency: body.currency,
      escrowAmount: body.escrowAmount
    });
    return { data: order };
  });

  app.post("/orders/:id/transition", async (request, reply) => {
    const { id } = request.params as { id: string };
    const body = request.body as { nextState: OrderState };
    try {
      const order = OrderService.transition(id, body.nextState);
      return { data: order };
    } catch (error) {
      return reply.code(400).send({ error: { code: "INVALID_TRANSITION", message: (error as Error).message } });
    }
  });
}
