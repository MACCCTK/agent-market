import Link from "next/link";
import { api } from "../../../lib/api";
import { Checklist } from "../../../components/Checklist";

type TemplatePageProps = {
  params: { id: string };
  searchParams: { action?: string };
};

export default async function TemplatePage({ params }: TemplatePageProps) {
  const [templateRes, packagesRes] = await Promise.all([api.getTemplate(params.id), api.listPackages()]);
  const template = templateRes.data;
  const packages = packagesRes.data.filter((pkg) => pkg.supportedTemplateIds.includes(template.id));

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div>
            <p className="text-xs uppercase tracking-[0.5em] text-brand-500">Template</p>
            <h2 className="mt-2 text-3xl font-semibold text-slate-900">{template.name}</h2>
            <p className="mt-3 max-w-3xl text-slate-600">{template.summary}</p>
          </div>
          <div className="rounded-2xl bg-slate-50 px-6 py-4 text-center">
            <p className="text-sm text-slate-500">SLA</p>
            <p className="text-3xl font-semibold text-slate-900">{template.slaHours}h</p>
            <p className="mt-4 text-sm text-slate-500">Base Price</p>
            <p className="text-2xl font-semibold text-slate-900">
              {template.pricing.currency} {template.pricing.basePrice}
            </p>
          </div>
        </div>
        <p className="mt-6 text-sm text-slate-500">
          Runs on Zeabur skill <span className="font-semibold">{template.zeaburSkill.skillId}</span> (v
          {template.zeaburSkill.version}).
        </p>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Required Inputs</h3>
          <ul className="space-y-3 text-sm text-slate-700">
            {template.inputs.map((input) => (
              <li key={input.id} className="flex items-start gap-3">
                <span className="mt-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700">
                  {input.required ? "*" : ""}
                </span>
                <div>
                  <p className="font-medium text-slate-900">{input.label}</p>
                  <p className="text-slate-500">
                    Type: {input.type}
                    {input.maxLength ? ` · ≤${input.maxLength} chars` : ""}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <Checklist title="Acceptance Checklist" items={template.acceptanceChecklist} />
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-slate-900">Available Capability Packages</h3>
          <Link href="/owner/dashboard" className="text-sm font-medium text-brand-500 hover:text-brand-700">
            Manage supply →
          </Link>
        </div>
        <ul className="space-y-3">
          {packages.length === 0 && <p className="text-sm text-slate-500">No packages currently mapped to this template.</p>}
          {packages.map((pkg) => (
            <li key={pkg.id} className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Package</p>
                  <p className="text-lg font-semibold text-slate-900">{pkg.title}</p>
                  <p className="text-sm text-slate-600">{pkg.description}</p>
                </div>
                <div className="text-right text-sm text-slate-500">
                  <p>Capacity: {pkg.capacity}</p>
                  <p>
                    Price {pkg.priceRange.currency} {pkg.priceRange.min}–{pkg.priceRange.max}
                  </p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-dashed border-brand-200 bg-white/70 p-6">
          <h3 className="text-base font-semibold text-slate-900">Order Steps</h3>
          <ol className="mt-4 space-y-3 text-sm text-slate-700">
            <li>1. Collect inputs above and submit order form.</li>
            <li>2. Funds are held in escrow; owner accepts within SLA.</li>
            <li>3. Zeabur skill executes with captured payload.</li>
            <li>4. Deliverable uploaded, Buyer reviews checklist.</li>
          </ol>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-base font-semibold text-slate-900">Rejection Conditions</h3>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-700">
            {template.rejectionNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
