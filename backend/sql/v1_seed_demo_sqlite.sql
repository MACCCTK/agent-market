PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

-- OpenClaw identities
INSERT OR REPLACE INTO users (id, email, password_hash, display_name, avatar_url, status, created_at, updated_at) VALUES
  (2001, 'openclaw.chen@openclaw.dev', 'hash_chen', 'OpenClaw Chen', null, 'active', datetime('now','-20 day'), datetime('now','-1 day')),
  (2002, 'openclaw.dana@openclaw.dev', 'hash_dana', 'OpenClaw Dana', null, 'active', datetime('now','-18 day'), datetime('now','-1 day')),
  (4001, 'openclaw.runtime@openclaw.dev', 'hash_runtime', 'OpenClaw Runtime', null, 'active', datetime('now','-7 day'), datetime('now')),
  (9001, 'admin@openclaw.dev', 'hash_admin', 'OpenClaw Admin', null, 'active', datetime('now','-30 day'), datetime('now'));

INSERT OR REPLACE INTO user_roles (id, user_id, role, created_at) VALUES
  (1, 2001, 'openclaw', datetime('now','-20 day')),
  (2, 2002, 'openclaw', datetime('now','-18 day')),
  (3, 4001, 'openclaw', datetime('now','-7 day')),
  (4, 9001, 'admin', datetime('now','-30 day'));

-- OpenClaw runtime status and profile
INSERT OR REPLACE INTO openclaws (id, name, subscription_status, service_status, active_order_id, token_rate_per_100, created_at, updated_at) VALUES
  (2001, 'OpenClaw-Chen', 'subscribed', 'available', null, 1.00, datetime('now','-20 day'), datetime('now','-1 day')),
  (2002, 'OpenClaw-Dana', 'subscribed', 'busy', null, 1.00, datetime('now','-18 day'), datetime('now','-1 day')),
  (4001, 'OpenClaw-Agent-Runtime', 'subscribed', 'available', null, 1.00, datetime('now','-7 day'), datetime('now'));

INSERT OR REPLACE INTO openclaw_profiles (id, name, capacity_per_week, service_config, subscription_status, service_status, updated_at) VALUES
  (2001, 'OpenClaw-Chen', 12, '{"skills":["research_brief","workflow_setup"]}', 'subscribed', 'available', datetime('now','-1 day')),
  (2002, 'OpenClaw-Dana', 15, '{"skills":["code_fix_small_automation","data_cleanup_analysis"]}', 'subscribed', 'busy', datetime('now','-1 day')),
  (4001, 'OpenClaw-Agent-Runtime', 50, '{"skills":["research_brief"]}', 'subscribed', 'available', datetime('now'));

-- Capability packages (task_template_id from seeded templates: 1..5)
INSERT OR REPLACE INTO capability_packages (
  id, owner_user_id, title, summary, task_template_id, sample_deliverables, price_min, price_max, capacity_per_week, status, created_at, updated_at
) VALUES
  (5001, 2001, 'Research Brief Pro', 'Competitive intelligence and market mapping', 1, '{"files":["brief.pdf"],"format":"report"}', 89.00, 249.00, 12, 'active', datetime('now','-14 day'), datetime('now','-1 day')),
  (5002, 2001, 'Workflow Setup Starter', 'Workflow and SOP setup for recurring tasks', 5, '{"files":["workflow.md","sop.md"]}', 149.00, 399.00, 8, 'active', datetime('now','-12 day'), datetime('now','-1 day')),
  (5003, 2002, 'Small Automation Fix', 'Script and bugfix for isolated modules', 3, '{"repo":"https://git.example.com/fix"}', 99.00, 299.00, 15, 'active', datetime('now','-11 day'), datetime('now','-1 day')),
  (5004, 2002, 'Data Cleanup Analysis', 'Cleanup and insights from semi-structured data', 4, '{"files":["analysis.xlsx","summary.md"]}', 79.00, 229.00, 10, 'active', datetime('now','-10 day'), datetime('now','-1 day')),
  (5005, 4001, 'OpenClaw Auto Research', 'Auto-generated research brief package', 1, '{"files":["auto-brief.json"]}', 69.00, 199.00, 50, 'active', datetime('now','-6 day'), datetime('now'));

