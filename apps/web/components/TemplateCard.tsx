"use client";

import Link from "next/link";
import type { TemplateSummary } from "../lib/api";

type Props = {
  template: TemplateSummary;
};

export function TemplateCard({ template }: Props) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-brand-500">Template</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">{template.name}</h2>
          <p className="mt-2 text-sm text-slate-600">{template.summary}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-slate-500">SLA</p>
          <p className="text-lg font-semibold text-slate-900">{template.slaHours}h</p>
          <p className="text-sm text-slate-500 mt-2">Base</p>
          <p className="text-lg font-semibold text-slate-900">
            {template.pricing.currency} {template.pricing.basePrice}
          </p>
        </div>
      </div>
      <div className="mt-6 flex items-center justify-between">
        <Link
          href={`/templates/${template.id}`}
          className="text-sm font-medium text-brand-500 hover:text-brand-700"
        >
          View flow →
        </Link>
        <Link
          href={`/templates/${template.id}?action=order`}
          className="rounded-full bg-brand-500 px-4 py-2 text-sm font-semibold text-white shadow"
        >
          Start Order
        </Link>
      </div>
    </article>
  );
}
