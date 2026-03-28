import { api } from "../lib/api";
import { TemplateCard } from "../components/TemplateCard";

export default async function HomePage() {
  const { data } = await api.listTemplates();

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-gradient-to-r from-brand-50 to-white p-8 shadow-sm">
        <p className="text-sm uppercase tracking-[0.4em] text-brand-700">Launch Catalog</p>
        <h2 className="mt-3 text-3xl font-semibold text-slate-900">Standardized templates with Zeabur-powered agents</h2>
        <p className="mt-4 max-w-3xl text-slate-600">
          Browse the initial template set, capture the required inputs, and spin up OpenClaw capability packages that run
          on the Zeabur-hosted skills deployed at <span className="font-semibold">bzhwdeddbzsh.zeabur.app</span>.
        </p>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        {data.map((template) => (
          <TemplateCard key={template.id} template={template} />
        ))}
      </section>
    </div>
  );
}
