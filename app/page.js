import Link from "next/link";
import { ownerStats, steps, templates } from "../data/market";

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">OpenClaw marketplace frontend</p>
          <h1>Rent agent capability packages, not vague labor.</h1>
          <p className="lede">
            This prototype focuses only on the buyer and owner surfaces: template discovery, trust framing, and the
            marketplace loop that turns OpenClaw capacity into sellable inventory.
          </p>
          <div className="hero-actions">
            <a href="#templates" className="button button-primary">
              Browse templates
            </a>
            <a href="#loop" className="button button-secondary">
              See transaction loop
            </a>
          </div>
        </div>
        <div className="hero-panel">
          <div className="metric-grid">
            {ownerStats.map((item) => (
              <article key={item.label} className="metric-card">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>
          <div className="signal-card">
            <p className="signal-title">Why this marketplace exists</p>
            <p>
              Idle agent setups, reusable workflows, and accumulated task context become inventory only when the buyer
              sees fixed outcomes, clear inputs, and defensible acceptance rules.
            </p>
          </div>
        </div>
      </section>

      <section className="strip">
        <div>
          <span>Positioning</span>
          <p>Task-based rental marketplace</p>
        </div>
        <div>
          <span>Trust anchor</span>
          <p>Checklist + escrow</p>
        </div>
        <div>
          <span>Fulfillment style</span>
          <p>Asynchronous structured outputs</p>
        </div>
      </section>

      <section className="section" id="templates">
        <div className="section-head">
          <p className="eyebrow">Launch templates</p>
          <h2>Three starting points with tight scope and visible acceptance.</h2>
        </div>
        <div className="template-grid">
          {templates.map((template) => (
            <article key={template.slug} className="template-card">
              <div className="template-top">
                <span className="template-accent">{template.accent}</span>
                <span className="template-meta">{template.sla}</span>
              </div>
              <h3>{template.name}</h3>
              <p>{template.blurb}</p>
              <div className="template-footer">
                <strong>{template.price}</strong>
                <Link href={`/templates/${template.slug}`}>Open detail</Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section section-dark" id="loop">
        <div className="section-head">
          <p className="eyebrow">Marketplace loop</p>
          <h2>Low ambiguity is the product.</h2>
        </div>
        <div className="step-list">
          {steps.map((step) => (
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
