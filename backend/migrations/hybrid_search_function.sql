-- MEXAR - Hybrid Search Function for Supabase
-- Combines semantic (vector) and keyword (full-text) search using Reciprocal Rank Fusion (RRF)

CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(384),
    query_text text,
    match_agent_id integer,
    match_count integer
)
RETURNS TABLE (
    id integer,
    agent_id integer,
    content text,
    source text,
    chunk_index integer,
    section_title text,
    created_at timestamp with time zone,
    rrf_score real
)
LANGUAGE plpgsql
AS $$
DECLARE
    semantic_weight real := 0.6;
    keyword_weight real := 0.4;
    k_constant real := 60.0;
BEGIN
    RETURN QUERY
    WITH semantic_search AS (
        SELECT
            dc.id,
            dc.agent_id,
            dc.content,
            dc.source,
            dc.chunk_index,
            dc.section_title,
            dc.created_at,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) AS rank_num
        FROM document_chunks dc
        WHERE dc.agent_id = match_agent_id
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    keyword_search AS (
        SELECT
            dc.id,
            dc.agent_id,
            dc.content,
            dc.source,
            dc.chunk_index,
            dc.section_title,
            dc.created_at,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.content_tsvector, plainto_tsquery('english', query_text)) DESC) AS rank_num
        FROM document_chunks dc
        WHERE dc.agent_id = match_agent_id
          AND dc.content_tsvector @@ plainto_tsquery('english', query_text)
        ORDER BY ts_rank_cd(dc.content_tsvector, plainto_tsquery('english', query_text)) DESC
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT 
            COALESCE(s.id, k.id) AS id,
            COALESCE(s.agent_id, k.agent_id) AS agent_id,
            COALESCE(s.content, k.content) AS content,
            COALESCE(s.source, k.source) AS source,
            COALESCE(s.chunk_index, k.chunk_index) AS chunk_index,
            COALESCE(s.section_title, k.section_title) AS section_title,
            COALESCE(s.created_at, k.created_at) AS created_at,
            (
                COALESCE(semantic_weight / (k_constant + s.rank_num::real), 0.0) +
                COALESCE(keyword_weight / (k_constant + k.rank_num::real), 0.0)
            ) AS rrf_score
        FROM semantic_search s
        FULL OUTER JOIN keyword_search k ON s.id = k.id
    )
    SELECT 
        c.id,
        c.agent_id,
        c.content,
        c.source,
        c.chunk_index,
        c.section_title,
        c.created_at,
        c.rrf_score::real
    FROM combined c
    ORDER BY c.rrf_score DESC
    LIMIT match_count;
END;
$$;

-- Add index on content_tsvector for better keyword search performance
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_tsvector 
ON document_chunks USING GIN(content_tsvector);

-- Add index on agent_id for filtering
CREATE INDEX IF NOT EXISTS idx_document_chunks_agent_id 
ON document_chunks(agent_id);

-- Add index on embedding for vector similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
ON document_chunks USING ivfflat(embedding vector_cosine_ops)
WITH (lists = 100);

COMMENT ON FUNCTION hybrid_search IS 'Combines semantic (vector) and keyword (full-text) search using Reciprocal Rank Fusion';
