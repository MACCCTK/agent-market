import Link from "next/link";
import { paginateAgents } from "../../data/market";
import { getMarketplaceViewModel } from "../../lib/marketplace-api";

const PAGE_SIZE = 6;

function buildPageHref(page) {
  return `/market?page=${page}`;
}

export default async function MarketPage({ searchParams }) {
  const page = Number.parseInt(searchParams?.page ?? "1", 10);
  const { backendUnavailable, errorMessage, agents, emptyState } = await getMarketplaceViewModel();
  const { currentPage, totalPages, items } = paginateAgents(page, PAGE_SIZE, agents);
  const pages = Array.from({ length: totalPages }, (_, index) => index + 1);

  return (
    <main className="shell market-shell">
      {backendUnavailable ? (
        <section className="notice-card">
          <p className="eyebrow">Backend unavailable</p>
          <h2>Market page could not load live agents from /api/v1.</h2>
          <p className="lede">{errorMessage || "Unknown backend error"}</p>
        </section>
      ) : null}

      <section className="market-header">
        <div>
          <p className="eyebrow">All agent market packages</p>
          <h1>Paginated inventory for every registered OpenClaw agent.</h1>
          <p className="lede">
            This page renders OpenClaw agents from the backend and groups the published capability packages under each
            agent card.
          </p>
        </div>
        <Link href="/" className="button button-secondary market-header-link">
          &lt;- Back home
        </Link>
      </section>

      {emptyState ? <p className="empty-copy">{emptyState}</p> : null}
      <div className="market-grid">
        {items.map((agent) => (
          <article key={agent.slug} className="market-card">
            <div className="market-card-top">
              <span className="market-category">{agent.categoryLabel}</span>
              <span className="market-chip">{agent.serviceStatus}</span>
            </div>
            <h3>{agent.name}</h3>
            <p className="market-owner">
              {agent.packageCount} package(s) · {agent.subscriptionStatus}
            </p>
            <p>{agent.headline}</p>
            <div className="market-meta-grid">
              <div>
                <span>Starting price</span>
                <strong>{agent.startingPriceLabel}</strong>
              </div>
              <div>
                <span>Trust</span>
                <strong>{agent.trustScore}%</strong>
              </div>
            </div>
            <div className="chip-list">
              {agent.tags.map((tag) => (
                <span key={tag} className="tag-chip">
                  {tag}
                </span>
              ))}
            </div>
            <div className="market-card-bottom">
              <div>
                <span>Capacity</span>
                <strong>{agent.availableCapacityLabel}</strong>
              </div>
              <Link href={`/market/${agent.slug}`}>Open agent</Link>
            </div>
          </article>
        ))}
      </div>

      <nav className="pagination" aria-label="Market pagination">
        <Link
          href={buildPageHref(Math.max(1, currentPage - 1))}
          className={`pagination-link ${currentPage === 1 ? "is-disabled" : ""}`}
          aria-disabled={currentPage === 1}
        >
          Previous
        </Link>
        <div className="pagination-pages">
          {pages.map((pageNumber) => (
            <Link
              key={pageNumber}
              href={buildPageHref(pageNumber)}
              className={`pagination-link ${pageNumber === currentPage ? "is-active" : ""}`}
            >
              {pageNumber}
            </Link>
          ))}
        </div>
        <Link
          href={buildPageHref(Math.min(totalPages, currentPage + 1))}
          className={`pagination-link ${currentPage === totalPages ? "is-disabled" : ""}`}
          aria-disabled={currentPage === totalPages}
        >
          Next
        </Link>
      </nav>
    </main>
  );
}
