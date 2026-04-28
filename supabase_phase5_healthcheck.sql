-- ============================================
-- NOBLESOFT PHASE 5 HEALTHCHECK (READ-ONLY)
-- Run this script in Supabase SQL Editor for:
-- 1) staging environment
-- 2) production environment
-- Then compare outputs for drift detection.
-- ============================================
-- Output schema:
-- section | check_id | severity | status | details | remediation_hint
--
-- Status values:
-- - PASS: requirement met
-- - WARN: non-blocking issue found
-- - FAIL: blocking issue found
--
-- NOTE: This script contains SELECT-only statements.

WITH checks AS (
    -- SECTION 01: Extensions
    SELECT
        '01_extensions'::text AS section,
        'EXT-001'::text AS check_id,
        'critical'::text AS severity,
        CASE
            WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') THEN 'PASS'
            ELSE 'FAIL'
        END AS status,
        'Extension uuid-ossp is required for UUID generation.'::text AS details,
        'Run: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'::text AS remediation_hint

    UNION ALL

    SELECT
        '01_extensions',
        'EXT-002',
        'high',
        CASE
            WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN 'PASS'
            ELSE 'WARN'
        END,
        'Extension vector (pgvector) supports embeddings/search features.',
        'Run: CREATE EXTENSION IF NOT EXISTS vector;'

    -- SECTION 02: Helper functions
    UNION ALL

    SELECT
        '02_functions',
        'FUN-001',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM pg_proc
                WHERE proname = 'get_user_tenant_id'
                  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Function public.get_user_tenant_id() is required by tenant RLS policies.',
        'Re-run supabase_setup.sql (or create function manually).'

    UNION ALL

    SELECT
        '02_functions',
        'FUN-002',
        'high',
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM pg_proc
                WHERE proname = 'update_updated_at_column'
                  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ) THEN 'PASS'
            ELSE 'WARN'
        END,
        'Function public.update_updated_at_column() is used by updated_at triggers.',
        'Re-run supabase_setup.sql to restore trigger helper function.'

    -- SECTION 03: Prerequisite governance tables
    UNION ALL

    SELECT
        '03_prereq_tables',
        'PRE-001',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'roles'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.roles is required for permission bindings.',
        'Apply supabase_phase4_governance.sql (or base schema with governance tables).'

    UNION ALL

    SELECT
        '03_prereq_tables',
        'PRE-002',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'permissions'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.permissions stores authorization codes.',
        'Apply supabase_phase4_governance.sql (or base schema with governance tables).'

    UNION ALL

    SELECT
        '03_prereq_tables',
        'PRE-003',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'role_permissions'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.role_permissions stores role-permission mappings.',
        'Apply supabase_phase4_governance.sql (or base schema with governance tables).'

    -- SECTION 04: Phase 5 table existence
    UNION ALL

    SELECT
        '04_phase5_tables',
        'P5T-001',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'onboarding_items'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.onboarding_items exists.',
        'Apply supabase_phase5_enterprise_engagement.sql.'

    UNION ALL

    SELECT
        '04_phase5_tables',
        'P5T-002',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'support_tickets'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.support_tickets exists.',
        'Apply supabase_phase5_enterprise_engagement.sql.'

    UNION ALL

    SELECT
        '04_phase5_tables',
        'P5T-003',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'support_ticket_comments'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.support_ticket_comments exists.',
        'Apply supabase_phase5_enterprise_engagement.sql.'

    UNION ALL

    SELECT
        '04_phase5_tables',
        'P5T-004',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'qbr_cycles'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.qbr_cycles exists.',
        'Apply supabase_phase5_enterprise_engagement.sql.'

    UNION ALL

    SELECT
        '04_phase5_tables',
        'P5T-005',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'qbr_goals'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Table public.qbr_goals exists.',
        'Apply supabase_phase5_enterprise_engagement.sql.'

    -- SECTION 05: RLS enabled checks
    UNION ALL

    SELECT
        '05_rls_enabled',
        'RLS-001',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename = 'onboarding_items'
                  AND rowsecurity
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'RLS enabled on onboarding_items.',
        'Run: ALTER TABLE onboarding_items ENABLE ROW LEVEL SECURITY;'

    UNION ALL

    SELECT
        '05_rls_enabled',
        'RLS-002',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename = 'support_tickets'
                  AND rowsecurity
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'RLS enabled on support_tickets.',
        'Run: ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;'

    UNION ALL

    SELECT
        '05_rls_enabled',
        'RLS-003',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename = 'support_ticket_comments'
                  AND rowsecurity
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'RLS enabled on support_ticket_comments.',
        'Run: ALTER TABLE support_ticket_comments ENABLE ROW LEVEL SECURITY;'

    UNION ALL

    SELECT
        '05_rls_enabled',
        'RLS-004',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename = 'qbr_cycles'
                  AND rowsecurity
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'RLS enabled on qbr_cycles.',
        'Run: ALTER TABLE qbr_cycles ENABLE ROW LEVEL SECURITY;'

    UNION ALL

    SELECT
        '05_rls_enabled',
        'RLS-005',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename = 'qbr_goals'
                  AND rowsecurity
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'RLS enabled on qbr_goals.',
        'Run: ALTER TABLE qbr_goals ENABLE ROW LEVEL SECURITY;'

    -- SECTION 06: Phase 5 policy checks
    UNION ALL

    SELECT
        '06_phase5_policies',
        'POL-001',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'onboarding_items'
                  AND policyname = 'onboarding_items_isolation_policy'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Policy onboarding_items_isolation_policy exists.',
        'Re-run supabase_phase5_enterprise_engagement.sql policy section.'

    UNION ALL

    SELECT
        '06_phase5_policies',
        'POL-002',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'support_tickets'
                  AND policyname = 'support_tickets_isolation_policy'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Policy support_tickets_isolation_policy exists.',
        'Re-run supabase_phase5_enterprise_engagement.sql policy section.'

    UNION ALL

    SELECT
        '06_phase5_policies',
        'POL-003',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'support_ticket_comments'
                  AND policyname = 'support_ticket_comments_isolation_policy'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Policy support_ticket_comments_isolation_policy exists.',
        'Re-run supabase_phase5_enterprise_engagement.sql policy section.'

    UNION ALL

    SELECT
        '06_phase5_policies',
        'POL-004',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'qbr_cycles'
                  AND policyname = 'qbr_cycles_isolation_policy'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Policy qbr_cycles_isolation_policy exists.',
        'Re-run supabase_phase5_enterprise_engagement.sql policy section.'

    UNION ALL

    SELECT
        '06_phase5_policies',
        'POL-005',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'qbr_goals'
                  AND policyname = 'qbr_goals_isolation_policy'
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'Policy qbr_goals_isolation_policy exists.',
        'Re-run supabase_phase5_enterprise_engagement.sql policy section.'

    -- SECTION 07: Permission seeds
    UNION ALL

    SELECT
        '07_permission_seeds',
        'PER-001',
        'critical',
        CASE WHEN EXISTS (SELECT 1 FROM permissions WHERE code = 'onboarding.read') THEN 'PASS' ELSE 'FAIL' END,
        'Permission onboarding.read exists.',
        'Re-run permission seed section in phase5 migration.'

    UNION ALL

    SELECT
        '07_permission_seeds',
        'PER-002',
        'critical',
        CASE WHEN EXISTS (SELECT 1 FROM permissions WHERE code = 'onboarding.write') THEN 'PASS' ELSE 'FAIL' END,
        'Permission onboarding.write exists.',
        'Re-run permission seed section in phase5 migration.'

    UNION ALL

    SELECT
        '07_permission_seeds',
        'PER-003',
        'critical',
        CASE WHEN EXISTS (SELECT 1 FROM permissions WHERE code = 'support.read') THEN 'PASS' ELSE 'FAIL' END,
        'Permission support.read exists.',
        'Re-run permission seed section in phase5 migration.'

    UNION ALL

    SELECT
        '07_permission_seeds',
        'PER-004',
        'critical',
        CASE WHEN EXISTS (SELECT 1 FROM permissions WHERE code = 'support.write') THEN 'PASS' ELSE 'FAIL' END,
        'Permission support.write exists.',
        'Re-run permission seed section in phase5 migration.'

    UNION ALL

    SELECT
        '07_permission_seeds',
        'PER-005',
        'critical',
        CASE WHEN EXISTS (SELECT 1 FROM permissions WHERE code = 'support.assign') THEN 'PASS' ELSE 'FAIL' END,
        'Permission support.assign exists.',
        'Re-run permission seed section in phase5 migration.'

    UNION ALL

    SELECT
        '07_permission_seeds',
        'PER-006',
        'critical',
        CASE WHEN EXISTS (SELECT 1 FROM permissions WHERE code = 'qbr.read') THEN 'PASS' ELSE 'FAIL' END,
        'Permission qbr.read exists.',
        'Re-run permission seed section in phase5 migration.'

    UNION ALL

    SELECT
        '07_permission_seeds',
        'PER-007',
        'critical',
        CASE WHEN EXISTS (SELECT 1 FROM permissions WHERE code = 'qbr.write') THEN 'PASS' ELSE 'FAIL' END,
        'Permission qbr.write exists.',
        'Re-run permission seed section in phase5 migration.'

    -- SECTION 08: Role-permission binding check
    UNION ALL

    SELECT
        '08_role_bindings',
        'BND-001',
        'critical',
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE p.code = 'support.assign'
                  AND r.code IN ('owner', 'admin')
            ) THEN 'PASS'
            ELSE 'FAIL'
        END,
        'support.assign is bound to owner/admin roles.',
        'Re-run role_permissions seed section in phase5 migration.'
),
summary AS (
    SELECT
        '99_summary'::text AS section,
        'SUM-001'::text AS check_id,
        'critical'::text AS severity,
        CASE
            WHEN COUNT(*) FILTER (WHERE severity = 'critical' AND status = 'FAIL') > 0 THEN 'NOT_READY'
            WHEN COUNT(*) FILTER (WHERE status = 'WARN') > 0 THEN 'READY_WITH_WARNINGS'
            ELSE 'READY'
        END::text AS status,
        (
            'total=' || COUNT(*)::text ||
            ', pass=' || COUNT(*) FILTER (WHERE status = 'PASS')::text ||
            ', warn=' || COUNT(*) FILTER (WHERE status = 'WARN')::text ||
            ', fail=' || COUNT(*) FILTER (WHERE status = 'FAIL')::text ||
            ', critical_fail=' || COUNT(*) FILTER (WHERE severity = 'critical' AND status = 'FAIL')::text
        )::text AS details,
        'Resolve FAIL rows before audit sign-off.'::text AS remediation_hint
    FROM checks
)
SELECT section, check_id, severity, status, details, remediation_hint
FROM checks
UNION ALL
SELECT section, check_id, severity, status, details, remediation_hint
FROM summary
ORDER BY section, check_id;