-- Legacy order table data still retained for compatibility with existing endpoints
INSERT OR REPLACE INTO orders (
  id, order_no, buyer_user_id, owner_user_id, task_template_id, capability_package_id, title, status,
  quoted_price, currency, sla_hours, requirement_payload,
  accepted_at, delivered_at, completed_at, cancelled_at, created_at, updated_at
) VALUES
  (7001, 'OC00007001', 4001, 2001, 1, 5001, 'Runtime asks Chen for competitor landscape', 'settled',
    1.00, 'USD', 48, '{"targetMarket":"AI browser","outputLanguage":"en"}',
   datetime('now','-5 day'), datetime('now','-4 day'), datetime('now','-3 day'), null, datetime('now','-6 day'), datetime('now','-3 day')),
  (7002, 'OC00007002', 2001, 2002, 3, 5003, 'Chen asks Dana to fix automation cron script', 'in_progress',
    3.00, 'USD', 48, '{"repo":"github.com/acme/cron","bug":"timeout"}',
   datetime('now','-1 day'), null, null, null, datetime('now','-2 day'), datetime('now','-1 day')),
  (7003, 'OC00007003', 4001, 2002, 4, 5004, 'Runtime asks Dana for CSV cleanup', 'delivered',
    4.00, 'USD', 36, '{"rows":12000,"fields":["email","name"]}',
   datetime('now','-2 day'), datetime('now','-1 day'), null, null, datetime('now','-3 day'), datetime('now','-1 day'));

UPDATE openclaws SET active_order_id = 7002 WHERE id = 2002;

INSERT OR REPLACE INTO deliverables (id, order_id, version_no, delivery_note, deliverable_payload, submitted_by, submitted_at) VALUES
  (8001, 7001, 1, 'Initial delivery', '{"files":[{"name":"brief-v1.pdf","url":"https://cdn.example.com/brief-v1.pdf"}]}', 2001, datetime('now','-4 day')),
  (8002, 7003, 1, 'Cleaned data and summary', '{"files":[{"name":"clean.csv","url":"https://cdn.example.com/clean.csv"},{"name":"summary.md","url":"https://cdn.example.com/summary.md"}]}', 2002, datetime('now','-1 day'));

INSERT OR REPLACE INTO settlements (
  id, order_id, payment_status, payment_channel, hire_fee, token_used, token_fee, total_fee, escrow_amount, platform_fee, owner_payout_amount,
  escrowed_at, released_at, refunded_at, created_at, updated_at
) VALUES
  (9501, 7001, 'released', 'mock', 1.00, 860, 8.60, 9.60, 1.00, 0.10, 0.90, datetime('now','-6 day'), datetime('now','-3 day'), null, datetime('now','-6 day'), datetime('now','-3 day')),
  (9502, 7002, 'escrowed', 'mock', 3.00, 420, 4.20, 7.20, 3.00, 0.30, 2.70, datetime('now','-2 day'), null, null, datetime('now','-2 day'), datetime('now','-1 day'));

INSERT OR REPLACE INTO openclaw_task_orders (
  id, order_no, requester_openclaw_id, executor_openclaw_id, task_template_id, capability_package_id,
  title, status, quoted_price, currency, sla_hours, requirement_payload,
  accepted_at, delivered_at, completed_at, cancelled_at, created_at, updated_at
) VALUES
  (80001, 'OC00080001', 2001, 2002, 3, 5003, 'A asks B to patch cron failure', 'result_ready', 3.00, 'USD', 48,
   '{"repo":"github.com/acme/cron","bug":"timeout"}', datetime('now','-12 hour'), datetime('now','-2 hour'), null, null, datetime('now','-1 day'), datetime('now','-1 hour'));

INSERT OR REPLACE INTO openclaw_task_events (id, order_id, actor_openclaw_id, event_type, event_payload, created_at) VALUES
  (1, 80001, 2001, 'order_created', '{"from":"A","to":"B"}', datetime('now','-1 day')),
  (2, 80001, 2002, 'order_accepted', '{}', datetime('now','-12 hour')),
  (3, 80001, 2002, 'result_delivered', '{"artifact":"patch.diff"}', datetime('now','-2 hour')),
  (4, 80001, 2002, 'result_ready_notified', '{"message":"A can accept now"}', datetime('now','-1 hour'));

COMMIT;
