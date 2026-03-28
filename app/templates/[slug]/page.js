import Link from "next/link";
import { notFound } from "next/navigation";
import { templates } from "../../../data/market";

export function generateStaticParams() {
  return templates.map((template) => ({ slug: template.slug }));
}

export default function TemplateDetailPage({ params }) {
  const template = templates.find((item) => item.slug === params.slug);

  if (!template) {
    notFound();
  }

  return (
    <main className="shell detail-shell">
      <Link href="/" className="back-link">
        Back to catalog
      </Link>

      <section className="detail-hero">
        <div>
          <p className="eyebrow">{template.accent}</p>
          <h1>{template.name}</h1>
          <p className="lede">{template.blurb}</p>
          <p className="fit-copy">{template.fit}</p>
        </div>
        <aside className="detail-summary">
          <div>
            <span>Starting price</span>
            <strong>{template.price}</strong>
          </div>
          <div>
            <span>Delivery promise</span>
            <strong>{template.sla}</strong>
          </div>
        </aside>
      </section>

      <section className="detail-grid">
        <article className="detail-card">
          <h2>Buyer inputs</h2>
          <ul>
            {template.inputs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card">
          <h2>Expected outputs</h2>
          <ul>
            {template.outputs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card detail-card-wide">
          <h2>Acceptance checklist</h2>
          <ul>
            {template.checklist.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
