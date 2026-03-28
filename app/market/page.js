import Link from "next/link";
import { agentMarkets, paginateMarkets } from "../../data/market";

const PAGE_SIZE = 6;

function buildPageHref(page) {
  return `/market?page=${page}`;
}

export default function MarketPage({ searchParams }) {
  const page = Number.parseInt(searchParams?.page ?? "1", 10);
  const { currentPage, totalPages, items } = paginateMarkets(page, PAGE_SIZE, agentMarkets);
  const pages = Array.from({ length: totalPages }, (_, index) => index + 1);

  return (
    <main className="shell market-shell">
      <section className="market-header">
        <div>
          <p className="eyebrow">All agent market packages</p>
          <h1>Paginated inventory for every live agent package.</h1>
          <p className="lede">
            This page is designed to accept a larger backend result set and render it without assuming a fixed number of
            cards on the homepage.
          </p>
        </div>
        <Link href="/" className="button button-secondary market-header-link">
          ← Back home
        </Link>
      </section>

      <div className="market-grid">
        {items.map((market) => (
          <article key={market.slug} className="market-card">
            <div className="market-card-top">
              <span className="market-category">{market.category}</span>
              <span className="market-chip">{market.availableSlots} slots</span>
            </div>
            <h3>{market.name}</h3>
            <p className="market-owner">{market.owner}</p>
            <p>{market.headline}</p>
            <div className="market-meta-grid">
              <div>
                <span>From</span>
                <strong>${market.priceFrom}</strong>
              </div>
              <div>
                <span>Trust</span>
                <strong>{market.trustScore}%</strong>
              </div>
            </div>
            <div className="chip-list">
              {market.regions.map((region) => (
                <span key={region} className="tag-chip">
                  {region}
                </span>
              ))}
            </div>
            <div className="market-card-bottom">
              <div>
                <span>SLA</span>
                <strong>{market.slaHours}h</strong>
              </div>
              <Link href={`/market/${market.slug}`}>Open package</Link>
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
