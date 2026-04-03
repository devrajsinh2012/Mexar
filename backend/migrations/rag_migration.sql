-- ============================================
-- MEXAR RAG Migration Script
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. Enable pgvector extension (if not already)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Clear existing chunks (required due to dimension change)
DELETE FROM document_chunks;

-- 3. Alter embedding dimension: 384 → 1024
ALTER TABLE document_chunks 
ALTER COLUMN embedding TYPE vector(1024);

-- 4. Add tsvector column for keyword search
ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS content_tsvector TSVECTOR;

-- 5. Add chunk metadata columns
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS chunk_index INTEGER,
ADD COLUMN IF NOT EXISTS section_title TEXT,
ADD COLUMN IF NOT EXISTS token_count INTEGER;

-- 6. Create HNSW index for fast cosine similarity
DROP INDEX IF EXISTS chunks_embedding_idx;
DROP INDEX IF EXISTS chunks_embedding_hnsw;
CREATE INDEX chunks_embedding_hnsw 
ON document_chunks USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- 7. Create GIN index for full-text search
CREATE INDEX IF NOT EXISTS chunks_content_gin 
ON document_chunks USING GIN (content_tsvector);

-- 8. Create trigger to auto-update tsvector
CREATE OR REPLACE FUNCTION update_tsvector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_tsvector := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tsvector_update ON document_chunks;
CREATE TRIGGER tsvector_update
BEFORE INSERT OR UPDATE ON document_chunks
FOR EACH ROW EXECUTE FUNCTION update_tsvector();

-- 9. Add agent metadata columns for full Supabase storage
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS knowledge_graph_json JSONB,
ADD COLUMN IF NOT EXISTS domain_signature JSONB,
ADD COLUMN IF NOT EXISTS prompt_analysis JSONB,
ADD COLUMN IF NOT EXISTS compilation_stats JSONB,
ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0;

-- 10. Update existing tsvector data
UPDATE document_chunks 
SET content_tsvector = to_tsvector('english', content)
WHERE content_tsvector IS NULL;

-- 11. Create hybrid search function
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1024),
    query_text text,
    target_agent_id integer,
    match_count integer DEFAULT 20
)
RETURNS TABLE (
    id integer,
    content text,
    source text,
    semantic_rank integer,
    keyword_rank integer,
    rrf_score float
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic AS (
        SELECT dc.id, dc.content, dc.source,
               ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding)::integer as rank
        FROM document_chunks dc
        WHERE dc.agent_id = target_agent_id
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count
    ),
    keyword AS (
        SELECT dc.id, dc.content, dc.source,
               ROW_NUMBER() OVER (ORDER BY ts_rank(dc.content_tsvector, plainto_tsquery('english', query_text)) DESC)::integer as rank
        FROM document_chunks dc
        WHERE dc.agent_id = target_agent_id
          AND dc.content_tsvector @@ plainto_tsquery('english', query_text)
        LIMIT match_count
    )
    SELECT 
        COALESCE(s.id, k.id) as id,
        COALESCE(s.content, k.content) as content,
        COALESCE(s.source, k.source) as source,
        s.rank as semantic_rank,
        k.rank as keyword_rank,
        (COALESCE(1.0/(60 + s.rank), 0) + COALESCE(1.0/(60 + k.rank), 0))::float as rrf_score
    FROM semantic s
    FULL OUTER JOIN keyword k ON s.id = k.id
    ORDER BY rrf_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Done! Verify with:
-- SELECT * FROM pg_indexes WHERE tablename = 'document_chunks';
