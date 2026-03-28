import Link from "next/link";
import {
  flowSteps,
  getCategorySummary,
  getFeaturedMarkets,
  getMarketStats,
  marketplaceMeta
} from "../data/market";

function ArrowLink() {
  return (
    <Link href={marketplaceMeta.ctaHref} className="market-jump">
      <div>
        <p className="eyebrow">Full market</p>
        <h3>Open the paginated marketplace view</h3>
        <p>See every agent package on a dedicated market page that can scale with backend results.</p>
      </div>
      <span aria-hidden="true" className="market-jump-arrow">
        ↗
      </span>
    </Link>
  );
}

export default function HomePage() {
  const stats = getMarketStats();
  const featuredMarkets = getFeaturedMarkets();
  const categorySummary = getCategorySummary();

  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">{marketplaceMeta.eyebrow}</p>
          <h1>{marketplaceMeta.title}</h1>
          <p className="lede">{marketplaceMeta.lede}</p>
          <div className="hero-actions">
            <Link href="/market" className="button button-primary">
              {marketplaceMeta.ctaLabel}
            </Link>
            <a href="#featured" className="button button-secondary">
              Featured packages
            </a>
          </div>
        </div>
        <div className="hero-panel">
          <div className="metric-grid">
            {stats.map((item) => (
              <article key={item.label} className="metric-card">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>
          <ArrowLink />
        </div>
      </section>

      <section className="strip">
        {categorySummary.map((item) => (
          <div key={item.label}>
            <span>{item.label}</span>
            <p>{item.count} packages</p>
          </div>
        ))}
      </section>

      <section className="section" id="featured">
        <div className="section-head">
          <p className="eyebrow">Featured inventory</p>
          <h2>These cards are projected from the market dataset, not hard-coded page slots.</h2>
        </div>
        <div className="market-grid">
          {featuredMarkets.map((market) => (
            <article key={market.slug} className="market-card">
              <div className="market-card-top">
                <span className="market-category">{market.category}</span>
                <span className="market-chip">{market.slaHours}h SLA</span>
              </div>
              <h3>{market.name}</h3>
              <p className="market-owner">{market.owner}</p>
              <p>{market.summary}</p>
              <div className="chip-list">
                {market.tags.map((tag) => (
                  <span key={tag} className="tag-chip">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="market-card-bottom">
                <div>
                  <span>From</span>
                  <strong>${market.priceFrom}</strong>
                </div>
                <Link href={`/market/${market.slug}`}>Open package</Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section section-dark">
        <div className="section-head">
          <p className="eyebrow">Dynamic rendering model</p>
          <h2>The page shape is now driven by arrays, counts, and slices from the market payload.</h2>
        </div>
        <div className="step-list">
          {flowSteps.map((step) => (
            <article key={step.id} className="step-card">
              <span>{step.id}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
