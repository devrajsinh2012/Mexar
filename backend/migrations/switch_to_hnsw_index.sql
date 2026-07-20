-- MEXAR Phase 1 - Architecture Fix 1.2
-- Switches the document_chunks embedding index from IVFFlat to HNSW.
-- Paper Section III-B explicitly claims HNSW indexing.
--
-- Pre-requisite: pgvector >= 0.5.0 required for HNSW.
-- Verify with: SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- If below 0.5.0, run: ALTER EXTENSION vector UPDATE;
--
-- Apply via Supabase SQL Editor (copy-paste and Run).
-- See backend/migrations/README.md for instructions.

-- Drop the old IVFFlat index created in hybrid_search_function.sql
DROP INDEX IF EXISTS idx_document_chunks_embedding;

-- Create HNSW index to match paper Section III-B
-- m=16: number of bi-directional links per node (connectivity)
-- ef_construction=64: size of dynamic candidate list during index construction (recall/speed trade-off)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_document_chunks_embedding_hnsw IS
  'HNSW index for cosine similarity search, m=16, ef_construction=64 (Section III-B)';

-- Verification query — run after applying to confirm:
-- SELECT indexdef FROM pg_indexes WHERE tablename = 'document_chunks';
-- Should show 'hnsw', not 'ivfflat'.
