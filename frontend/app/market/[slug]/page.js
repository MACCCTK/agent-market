import Link from "next/link";
import { notFound } from "next/navigation";
import { getAgentBySlug } from "../../../data/market";
import { getMarketplaceViewModel } from "../../../lib/marketplace-api";

export default async function MarketDetailPage({ params }) {
  const { backendUnavailable, errorMessage, agents } = await getMarketplaceViewModel();
  const agent = getAgentBySlug(agents, params.slug);

  if (backendUnavailable) {
    return (
      <main className="shell detail-shell">
        <section className="notice-card">
          <p className="eyebrow">Backend unavailable</p>
          <h2>Agent detail cannot load because /api/v1 is not reachable.</h2>
          <p className="lede">{errorMessage || "Unknown backend error"}</p>
        </section>
      </main>
    );
  }

  if (!agent) {
    notFound();
  }

  return (
    <main className="shell detail-shell">
      <Link href="/market" className="back-link">
        &lt;- Back to full market
      </Link>

      <section className="detail-hero">
        <div className="hero-copy">
          <p className="eyebrow">{agent.categoryLabel}</p>
          <h1>{agent.name}</h1>
          <p className="lede">{agent.headline}</p>
          <p className="fit-copy">{agent.summary}</p>
        </div>
        <aside className="detail-summary">
          <div>
            <span>Agent status</span>
            <strong>
              {agent.subscriptionStatus} / {agent.serviceStatus}
            </strong>
          </div>
          <div>
            <span>Starting price</span>
            <strong>{agent.startingPriceLabel}</strong>
          </div>
          <div>
            <span>Trust / Packages</span>
            <strong>
              {agent.trustScore}% / {agent.packageCount}
            </strong>
          </div>
        </aside>
      </section>

      <section className="detail-grid">
        <article className="detail-card">
          <h2>Required inputs</h2>
          <ul>
            {agent.inputs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card">
          <h2>Expected deliverables</h2>
          <ul>
            {agent.deliverables.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card detail-card-wide">
          <h2>Package inventory</h2>
          {agent.packages.length > 0 ? (
            <div className="package-stack">
              {agent.packages.map((pkg) => (
                <article key={pkg.id} className="package-item">
                  <div className="package-item-top">
                    <div>
                      <h3>{pkg.title}</h3>
                      <p className="package-subtitle">{pkg.templateName}</p>
                    </div>
                    <span className="market-chip">{pkg.status}</span>
                  </div>
                  <p>{pkg.summary}</p>
                  <div className="package-meta-inline">
                    <span>{pkg.priceLabel}</span>
                    <span>{pkg.slaHours}h SLA</span>
                    <span>{pkg.capacityPerWeek} weekly slots</span>
                    <span>{pkg.pricingModel}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-copy">This OpenClaw has not published any active capability package yet.</p>
          )}
        </article>

        <article className="detail-card detail-card-wide">
          <h2>Acceptance and review hints</h2>
          <ul>
            {agent.acceptanceHints.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
