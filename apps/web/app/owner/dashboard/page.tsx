import Link from "next/link";
import { api } from "../../../lib/api";

export default async function OwnerDashboard() {
  const [ownersRes, packagesRes, ordersRes, skillsRes] = await Promise.all([
    api.listOwners(),
    api.listPackages(),
    api.listOrders(),
    api.listSkills()
  ]);
  const owner = ownersRes.data[0];
  const packages = packagesRes.data.filter((pkg) => owner.capabilityPackages.includes(pkg.id));
  const orders = ordersRes.data;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Owner</p>
        <h2 className="mt-2 text-3xl font-semibold text-slate-900">{owner.displayName}</h2>
        <p className="mt-3 text-slate-600">{owner.bio}</p>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-500">
          <span>Timezone: {owner.timezone}</span>
          <span>Skill IDs: {owner.skillIds?.join(", ") ?? "—"}</span>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Capability Packages</h3>
          <ul className="mt-4 space-y-3">
            {packages.map((pkg) => (
              <li key={pkg.id} className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
                <p className="text-lg font-semibold text-slate-900">{pkg.title}</p>
                <p className="text-sm text-slate-600">{pkg.description}</p>
                <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-500">
                  <span>Capacity: {pkg.capacity}</span>
                  <span>
                    Price {pkg.priceRange.currency} {pkg.priceRange.min}–{pkg.priceRange.max}
                  </span>
                  <span>Templates: {pkg.supportedTemplateIds.join(", ")}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Zeabur Skills</h3>
          <ul className="mt-4 space-y-3">
            {skillsRes.data.map((skill) => (
              <li key={skill.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.3em] text-slate-500">{skill.id}</p>
                    <p className="text-lg font-semibold text-slate-900">{skill.name}</p>
                    <p className="text-sm text-slate-600">{skill.description}</p>
                  </div>
                  <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">
                    v{skill.version}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-slate-900">Live Orders</h3>
          <p className="text-sm text-slate-500">{orders.length} total</p>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Order ID</th>
                <th className="px-4 py-2 font-medium">Template</th>
                <th className="px-4 py-2 font-medium">State</th>
                <th className="px-4 py-2 font-medium">Escrow</th>
                <th className="px-4 py-2 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className="border-t border-slate-100">
                  <td className="px-4 py-3 text-brand-500">
                    <Link href={`/orders/${order.id}`}>{order.id}</Link>
                  </td>
                  <td className="px-4 py-3">{order.templateId}</td>
                  <td className="px-4 py-3 capitalize">{order.state.replace("_", " ")}</td>
                  <td className="px-4 py-3">
                    {order.currency} {order.escrowAmount}
                  </td>
                  <td className="px-4 py-3">{new Date(order.updatedAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
