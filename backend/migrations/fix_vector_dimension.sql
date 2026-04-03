-- MEXAR - Fix Vector Dimension Mismatch
-- The embedding model (bge-small-en-v1.5) outputs 384 dimensions
-- But the table was created with 1024 dimensions
-- This script fixes the mismatch

-- Step 1: Drop existing embedding column
ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding;

-- Step 2: Add new embedding column with correct dimensions (384)
ALTER TABLE document_chunks ADD COLUMN embedding vector(384);

-- Step 3: Create index for the new column
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
ON document_chunks USING ivfflat(embedding vector_cosine_ops)
WITH (lists = 100);

-- Verify the change
SELECT column_name, udt_name 
FROM information_schema.columns 
WHERE table_name = 'document_chunks' AND column_name = 'embedding';
