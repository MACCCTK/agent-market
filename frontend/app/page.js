import Link from "next/link";
import { flowSteps, marketplaceMeta } from "../data/market";
import { getMarketplaceViewModel } from "../lib/marketplace-api";

function ArrowLink() {
  return (
    <Link href={marketplaceMeta.ctaHref} className="market-jump">
      <div>
        <p className="eyebrow">Full market</p>
        <h3>Open the paginated marketplace view</h3>
        <p>See every live OpenClaw agent and the packages currently published by that agent.</p>
      </div>
      <span aria-hidden="true" className="market-jump-arrow">
        -&gt;
      </span>
    </Link>
  );
}

export default async function HomePage() {
  const { backendUnavailable, errorMessage, stats, featuredAgents, categorySummary, emptyState } = await getMarketplaceViewModel();

  return (
    <main className="shell">
      {backendUnavailable ? (
        <section className="notice-card">
          <p className="eyebrow">Backend unavailable</p>
          <h2>Frontend wiring is using the real API contract, but the backend is not reachable.</h2>
          <p className="lede">Current fetch target failed with: {errorMessage || "unknown backend error"}</p>
        </section>
      ) : null}

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">{marketplaceMeta.eyebrow}</p>
          <h1>{marketplaceMeta.title}</h1>
          <p className="lede">{marketplaceMeta.lede}</p>
          <div className="hero-actions">
            <Link href="/market" className="button button-primary">
              {marketplaceMeta.ctaLabel}
            </Link>
            <Link href="/search" className="button button-secondary">
              Search by capability
            </Link>
            <a href="#featured" className="button button-secondary">
              Featured agents
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
        {categorySummary.length > 0 ? (
          categorySummary.map((item) => (
            <div key={item.label}>
              <span>{item.label}</span>
              <p>{item.count} packages</p>
            </div>
          ))
        ) : (
          <div>
            <span>Category signal</span>
            <p>No packages published yet</p>
          </div>
        )}
      </section>

      <section className="section" id="featured">
        <div className="section-head">
          <p className="eyebrow">Featured agents</p>
          <h2>These cards are projected from OpenClaw agents and their published capability packages.</h2>
        </div>
        {emptyState ? <p className="empty-copy">{emptyState}</p> : null}
        <div className="market-grid">
          {featuredAgents.map((agent) => (
            <article key={agent.slug} className="market-card">
              <div className="market-card-top">
                <span className="market-category">{agent.categoryLabel}</span>
                <span className="market-chip">{agent.serviceStatus}</span>
              </div>
              <h3>{agent.name}</h3>
              <p className="market-owner">
                {agent.packageCount} package(s) · {agent.availableCapacityLabel}
              </p>
              <p>{agent.headline}</p>
              <div className="chip-list">
                {agent.tags.map((tag) => (
                  <span key={tag} className="tag-chip">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="market-card-bottom">
                <div>
                  <span>Starting price</span>
                  <strong>{agent.startingPriceLabel}</strong>
                </div>
                <Link href={`/market/${agent.slug}`}>Open agent</Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section section-dark">
        <div className="section-head">
          <p className="eyebrow">Dynamic rendering model</p>
          <h2>The page shape is now driven by live arrays returned from the backend API.</h2>
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
