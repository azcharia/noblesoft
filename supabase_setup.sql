-- ============================================
-- NOBLESOFT DATABASE SETUP
-- Run this entire script in Supabase SQL Editor
-- ============================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- TENANTS TABLE (Multi-tenant root)
-- ============================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'trial' 
        CHECK (subscription_tier IN ('trial', 'basic', 'pro', 'enterprise')),
    trial_start_date TIMESTAMPTZ,
    trial_end_date TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    max_users INTEGER DEFAULT 5,
    payment_gateway_customer_id VARCHAR(255),
    billing_period VARCHAR(20) DEFAULT 'monthly'
        CHECK (billing_period IN ('monthly', 'annual')),
    active_add_ons JSONB DEFAULT '[]'::jsonb,
    billing_start_date TIMESTAMPTZ,
    billing_end_date TIMESTAMPTZ,
    last_billing_event_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_tier ON tenants(subscription_tier);

-- ============================================
-- USERS TABLE (linked to Supabase Auth)
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================
-- PRODUCTS TABLE (Inventory)
-- ============================================
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sku VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    unit_price DECIMAL(15, 2) NOT NULL DEFAULT 0,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, sku)
);

CREATE INDEX idx_products_tenant ON products(tenant_id);
CREATE INDEX idx_products_sku ON products(tenant_id, sku);

-- ============================================
-- INVOICES TABLE
-- ============================================
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    issue_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE,
    subtotal DECIMAL(15, 2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0,
    payment_status VARCHAR(20) DEFAULT 'unpaid' 
        CHECK (payment_status IN ('unpaid', 'partial', 'paid', 'overdue')),
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, invoice_number)
);

CREATE INDEX idx_invoices_tenant ON invoices(tenant_id);
CREATE INDEX idx_invoices_status ON invoices(tenant_id, payment_status);

-- ============================================
-- INVOICE ITEMS TABLE
-- ============================================
CREATE TABLE invoice_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    description VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(15, 2) NOT NULL,
    line_total DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoice_items_invoice ON invoice_items(invoice_id);

-- ============================================
-- DOCUMENT EMBEDDINGS TABLE (RAG/Vector Store)
-- ============================================
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL 
        CHECK (document_type IN ('invoice', 'product', 'customer', 'general')),
    document_id UUID,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_vector ON document_embeddings 
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_embeddings_tenant ON document_embeddings(tenant_id);
CREATE INDEX idx_embeddings_type ON document_embeddings(tenant_id, document_type);

-- ============================================
-- BILLING EVENTS TABLE (Webhook idempotency + audit)
-- ============================================
CREATE TABLE billing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_id VARCHAR(255) NOT NULL UNIQUE,
    transaction_status VARCHAR(50) NOT NULL,
    updated_tier VARCHAR(20),
    billing_period VARCHAR(20),
    add_ons JSONB DEFAULT '[]'::jsonb,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_billing_events_tenant ON billing_events(tenant_id);
CREATE INDEX idx_billing_events_created_at ON billing_events(created_at DESC);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_events ENABLE ROW LEVEL SECURITY;

-- Helper function to get current user's tenant_id from JWT
-- Create in public schema instead of auth schema
CREATE OR REPLACE FUNCTION public.get_user_tenant_id()
RETURNS UUID AS $$
    SELECT tenant_id FROM public.users WHERE id = auth.uid();
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- TENANTS: Users can only see their own tenant
CREATE POLICY tenant_isolation_policy ON tenants
    FOR ALL
    USING (id = public.get_user_tenant_id());

-- USERS: Users can only see users in their tenant
CREATE POLICY users_isolation_policy ON users
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

-- PRODUCTS: Tenant isolation
CREATE POLICY products_isolation_policy ON products
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

-- INVOICES: Tenant isolation
CREATE POLICY invoices_isolation_policy ON invoices
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

-- INVOICE_ITEMS: Access through parent invoice
CREATE POLICY invoice_items_isolation_policy ON invoice_items
    FOR ALL
    USING (
        invoice_id IN (
            SELECT id FROM invoices WHERE tenant_id = public.get_user_tenant_id()
        )
    );

-- DOCUMENT_EMBEDDINGS: Tenant isolation
CREATE POLICY embeddings_isolation_policy ON document_embeddings
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

