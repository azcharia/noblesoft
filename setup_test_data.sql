-- Setup Test Data for NobleSoft MVP
-- Run this AFTER creating a user in Supabase Authentication UI

-- Step 1: Create a test tenant
INSERT INTO tenants (company_name, subscription_tier, is_active, max_users)
VALUES (
  'PT Contoh Usaha',
  'pro',
  true,
  10
) RETURNING id;

-- Copy the tenant ID from above, then run this:
-- Step 2: Link your user to the tenant (REPLACE both UUIDs below)
INSERT INTO users (id, tenant_id, email, full_name, role, is_active)
VALUES (
  'PASTE_USER_UUID_HERE',   -- Replace with user UUID from Supabase Auth
  'PASTE_TENANT_ID_HERE',   -- Replace with tenant id from step 1
  'test@noblesoft.com',     -- Replace with your test user email
  'Test User',
  'owner',
  true
);

-- Step 3: Add some sample products
INSERT INTO products (tenant_id, name, sku, description, category, unit_price, stock_quantity, unit_of_measure)
VALUES 
  ('PASTE_TENANT_ID_HERE', 'Kopi Arabica Premium', 'KAP-001', 'Kopi arabica pilihan dari dataran tinggi', 'Beverage', 85000, 150, 'kg'),
  ('PASTE_TENANT_ID_HERE', 'Teh Hijau Organik', 'THO-002', 'Teh hijau organik tanpa pestisida', 'Beverage', 45000, 200, 'kg'),
  ('PASTE_TENANT_ID_HERE', 'Madu Hutan Asli', 'MHA-003', 'Madu murni dari hutan Kalimantan', 'Food', 125000, 80, 'bottle');

-- Step 4: Add a sample invoice
INSERT INTO invoices (tenant_id, invoice_number, customer_name, customer_email, customer_phone, issue_date, due_date, subtotal, tax_amount, total_amount, payment_status, notes)
VALUES (
  'PASTE_TENANT_ID_HERE',
  'INV-2024-001',
  'Toko Berkah Jaya',
  'berkah@example.com',
  '+62812345678',
  '2024-03-01',
  '2024-03-15',
  340000,
  37400,
  377400,
  'paid',
  'Pesanan rutin bulanan'
) RETURNING id;

-- Step 5: Add invoice items (REPLACE invoice_id with the ID from step 4)
INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price, subtotal)
SELECT 
  'PASTE_INVOICE_ID_HERE',  -- Replace with invoice id from step 4
  p.id,
  CASE 
    WHEN p.sku = 'KAP-001' THEN 2
    WHEN p.sku = 'THO-002' THEN 3
    ELSE 1
  END,
  p.unit_price,
  CASE 
    WHEN p.sku = 'KAP-001' THEN 2 * p.unit_price
    WHEN p.sku = 'THO-002' THEN 3 * p.unit_price
    ELSE p.unit_price
  END
FROM products p
WHERE p.sku IN ('KAP-001', 'THO-002')
  AND p.tenant_id = 'PASTE_TENANT_ID_HERE';
