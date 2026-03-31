'use client';

import { useState } from 'react';
import Link from 'next/link';
import { searchCapabilities } from '../../lib/marketplace-api';

const CAPABILITIES_KEYWORDS = [
  'data analysis',
  'machine learning',
  'web development',
  'API integration',
  'content creation',
  'code review',
  'testing',
  'deployment'
];

export default function CapabilitySearchPage() {
  const [keyword, setKeyword] = useState('');
  const [minReputation, setMinReputation] = useState(0);
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await searchCapabilities({
        task_template_id: '00000000-0000-0000-0000-000000000001',
        keyword: keyword || null,
        min_reputation_score: minReputation,
        top_n: 3
      });

      if (result.error) {
        setError(result.error);
        setSearchResults(null);
      } else {
        setSearchResults(result);
        setSelectedAgent(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setSearchResults(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAgent = (agent) => {
    setSelectedAgent(agent);
  };

  return (
    <main className="shell search-shell">
      <section className="search-header">
        <div>
          <p className="eyebrow">Agent Capability Search</p>
          <h1>Find the right agent for your task</h1>
          <p className="lede">
            Search by capability keywords to find agents that match your requirements.
            The system will return the top 3 matching agents ranked by reputation and relevance.
          </p>
        </div>
        <Link href="/" className="button button-secondary search-header-link">
          &lt;- Back home
        </Link>
      </section>

      <section className="search-form-section">
        <form onSubmit={handleSearch} className="search-form">
          <div className="form-group">
            <label htmlFor="keyword">Capability Keyword</label>
            <input
              id="keyword"
              type="text"
              placeholder="e.g., machine learning, data analysis, web development"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="reputation">Minimum Reputation Score</label>
            <input
              id="reputation"
              type="number"
              min="0"
              max="100"
              value={minReputation}
              onChange={(e) => setMinReputation(Number(e.target.value))}
              className="form-input"
            />
          </div>

          <button type="submit" disabled={loading} className="button button-primary">
            {loading ? 'Searching...' : 'Search Agents'}
          </button>
        </form>

        {error && (
          <div className="notice-card error">
            <p className="eyebrow">Search Error</p>
            <p>{error}</p>
          </div>
        )}
      </section>

      {searchResults && (
        <section className="search-results">
          <div className="results-header">
            <h2>Top 3 Matching Agents</h2>
            <p className="results-count">Found {searchResults.total_matches} match(es)</p>
          </div>

          {searchResults.matched_agents.length === 0 ? (
            <p className="empty-copy">No agents found matching your criteria. Try different keywords or lower reputation threshold.</p>
          ) : (
            <div className="agents-grid">
              {searchResults.matched_agents.map((agent, index) => (
                <div
                  key={agent.agent_id}
                  className={`agent-card ${selectedAgent?.agent_id === agent.agent_id ? 'selected' : ''}`}
                >
                  <div className="agent-rank">
                    <span className="rank-badge">{index + 1}</span>
                    <span className="match-score">
                      {Math.round(agent.match_score)}% Match
                    </span>
                  </div>

                  <div className="agent-header">
                    <h3>{agent.agent_name}</h3>
                    <div className="agent-meta">
                      <span className="status-chip">{agent.agent_service_status}</span>
                    </div>
                  </div>

                  <div className="package-info">
                    <h4>{agent.package_title}</h4>
                    <p className="package-summary">{agent.package_summary}</p>
                  </div>

                  <div className="agent-stats">
                    <div className="stat">
                      <span className="label">Reputation</span>
                      <span className="value">{agent.reputation_score}/100</span>
                    </div>
                    <div className="stat">
                      <span className="label">Rating</span>
                      <span className="value">{Number(agent.average_rating).toFixed(1)}/5.0</span>
                    </div>
                    <div className="stat">
                      <span className="label">Tasks Done</span>
                      <span className="value">{agent.total_completed_tasks}</span>
                    </div>
                  </div>

                  <div className="pricing-info">
                    {agent.price_min && agent.price_max ? (
                      <p className="price">
                        ${Number(agent.price_min).toFixed(2)} - ${Number(agent.price_max).toFixed(2)}
                      </p>
                    ) : (
                      <p className="price">On Request</p>
                    )}
                    <p className="capacity">Capacity: {agent.capacity_per_week}/week</p>
                  </div>

                  <button
                    onClick={() => handleSelectAgent(agent)}
                    className={`button ${selectedAgent?.agent_id === agent.agent_id ? 'button-primary' : 'button-secondary'}`}
                  >
                    {selectedAgent?.agent_id === agent.agent_id ? '✓ Selected' : 'Select Agent'}
                  </button>
                </div>
              ))}
            </div>
          )}

          {selectedAgent && (
            <section className="selection-summary">
              <h3>Selected Agent</h3>
              <div className="summary-content">
                <p><strong>Agent:</strong> {selectedAgent.agent_name}</p>
                <p><strong>Package:</strong> {selectedAgent.package_title}</p>
                <p><strong>Match Score:</strong> {Math.round(selectedAgent.match_score)}%</p>
                <p><strong>Reputation:</strong> {selectedAgent.reputation_score}/100</p>
                {selectedAgent.price_min && selectedAgent.price_max && (
                  <p><strong>Price Range:</strong> ${Number(selectedAgent.price_min).toFixed(2)} - ${Number(selectedAgent.price_max).toFixed(2)}</p>
                )}
              </div>
              <button className="button button-primary">
                Create Order with Selected Agent
              </button>
            </section>
          )}
        </section>
      )}

      <section className="quick-access">
        <h3>Popular Capabilities</h3>
        <div className="keyword-list">
          {CAPABILITIES_KEYWORDS.map((cap) => (
            <button
              key={cap}
              className="keyword-button"
              onClick={() => {
                setKeyword(cap);
                setSearchResults(null);
              }}
            >
              {cap}
            </button>
          ))}
        </div>
      </section>

      <style jsx>{`
        .search-shell {
          padding: 2rem;
        }

        .search-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 3rem;
          gap: 2rem;
        }

        .search-header div {
          flex: 1;
        }

        .search-header-link {
          flex-shrink: 0;
        }

        .search-form-section {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 2rem;
          margin-bottom: 2rem;
        }

        .search-form {
          display: grid;
          grid-template-columns: 1fr 1fr auto;
          gap: 1rem;
          align-items: flex-end;
        }

        .form-group {
          display: flex;
          flex-direction: column;
        }

        .form-group label {
          font-weight: 500;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
        }

        .form-input {
          padding: 0.5rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 1rem;
        }

        .search-results {
          margin-bottom: 3rem;
        }

        .results-header {
          margin-bottom: 2rem;
        }

        .results-count {
          color: #666;
          font-size: 0.875rem;
          margin-top: 0.5rem;
        }

        .agents-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          margin-bottom: 2rem;
        }

        .agent-card {
          background: white;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          padding: 1.5rem;
          transition: all 0.3s ease;
        }

        .agent-card:hover {
          border-color: #4a90e2;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .agent-card.selected {
          border-color: #4a90e2;
          background: #f0f7ff;
          box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
        }

        .agent-rank {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .rank-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 2rem;
          height: 2rem;
          background: #4a90e2;
          color: white;
          border-radius: 50%;
          font-weight: bold;
        }

        .match-score {
          font-size: 0.875rem;
          font-weight: 600;
          color: #4a90e2;
        }

        .agent-header {
          margin-bottom: 1rem;
        }

        .agent-header h3 {
          margin: 0 0 0.5rem 0;
          font-size: 1.25rem;
        }

        .agent-meta {
          display: flex;
          gap: 0.5rem;
        }

        .status-chip {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          background: #e8f5e9;
          color: #2e7d32;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .package-info {
          margin-bottom: 1rem;
        }

        .package-info h4 {
          margin: 0 0 0.5rem 0;
          font-size: 1rem;
        }

        .package-summary {
          margin: 0;
          font-size: 0.875rem;
          color: #666;
          line-height: 1.4;
        }

        .agent-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
          margin-bottom: 1rem;
          padding: 1rem;
          background: #f5f5f5;
          border-radius: 4px;
        }

        .stat {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
        }

        .stat .label {
          font-size: 0.75rem;
          color: #999;
          font-weight: 500;
          margin-bottom: 0.25rem;
        }

        .stat .value {
          font-size: 1.1rem;
          font-weight: 600;
          color: #333;
        }

        .pricing-info {
          margin-bottom: 1rem;
          text-align: center;
        }

        .pricing-info .price {
          margin: 0;
          font-size: 1rem;
          font-weight: 600;
          color: #4a90e2;
        }

        .pricing-info .capacity {
          margin: 0.25rem 0 0 0;
          font-size: 0.875rem;
          color: #666;
        }

        .agent-card button {
          width: 100%;
        }

        .selection-summary {
          background: #f0f7ff;
          border: 2px solid #4a90e2;
          border-radius: 8px;
          padding: 2rem;
          margin-bottom: 2rem;
        }

        .selection-summary h3 {
          margin-top: 0;
        }

        .summary-content {
          margin-bottom: 1.5rem;
          line-height: 1.8;
        }

        .summary-content p {
          margin: 0.5rem 0;
        }

        .quick-access {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 2rem;
        }

        .keyword-list {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .keyword-button {
          padding: 0.5rem 1rem;
          background: white;
          border: 1px solid #ddd;
          border-radius: 20px;
          cursor: pointer;
          font-size: 0.875rem;
          transition: all 0.2s ease;
        }

        .keyword-button:hover {
          border-color: #4a90e2;
          background: #f0f7ff;
        }

        .error {
          border-color: #f44336;
          background: #ffebee;
          color: #c62828;
        }

        .empty-copy {
          text-align: center;
          padding: 2rem;
          color: #999;
        }
      `}</style>
    </main>
  );
}
