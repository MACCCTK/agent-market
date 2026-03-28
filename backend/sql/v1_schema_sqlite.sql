PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  avatar_url TEXT,
  status TEXT NOT NULL CHECK (status IN ('active', 'suspended', 'pending')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('openclaw', 'admin')),
  created_at TEXT NOT NULL,
  UNIQUE(user_id, role),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS agent_owner_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER UNIQUE NOT NULL,
  headline TEXT NOT NULL,
  bio TEXT,
  pricing_note TEXT,
  service_status TEXT NOT NULL CHECK (service_status IN ('online', 'offline', 'paused')),
  rating_avg NUMERIC DEFAULT 0,
  rating_count INTEGER DEFAULT 0,
  completed_order_count INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS openclaws (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  subscription_status TEXT NOT NULL CHECK (subscription_status IN ('subscribed', 'unsubscribed')),
  service_status TEXT NOT NULL CHECK (service_status IN ('available', 'busy', 'offline', 'paused')),
  active_order_id INTEGER,
  token_rate_per_100 NUMERIC NOT NULL DEFAULT 1.00,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (active_order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS openclaw_profiles (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  capacity_per_week INTEGER NOT NULL,
  service_config TEXT NOT NULL,
  subscription_status TEXT NOT NULL CHECK (subscription_status IN ('subscribed', 'unsubscribed')),
  service_status TEXT NOT NULL CHECK (service_status IN ('available', 'busy', 'offline', 'paused')),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS openclaw_task_orders (
  id INTEGER PRIMARY KEY,
  order_no TEXT NOT NULL,
  requester_openclaw_id INTEGER NOT NULL,
  executor_openclaw_id INTEGER,
  task_template_id INTEGER NOT NULL,
  capability_package_id INTEGER,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  quoted_price NUMERIC NOT NULL,
  currency TEXT NOT NULL,
  sla_hours INTEGER NOT NULL,
  requirement_payload TEXT NOT NULL,
  accepted_at TEXT,
  delivered_at TEXT,
  completed_at TEXT,
  cancelled_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS openclaw_task_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  actor_openclaw_id INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  event_payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  task_type TEXT NOT NULL,
  description TEXT NOT NULL,
  input_schema TEXT NOT NULL,
  output_schema TEXT NOT NULL,
  acceptance_schema TEXT NOT NULL,
  pricing_model TEXT NOT NULL CHECK (pricing_model IN ('fixed', 'tiered', 'quote_based')),
  base_price NUMERIC,
  sla_hours INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capability_packages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  task_template_id INTEGER NOT NULL,
  sample_deliverables TEXT,
  price_min NUMERIC,
  price_max NUMERIC,
  capacity_per_week INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'paused')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (owner_user_id) REFERENCES users(id),
  FOREIGN KEY (task_template_id) REFERENCES task_templates(id)
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_no TEXT UNIQUE NOT NULL,
  buyer_user_id INTEGER NOT NULL,
  owner_user_id INTEGER,
  task_template_id INTEGER NOT NULL,
  capability_package_id INTEGER,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  quoted_price NUMERIC NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  sla_hours INTEGER NOT NULL,
  requirement_payload TEXT NOT NULL,
  accepted_at TEXT,
  delivered_at TEXT,
  completed_at TEXT,
  cancelled_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (buyer_user_id) REFERENCES users(id),
  FOREIGN KEY (owner_user_id) REFERENCES users(id),
  FOREIGN KEY (task_template_id) REFERENCES task_templates(id),
  FOREIGN KEY (capability_package_id) REFERENCES capability_packages(id)
);

CREATE TABLE IF NOT EXISTS deliverables (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  version_no INTEGER NOT NULL,
  delivery_note TEXT,
  deliverable_payload TEXT NOT NULL,
  submitted_by INTEGER NOT NULL,
  submitted_at TEXT NOT NULL,
  UNIQUE(order_id, version_no),
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (submitted_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS acceptance_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  deliverable_id INTEGER NOT NULL,
  reviewer_user_id INTEGER NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'revision_requested')),
  checklist_result TEXT NOT NULL,
  comment TEXT,
  reviewed_at TEXT NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (deliverable_id) REFERENCES deliverables(id),
  FOREIGN KEY (reviewer_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS settlements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER UNIQUE NOT NULL,
  payment_status TEXT NOT NULL CHECK (payment_status IN ('pending', 'escrowed', 'released', 'refunded')),
  payment_channel TEXT,
  hire_fee NUMERIC,
  token_used INTEGER,
  token_fee NUMERIC,
  total_fee NUMERIC,
  escrow_amount NUMERIC NOT NULL,
  platform_fee NUMERIC NOT NULL,
  owner_payout_amount NUMERIC NOT NULL,
  escrowed_at TEXT,
  released_at TEXT,
  refunded_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS disputes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  opened_by INTEGER NOT NULL,
  reason_code TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'investigating', 'resolved_buyer', 'resolved_owner', 'closed')),
  resolution_note TEXT,
  resolved_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (opened_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  actor_user_id INTEGER,
  event_type TEXT NOT NULL,
  event_payload TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (actor_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_orders_buyer_status ON orders(buyer_user_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_owner_status ON orders(owner_user_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_template_status ON orders(task_template_id, status);
CREATE INDEX IF NOT EXISTS idx_capability_packages_owner_status ON capability_packages(owner_user_id, status);
CREATE INDEX IF NOT EXISTS idx_task_templates_task_type_status ON task_templates(task_type, status);
CREATE INDEX IF NOT EXISTS idx_disputes_order_status ON disputes(order_id, status);
CREATE INDEX IF NOT EXISTS idx_order_events_order_created ON order_events(order_id, created_at DESC);

-- Seed fixed v1 task templates
INSERT OR IGNORE INTO task_templates (
  code, name, task_type, description, input_schema, output_schema, acceptance_schema,
  pricing_model, base_price, sla_hours, status, created_at, updated_at
)
VALUES
  ('research_brief_basic', 'Research Brief', 'research_brief', 'Structured market and product research brief', '{}', '{}', '{}', 'fixed', 1.00, 48, 'active', datetime('now'), datetime('now')),
  ('content_draft_standard', 'Content Draft', 'content_draft', 'Draft SEO/article/content assets', '{}', '{}', '{}', 'fixed', 2.00, 24, 'active', datetime('now'), datetime('now')),
  ('code_fix_small_automation_basic', 'Code Fix Small Automation', 'code_fix_small_automation', 'Small fix, script, or automation', '{}', '{}', '{}', 'fixed', 3.00, 48, 'active', datetime('now'), datetime('now')),
  ('data_cleanup_analysis_basic', 'Data Cleanup Analysis', 'data_cleanup_analysis', 'Data cleaning and structured analysis', '{}', '{}', '{}', 'fixed', 4.00, 36, 'active', datetime('now'), datetime('now')),
  ('workflow_setup_basic', 'Workflow Setup', 'workflow_setup', 'Set up reusable workflow with docs', '{}', '{}', '{}', 'fixed', 5.00, 72, 'active', datetime('now'), datetime('now'));
