-- ============================================
-- PHASE 5 ENTERPRISE ENGAGEMENT MIGRATION
-- Onboarding checklist, support ticketing + SLA, and QBR goals/metrics
-- ============================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ONBOARDING CHECKLIST
-- ============================================
CREATE TABLE IF NOT EXISTS onboarding_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL DEFAULT 'general',
    is_required BOOLEAN NOT NULL DEFAULT true,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
    sort_order INTEGER NOT NULL DEFAULT 0,
    due_date DATE,
    completed_at TIMESTAMPTZ,
    completed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_onboarding_items_tenant_status
    ON onboarding_items(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_onboarding_items_tenant_sort
    ON onboarding_items(tenant_id, sort_order, created_at);

-- ============================================
-- SUPPORT TICKETING + SLA
-- ============================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ticket_number VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL DEFAULT 'general',
    priority VARCHAR(10) NOT NULL DEFAULT 'p3'
        CHECK (priority IN ('p1', 'p2', 'p3')),
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    requester_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    assignee_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    first_response_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    sla_response_deadline TIMESTAMPTZ NOT NULL,
    sla_resolution_deadline TIMESTAMPTZ NOT NULL,
    is_sla_response_breached BOOLEAN NOT NULL DEFAULT false,
    is_sla_resolution_breached BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, ticket_number)
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_tenant_status
    ON support_tickets(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_tickets_tenant_priority
    ON support_tickets(tenant_id, priority, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assignee_status
    ON support_tickets(assignee_user_id, status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_resolution_deadline
    ON support_tickets(tenant_id, sla_resolution_deadline)
    WHERE status NOT IN ('resolved', 'closed');

CREATE TABLE IF NOT EXISTS support_ticket_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    author_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    is_internal BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_ticket_comments_ticket_created
    ON support_ticket_comments(ticket_id, created_at DESC);

-- ============================================
-- QBR CYCLES + GOALS
-- ============================================
CREATE TABLE IF NOT EXISTS qbr_cycles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    quarter_code VARCHAR(10) NOT NULL,
    title VARCHAR(255),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'completed')),
    notes TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, quarter_code),
    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_qbr_cycles_tenant_status
    ON qbr_cycles(tenant_id, status, start_date DESC);

CREATE TABLE IF NOT EXISTS qbr_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cycle_id UUID NOT NULL REFERENCES qbr_cycles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    metric_name VARCHAR(100),
    unit VARCHAR(30),
    target_value DECIMAL(15, 2) NOT NULL DEFAULT 0,
    current_value DECIMAL(15, 2) NOT NULL DEFAULT 0,
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'on_track'
        CHECK (status IN ('on_track', 'at_risk', 'off_track', 'achieved')),
    due_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qbr_goals_tenant_cycle
    ON qbr_goals(tenant_id, cycle_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_qbr_goals_owner_status
    ON qbr_goals(owner_user_id, status);

-- ============================================
-- RLS FOR NEW TABLES
-- ============================================
ALTER TABLE onboarding_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_ticket_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE qbr_cycles ENABLE ROW LEVEL SECURITY;
ALTER TABLE qbr_goals ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS onboarding_items_isolation_policy ON onboarding_items;
CREATE POLICY onboarding_items_isolation_policy ON onboarding_items
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

DROP POLICY IF EXISTS support_tickets_isolation_policy ON support_tickets;
CREATE POLICY support_tickets_isolation_policy ON support_tickets
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

DROP POLICY IF EXISTS support_ticket_comments_isolation_policy ON support_ticket_comments;
CREATE POLICY support_ticket_comments_isolation_policy ON support_ticket_comments
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

DROP POLICY IF EXISTS qbr_cycles_isolation_policy ON qbr_cycles;
CREATE POLICY qbr_cycles_isolation_policy ON qbr_cycles
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

DROP POLICY IF EXISTS qbr_goals_isolation_policy ON qbr_goals;
CREATE POLICY qbr_goals_isolation_policy ON qbr_goals
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

-- ============================================
-- UPDATED_AT TRIGGERS
-- ============================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'update_updated_at_column'
    ) THEN
        DROP TRIGGER IF EXISTS update_onboarding_items_updated_at ON onboarding_items;
        CREATE TRIGGER update_onboarding_items_updated_at
        BEFORE UPDATE ON onboarding_items
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS update_support_tickets_updated_at ON support_tickets;
        CREATE TRIGGER update_support_tickets_updated_at
        BEFORE UPDATE ON support_tickets
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS update_qbr_cycles_updated_at ON qbr_cycles;
        CREATE TRIGGER update_qbr_cycles_updated_at
        BEFORE UPDATE ON qbr_cycles
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS update_qbr_goals_updated_at ON qbr_goals;
        CREATE TRIGGER update_qbr_goals_updated_at
        BEFORE UPDATE ON qbr_goals
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

