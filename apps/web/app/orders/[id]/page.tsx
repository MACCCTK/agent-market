import { api } from "../../../lib/api";

type OrderPageProps = { params: { id: string } };

const stateColors: Record<string, string> = {
  created: "bg-slate-200 text-slate-700",
  accepted: "bg-blue-100 text-blue-700",
  in_progress: "bg-amber-100 text-amber-800",
  delivered: "bg-emerald-100 text-emerald-800",
  rejected: "bg-rose-100 text-rose-700",
  accepted_final: "bg-indigo-100 text-indigo-800",
  settled: "bg-emerald-200 text-emerald-900",
  cancelled: "bg-slate-100 text-slate-500",
  disputed: "bg-rose-200 text-rose-800"
};

export default async function OrderPage({ params }: OrderPageProps) {
  const { data } = await api.getOrder(params.id);
  const badgeClass = stateColors[data.state] ?? "bg-slate-200 text-slate-700";

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Order</p>
          <h2 className="mt-2 text-3xl font-semibold text-slate-900">{data.id}</h2>
          <p className="mt-1 text-sm text-slate-500">Template: {data.templateId}</p>
        </div>
        <div className={`rounded-full px-4 py-2 text-sm font-semibold ${badgeClass}`}>{data.state}</div>
      </div>
      <div className="mt-6 grid gap-6 md:grid-cols-3">
        <div>
          <p className="text-sm text-slate-500">Escrow</p>
          <p className="text-xl font-semibold text-slate-900">
            {data.currency} {data.escrowAmount}
          </p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Package ID</p>
          <p className="text-xl font-semibold text-slate-900">{data.packageId}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Buyer</p>
          <p className="text-xl font-semibold text-slate-900">{data.buyerId}</p>
        </div>
      </div>
      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-slate-100 bg-slate-50/70 p-5">
          <h3 className="text-base font-semibold text-slate-900">Inputs</h3>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-white p-4 text-xs text-slate-700">
            {JSON.stringify(data.inputs, null, 2)}
          </pre>
        </section>
        <section className="rounded-2xl border border-slate-100 bg-slate-50/70 p-5">
          <h3 className="text-base font-semibold text-slate-900">Deliverables</h3>
          {data.deliverables && data.deliverables.length > 0 ? (
            <ul className="mt-3 space-y-3 text-sm text-slate-700">
              {data.deliverables.map((item) => (
                <li key={item.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="font-medium text-slate-900">{item.summary}</p>
                  <a className="text-brand-500" href={item.artifactUrl} target="_blank" rel="noreferrer">
                    View artifact
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-500">No deliverables yet.</p>
          )}
        </section>
      </div>
    </section>
  );
}
