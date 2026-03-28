import Link from "next/link";
import { notFound } from "next/navigation";
import { agentMarkets, getMarketBySlug } from "../../../data/market";

export function generateStaticParams() {
  return agentMarkets.map((market) => ({ slug: market.slug }));
}

export default function MarketDetailPage({ params }) {
  const market = getMarketBySlug(params.slug);

  if (!market) {
    notFound();
  }

  return (
    <main className="shell detail-shell">
      <Link href="/market" className="back-link">
        ← Back to full market
      </Link>

      <section className="detail-hero">
        <div className="hero-copy">
          <p className="eyebrow">{market.category}</p>
          <h1>{market.name}</h1>
          <p className="lede">{market.headline}</p>
          <p className="fit-copy">{market.summary}</p>
        </div>
        <aside className="detail-summary">
          <div>
            <span>Owner</span>
            <strong>{market.owner}</strong>
          </div>
          <div>
            <span>Starting price</span>
            <strong>${market.priceFrom}</strong>
          </div>
          <div>
            <span>Trust / SLA</span>
            <strong>
              {market.trustScore}% / {market.slaHours}h
            </strong>
          </div>
        </aside>
      </section>

      <section className="detail-grid">
        <article className="detail-card">
          <h2>Required inputs</h2>
          <ul>
            {market.inputs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card">
          <h2>Expected deliverables</h2>
          <ul>
            {market.deliverables.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card detail-card-wide">
          <h2>Why this package belongs in the market</h2>
          <ul>
            {market.signals.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
