-- ============================================
-- NOBLESOFT TEST DATA SETUP
-- Run this AFTER you create a user in Supabase Auth
-- ============================================

-- Step 1: Create a test tenant (Pro tier for full features)
INSERT INTO tenants (id, company_name, subscription_tier, is_active, max_users)
VALUES (
  '11111111-1111-1111-1111-111111111111',
  'PT Demo Indonesia',
  'pro',
  true,
  10
);

-- Step 2: Link the user to the tenant
INSERT INTO users (id, tenant_id, email, full_name, role, is_active)
VALUES (
  '08c24a16-9285-42db-b8dc-04f9ff283375',
  '11111111-1111-1111-1111-111111111111',
  'demo@noblesoft.com',
  'Demo User',
  'owner',
  true
);

-- Step 3: Add sample products
INSERT INTO products (tenant_id, sku, name, description, category, unit_price, stock_quantity, low_stock_threshold)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'LAPTOP-001', 'Laptop Dell XPS 13', 'Laptop premium untuk bisnis', 'Electronics', 15000000, 25, 5),
  ('11111111-1111-1111-1111-111111111111', 'MOUSE-001', 'Logitech MX Master 3', 'Mouse wireless ergonomis', 'Electronics', 1200000, 50, 10),
  ('11111111-1111-1111-1111-111111111111', 'DESK-001', 'Standing Desk Adjustable', 'Meja kerja adjustable', 'Furniture', 3500000, 15, 3),
  ('11111111-1111-1111-1111-111111111111', 'CHAIR-001', 'Herman Miller Aeron', 'Kursi kantor ergonomis', 'Furniture', 8500000, 10, 2),
  ('11111111-1111-1111-1111-111111111111', 'MONITOR-001', 'LG UltraWide 34"', 'Monitor ultrawide 34 inch', 'Electronics', 6500000, 20, 5);

-- Step 4: Add sample invoices
INSERT INTO invoices (tenant_id, invoice_number, customer_name, customer_email, customer_phone, issue_date, due_date, subtotal, tax_amount, total_amount, payment_status, notes)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'INV-2024-001', 'PT Maju Jaya', 'maju@example.com', '+628123456789', '2024-03-01', '2024-03-15', 30000000, 3300000, 33300000, 'paid', 'Pembelian laptop untuk kantor'),
  ('11111111-1111-1111-1111-111111111111', 'INV-2024-002', 'CV Berkah Sejahtera', 'berkah@example.com', '+628234567890', '2024-03-05', '2024-03-20', 12000000, 1320000, 13320000, 'unpaid', 'Setup kantor baru'),
  ('11111111-1111-1111-1111-111111111111', 'INV-2024-003', 'Toko Elektronik Jaya', 'jaya@example.com', '+628345678901', '2024-03-10', '2024-03-25', 6500000, 715000, 7215000, 'partial', 'Monitor untuk display toko');

-- Success! Now you can test the backend API