-- BILLING_EVENTS: Tenant isolation
CREATE POLICY billing_events_isolation_policy ON billing_events
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VECTOR SEARCH FUNCTION (RAG)
-- ============================================
-- IMPORTANT: vector(384) must match EMBEDDING_DIMENSION for
-- sentence-transformers/all-MiniLM-L6-v2
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_tenant_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    tenant_id uuid,
    document_type text,
    document_id uuid,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        document_embeddings.id,
        document_embeddings.tenant_id,
        document_embeddings.document_type::text,
        document_embeddings.document_id,
        document_embeddings.content,
        document_embeddings.metadata,
        1 - (document_embeddings.embedding <=> query_embedding) AS similarity
    FROM document_embeddings
    WHERE
        (filter_tenant_id IS NULL OR document_embeddings.tenant_id = filter_tenant_id)
        AND 1 - (document_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY document_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION match_documents TO authenticated;

-- ============================================
-- GOVERNANCE TABLES (Roles, Permissions, Branches, Audit)
-- ============================================

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, code),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_roles_tenant ON roles(tenant_id);
CREATE INDEX idx_roles_tenant_active ON roles(tenant_id, is_active);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(150) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_permissions_resource ON permissions(resource);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);

CREATE TABLE branches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    manager_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

CREATE INDEX idx_branches_tenant ON branches(tenant_id);
CREATE INDEX idx_branches_tenant_active ON branches(tenant_id, is_active);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_tenant_created_desc ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- ============================================
-- GOVERNANCE COLUMN EXTENSIONS
-- ============================================

ALTER TABLE users
    ADD COLUMN role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    ADD COLUMN branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;

ALTER TABLE products
    ADD COLUMN branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;

ALTER TABLE invoices
    ADD COLUMN branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;

ALTER TABLE document_embeddings
    ADD COLUMN branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;

CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_branch_id ON users(branch_id);
CREATE INDEX idx_products_branch_id ON products(branch_id);
CREATE INDEX idx_invoices_branch_id ON invoices(branch_id);
CREATE INDEX idx_document_embeddings_branch_id ON document_embeddings(branch_id);

-- ============================================
-- GOVERNANCE RLS POLICIES
-- ============================================

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY roles_read_policy ON roles
    FOR SELECT
    USING (tenant_id = public.get_user_tenant_id());

CREATE POLICY roles_write_policy ON roles
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id())
    WITH CHECK (tenant_id = public.get_user_tenant_id());

CREATE POLICY permissions_read_policy ON permissions
    FOR SELECT
    USING (true);

CREATE POLICY role_permissions_read_policy ON role_permissions
    FOR SELECT
    USING (
        role_id IN (
            SELECT id FROM roles WHERE tenant_id = public.get_user_tenant_id()
        )
    );

CREATE POLICY role_permissions_write_policy ON role_permissions
    FOR ALL
    USING (
        role_id IN (
            SELECT id FROM roles WHERE tenant_id = public.get_user_tenant_id()
        )
    )
    WITH CHECK (
        role_id IN (
            SELECT id FROM roles WHERE tenant_id = public.get_user_tenant_id()
        )
    );

CREATE POLICY branches_isolation_policy ON branches
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

CREATE POLICY audit_logs_isolation_policy ON audit_logs
    FOR SELECT
    USING (tenant_id = public.get_user_tenant_id());

-- ============================================
-- GOVERNANCE UPDATED_AT TRIGGERS
-- ============================================

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_branches_updated_at BEFORE UPDATE ON branches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- GOVERNANCE SEED DATA
-- ============================================

INSERT INTO permissions (code, name, resource, action, description)
VALUES
    ('users.read', 'Read Users', 'users', 'read', 'List and inspect tenant users'),
    ('users.invite', 'Invite Users', 'users', 'invite', 'Invite users to tenant workspace'),
    ('users.status', 'Manage User Status', 'users', 'status', 'Deactivate or reactivate tenant users'),
    ('roles.read', 'Read Roles', 'roles', 'read', 'View role configuration'),
    ('roles.write', 'Write Roles', 'roles', 'write', 'Create, edit, and delete custom roles'),
    ('permissions.read', 'Read Permissions', 'permissions', 'read', 'View permission matrix'),
    ('permissions.write', 'Write Permissions', 'permissions', 'write', 'Update role permission matrix'),
    ('branches.read', 'Read Branches', 'branches', 'read', 'View branch directory and assignments'),
    ('branches.write', 'Write Branches', 'branches', 'write', 'Create, edit, and deactivate branches'),
    ('audit.read', 'Read Audit Logs', 'audit_logs', 'read', 'View governance and operational audit logs'),
    ('products.read', 'Read Products', 'products', 'read', 'View inventory products'),
    ('products.write', 'Write Products', 'products', 'write', 'Create, update, and delete products'),
    ('invoices.read', 'Read Invoices', 'invoices', 'read', 'View invoices'),
    ('invoices.write', 'Write Invoices', 'invoices', 'write', 'Create, update, and delete invoices'),
    ('chat.use', 'Use AI Chat', 'chat', 'use', 'Access AI chat assistant')
ON CONFLICT (code) DO NOTHING;