-- ============================================
-- PERMISSION SEEDS
-- ============================================
INSERT INTO permissions (code, name, resource, action, description)
VALUES
    ('onboarding.read', 'Read Onboarding Checklist', 'onboarding', 'read', 'View onboarding checklist and progress'),
    ('onboarding.write', 'Manage Onboarding Checklist', 'onboarding', 'write', 'Create and update onboarding items'),
    ('support.read', 'Read Support Tickets', 'support', 'read', 'View support tickets and comments'),
    ('support.write', 'Manage Support Tickets', 'support', 'write', 'Create and update support tickets'),
    ('support.assign', 'Assign Support Tickets', 'support', 'assign', 'Assign ticket ownership and responders'),
    ('qbr.read', 'Read QBR Cycles and Goals', 'qbr', 'read', 'View QBR cycles, goals, and metrics dashboard'),
    ('qbr.write', 'Manage QBR Cycles and Goals', 'qbr', 'write', 'Create and update QBR cycles and goals')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON (
    (r.code = 'owner' AND p.code IN (
        'onboarding.read', 'onboarding.write',
        'support.read', 'support.write', 'support.assign',
        'qbr.read', 'qbr.write'
    )) OR
    (r.code = 'admin' AND p.code IN (
        'onboarding.read', 'onboarding.write',
        'support.read', 'support.write', 'support.assign',
        'qbr.read', 'qbr.write'
    ))
)
ON CONFLICT DO NOTHING;

-- ============================================
-- ONBOARDING DEFAULT TEMPLATE FOR ALL TENANTS
-- ============================================
INSERT INTO onboarding_items (
    tenant_id,
    code,
    title,
    description,
    category,
    is_required,
    sort_order
)
SELECT
    t.id,
    seed.code,
    seed.title,
    seed.description,
    seed.category,
    seed.is_required,
    seed.sort_order
FROM tenants t
CROSS JOIN (
    VALUES
        ('company_profile', 'Lengkapi Profil Perusahaan', 'Isi data legal, alamat, dan kontak utama tenant.', 'workspace', true, 10),
        ('invite_core_team', 'Undang Tim Inti', 'Tambahkan owner/admin/operator utama untuk operasional harian.', 'team', true, 20),
        ('define_governance', 'Atur Governance Dasar', 'Review role, permissions, dan branch agar akses terstruktur.', 'governance', true, 30),
        ('seed_inventory', 'Input Produk Awal', 'Masukkan SKU prioritas agar dashboard inventory aktif.', 'inventory', true, 40),
        ('first_invoice', 'Buat Invoice Pertama', 'Uji alur invoicing end-to-end dengan data customer contoh.', 'billing', true, 50),
        ('qbr_baseline', 'Set Baseline QBR', 'Buat siklus QBR pertama dan tetapkan target utama kuartal ini.', 'qbr', false, 60)
) AS seed(code, title, description, category, is_required, sort_order)
ON CONFLICT (tenant_id, code) DO NOTHING;
