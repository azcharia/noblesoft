-- ============================================
-- NOBLESOFT PHASE 4 GOVERNANCE MIGRATION
-- Additive and idempotent migration for existing environments
-- ============================================

-- Prerequisite extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS roles (
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

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(150) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS branches (
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

CREATE TABLE IF NOT EXISTS audit_logs (
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

-- ============================================
-- COLUMN EXTENSIONS
-- ============================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id UUID REFERENCES roles(id) ON DELETE SET NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE products ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE document_embeddings ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id) ON DELETE SET NULL;

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_roles_tenant ON roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_roles_tenant_active ON roles(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_branches_tenant ON branches(tenant_id);
CREATE INDEX IF NOT EXISTS idx_branches_tenant_active ON branches(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_created_desc ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_branch_id ON users(branch_id);
CREATE INDEX IF NOT EXISTS idx_products_branch_id ON products(branch_id);
CREATE INDEX IF NOT EXISTS idx_invoices_branch_id ON invoices(branch_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_branch_id ON document_embeddings(branch_id);

-- ============================================
-- RLS
-- ============================================

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS roles_read_policy ON roles;
CREATE POLICY roles_read_policy ON roles
    FOR SELECT
    USING (tenant_id = public.get_user_tenant_id());

DROP POLICY IF EXISTS roles_write_policy ON roles;
CREATE POLICY roles_write_policy ON roles
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id())
    WITH CHECK (tenant_id = public.get_user_tenant_id());

DROP POLICY IF EXISTS permissions_read_policy ON permissions;
CREATE POLICY permissions_read_policy ON permissions
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS role_permissions_read_policy ON role_permissions;
CREATE POLICY role_permissions_read_policy ON role_permissions
    FOR SELECT
    USING (
        role_id IN (
            SELECT id FROM roles WHERE tenant_id = public.get_user_tenant_id()
        )
    );

DROP POLICY IF EXISTS role_permissions_write_policy ON role_permissions;
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

DROP POLICY IF EXISTS branches_isolation_policy ON branches;
CREATE POLICY branches_isolation_policy ON branches
    FOR ALL
    USING (tenant_id = public.get_user_tenant_id());

DROP POLICY IF EXISTS audit_logs_isolation_policy ON audit_logs;
CREATE POLICY audit_logs_isolation_policy ON audit_logs
    FOR SELECT
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
        DROP TRIGGER IF EXISTS update_roles_updated_at ON roles;
        CREATE TRIGGER update_roles_updated_at
        BEFORE UPDATE ON roles
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS update_branches_updated_at ON branches;
        CREATE TRIGGER update_branches_updated_at
        BEFORE UPDATE ON branches
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

-- ============================================
-- SEED PERMISSIONS
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

-- ============================================
-- ROLE AND BRANCH BACKFILL
-- ============================================

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
-- AUDIT FUNCTIONS + TRIGGERS
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

DROP TRIGGER IF EXISTS audit_users_changes ON users;
CREATE TRIGGER audit_users_changes
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

DROP TRIGGER IF EXISTS audit_products_changes ON products;
CREATE TRIGGER audit_products_changes
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

DROP TRIGGER IF EXISTS audit_invoices_changes ON invoices;
CREATE TRIGGER audit_invoices_changes
AFTER INSERT OR UPDATE OR DELETE ON invoices
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

DROP TRIGGER IF EXISTS audit_branches_changes ON branches;
CREATE TRIGGER audit_branches_changes
AFTER INSERT OR UPDATE OR DELETE ON branches
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

DROP TRIGGER IF EXISTS audit_roles_changes ON roles;
CREATE TRIGGER audit_roles_changes
AFTER INSERT OR UPDATE OR DELETE ON roles
FOR EACH ROW EXECUTE FUNCTION public.capture_audit_log();

DROP TRIGGER IF EXISTS audit_role_permissions_changes ON role_permissions;
CREATE TRIGGER audit_role_permissions_changes
AFTER INSERT OR UPDATE OR DELETE ON role_permissions
FOR EACH ROW EXECUTE FUNCTION public.capture_role_permissions_audit_log();
