# MEXAR - Apply Hybrid Search Migration

## What This Does

This SQL script creates the `hybrid_search()` function in your Supabase database,
which combines semantic (vector) and keyword (full-text) search using
Reciprocal Rank Fusion (RRF) algorithm.

## Instructions

1. **Open Supabase Dashboard**
   - Go to: https://supabase.com/dashboard
   - Select your project: `xmfcidiwovxuihrkfzps`

2. **Navigate to SQL Editor**
   - Click "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Copy and Paste**
   - Open: `backend/migrations/hybrid_search_function.sql`
   - Copy ALL the contents
   - Paste into the Supabase SQL Editor

4. **Run the Migration**
   - Click "Run" button (or press Ctrl+Enter)
   - Wait for success message

5. **Verify**
   - Run this query to check:
   ```sql
   SELECT routine_name 
   FROM information_schema.routines 
   WHERE routine_name = 'hybrid_search';
   ```
   - Should return one row

## Recommended: Automated Python Migration Runner

Run all migrations automatically using your `DATABASE_URL` configured in `backend/.env`:

```bash
python scripts/run_migrations.py
```

## Alternative: Run manually via Supabase Dashboard


## What Gets Created

- **Function**: `hybrid_search(vector, text, integer, integer)` 
- **Indexes**: 
  - `idx_document_chunks_content_tsvector` (GIN index for full-text search)
  - `idx_document_chunks_agent_id` (B-tree index for filtering)
  - `idx_document_chunks_embedding` (IVFFlat index for vector search)

## Troubleshooting

**Error: "type vector does not exist"**
- Run: `CREATE EXTENSION IF NOT EXISTS vector;`
- Then retry the migration

**Error: "table document_chunks does not exist"**
- Restart your backend server to create tables
- Then retry the migration

---

**After running this migration**, your system will be ready for hybrid search!
