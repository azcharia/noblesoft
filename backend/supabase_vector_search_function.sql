-- ============================================
-- Supabase Vector Similarity Search Function
-- Run this in your Supabase SQL Editor
-- ============================================

-- Function to match documents using vector similarity (tenant-scoped)
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
        -- Tenant filtering (CRITICAL for multi-tenancy)
        (filter_tenant_id IS NULL OR document_embeddings.tenant_id = filter_tenant_id)
        -- Similarity threshold
        AND 1 - (document_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY document_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_documents TO authenticated;

-- Example usage:
-- SELECT * FROM match_documents(
--     query_embedding := '[0.1, 0.2, ...]'::vector,
--     match_threshold := 0.7,
--     match_count := 5,
--     filter_tenant_id := '123e4567-e89b-12d3-a456-426614174000'::uuid
-- );
