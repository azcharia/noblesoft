-- ============================================
-- NOBLESOFT CLEAN DATABASE SETUP (OPEN SOURCE)
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
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'enterprise',
    is_active BOOLEAN DEFAULT true,
    max_users INTEGER DEFAULT 1000,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TENANT AI SETTINGS (BYOK Support)
-- ============================================
CREATE TABLE tenant_ai_settings (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    api_key VARCHAR(255),
    base_url VARCHAR(512),
    model_name VARCHAR(100) DEFAULT 'llama-3.1-8b-instant',
    temperature DECIMAL(3, 2) DEFAULT 0.2,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- USERS TABLE (linked to Supabase Auth)
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'owner' CHECK (role IN ('owner', 'admin', 'member')),
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
    low_stock_threshold INTEGER DEFAULT 5,
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
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_ai_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_embeddings ENABLE ROW LEVEL SECURITY;

-- Helper function to get current user's tenant_id from JWT
CREATE OR REPLACE FUNCTION public.get_user_tenant_id()
RETURNS UUID AS $$
    SELECT tenant_id FROM public.users WHERE id = auth.uid();
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- TENANTS: Users can only see their own tenant
CREATE POLICY tenant_isolation_policy ON tenants
    FOR ALL USING (id = public.get_user_tenant_id());

-- AI SETTINGS: Tenant isolation
CREATE POLICY ai_settings_isolation_policy ON tenant_ai_settings
    FOR ALL USING (tenant_id = public.get_user_tenant_id());

-- USERS: Users can only see users in their tenant
CREATE POLICY users_isolation_policy ON users
    FOR ALL USING (tenant_id = public.get_user_tenant_id());

-- PRODUCTS: Tenant isolation
CREATE POLICY products_isolation_policy ON products
    FOR ALL USING (tenant_id = public.get_user_tenant_id());

-- INVOICES: Tenant isolation
CREATE POLICY invoices_isolation_policy ON invoices
    FOR ALL USING (tenant_id = public.get_user_tenant_id());

-- INVOICE_ITEMS: Access through parent invoice
CREATE POLICY invoice_items_isolation_policy ON invoice_items
    FOR ALL USING (
        invoice_id IN (
            SELECT id FROM invoices WHERE tenant_id = public.get_user_tenant_id()
        )
    );

-- DOCUMENT_EMBEDDINGS: Tenant isolation
CREATE POLICY embeddings_isolation_policy ON document_embeddings
    FOR ALL USING (tenant_id = public.get_user_tenant_id());

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