INSERT INTO roles (tenant_id, code, name, description, is_system, is_active)
SELECT
    t.id,
    role_seed.code,
    role_seed.name,
    role_seed.description,
    true,
    true
FROM tenants t
CROSS JOIN (
    VALUES
        ('owner', 'Owner', 'Tenant owner with full governance access'),
        ('admin', 'Admin', 'Administrator with operational management access'),
        ('member', 'Member', 'Member with default operational read/write access')
) AS role_seed(code, name, description)
ON CONFLICT (tenant_id, code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON (
    (r.code = 'owner') OR
    (r.code = 'admin' AND p.code IN (
        'users.read', 'users.invite', 'users.status',
        'roles.read', 'permissions.read',
        'branches.read', 'branches.write',
        'audit.read',
        'products.read', 'products.write',
        'invoices.read', 'invoices.write',
        'chat.use'
    )) OR
    (r.code = 'member' AND p.code IN (
        'products.read', 'products.write',
        'invoices.read', 'invoices.write',
        'chat.use'
    ))
)
ON CONFLICT DO NOTHING;

INSERT INTO branches (tenant_id, code, name, location, is_active)
SELECT
    t.id,
    'hq',
    'Headquarters',
    t.company_name,
    true
FROM tenants t
ON CONFLICT (tenant_id, code) DO NOTHING;

UPDATE users u
SET role_id = r.id
FROM roles r
WHERE
    u.tenant_id = r.tenant_id
    AND lower(u.role) = r.code
    AND u.role_id IS NULL;

UPDATE users u
SET branch_id = b.id
FROM branches b
WHERE
    u.tenant_id = b.tenant_id
    AND b.code = 'hq'
    AND u.branch_id IS NULL;

UPDATE products p
SET branch_id = b.id
FROM branches b
WHERE
    p.tenant_id = b.tenant_id
    AND b.code = 'hq'
    AND p.branch_id IS NULL;

UPDATE invoices i
SET branch_id = b.id
FROM branches b
WHERE
    i.tenant_id = b.tenant_id
    AND b.code = 'hq'
    AND i.branch_id IS NULL;

UPDATE document_embeddings de
SET branch_id = b.id
FROM branches b
WHERE
    de.tenant_id = b.tenant_id
    AND b.code = 'hq'
    AND de.branch_id IS NULL;

-- ============================================
-- GOVERNANCE AUDIT TRIGGERS
-- ============================================

CREATE OR REPLACE FUNCTION public.capture_audit_log()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_tenant_id UUID;
    v_actor_id UUID;
    v_resource_id UUID;
BEGIN
    v_actor_id := auth.uid();

    IF TG_OP = 'DELETE' THEN
        v_tenant_id := OLD.tenant_id;
        v_resource_id := OLD.id;
    ELSE
        v_tenant_id := NEW.tenant_id;
        v_resource_id := NEW.id;
    END IF;

    INSERT INTO audit_logs (
        tenant_id,
        actor_user_id,
        action,
        resource_type,
        resource_id,
        old_values,
        new_values,
        metadata
    )
    VALUES (
        v_tenant_id,
        v_actor_id,
        LOWER(TG_OP),
        TG_TABLE_NAME,
        v_resource_id,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) ELSE NULL END,
        jsonb_build_object('schema', TG_TABLE_SCHEMA)
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.capture_role_permissions_audit_log()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_tenant_id UUID;
    v_actor_id UUID;
    v_role_id UUID;
BEGIN
    v_actor_id := auth.uid();
    v_role_id := COALESCE(NEW.role_id, OLD.role_id);

    SELECT tenant_id INTO v_tenant_id
    FROM roles
    WHERE id = v_role_id;

    IF v_tenant_id IS NULL THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;

    INSERT INTO audit_logs (
        tenant_id,
        actor_user_id,
        action,
        resource_type,
        resource_id,
        old_values,
        new_values,
        metadata
    )
    VALUES (
        v_tenant_id,
        v_actor_id,
        LOWER(TG_OP),
        'role_permissions',
        v_role_id,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) ELSE NULL END,
        jsonb_build_object('role_id', v_role_id)
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER audit_users_changes
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

CREATE TRIGGER audit_products_changes
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

CREATE TRIGGER audit_invoices_changes
AFTER INSERT OR UPDATE OR DELETE ON invoices
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

CREATE TRIGGER audit_branches_changes
AFTER INSERT OR UPDATE OR DELETE ON branches
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

CREATE TRIGGER audit_roles_changes
AFTER INSERT OR UPDATE OR DELETE ON roles
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

CREATE TRIGGER audit_role_permissions_changes
AFTER INSERT OR UPDATE OR DELETE ON role_permissions
FOR EACH ROW EXECUTE FUNCTION public.capture_role_permissions_audit_log();

