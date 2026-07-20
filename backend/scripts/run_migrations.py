import os
import sys
import psycopg2
from dotenv import load_dotenv

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL environment variable is not set in backend/.env")

print("Connecting to database to apply migrations...")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

migrations = [
    (
        "Phase 1.1: Add domain_signature_weights & domain_entities columns to agents table",
        """
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS domain_signature_weights JSONB;
        ALTER TABLE agents ADD COLUMN IF NOT EXISTS domain_entities JSONB;
        COMMENT ON COLUMN agents.domain_signature_weights IS
          'TF-IDF lexical weights dict {term: weight} for domain signature (Section III-A, Eq. 1)';
        COMMENT ON COLUMN agents.domain_entities IS
          'NER-extracted domain entities list for domain signature (Section III-A)';
        """
    ),
    (
        "Phase 1.2: Switch vector index on document_chunks from IVFFlat to HNSW",
        """
        DROP INDEX IF EXISTS idx_document_chunks_embedding;
        DROP INDEX IF EXISTS chunks_embedding_idx;
        CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
        ON document_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        COMMENT ON INDEX idx_document_chunks_embedding_hnsw IS
          'HNSW index for cosine similarity search, m=16, ef_construction=64 (Section III-B)';
        """
    ),
    (
        "Add preferences column to users table",
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences JSON DEFAULT '{}';
        """
    )
]

for name, sql in migrations:
    print(f"\nApplying migration: {name}...")
    try:
        cur.execute(sql)
        print(f"[SUCCESS] {name}")
    except Exception as e:
        print(f"[ERROR] applying {name}: {e}")

print("\n--- Migration Verification ---")

# Verify agents table columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'agents';")
agent_cols = [r[0] for r in cur.fetchall()]
print("Agents columns:", agent_cols)
assert "domain_signature_weights" in agent_cols, "domain_signature_weights missing from agents!"
assert "domain_entities" in agent_cols, "domain_entities missing from agents!"
print("  [OK] agents.domain_signature_weights present")
print("  [OK] agents.domain_entities present")

# Verify document_chunks index
cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'document_chunks';")
chunk_indexes = cur.fetchall()
print("\nDocument Chunks indexes:")
hnsw_found = False
for idx_name, idx_def in chunk_indexes:
    print(f"  - {idx_name}: {idx_def}")
    if "hnsw" in idx_def.lower():
        hnsw_found = True

assert hnsw_found, "HNSW index missing on document_chunks!"
print("  [OK] HNSW index verified on document_chunks.embedding")

# Verify users preferences column
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';")
user_cols = [r[0] for r in cur.fetchall()]
assert "preferences" in user_cols, "preferences missing from users!"
print("  [OK] users.preferences column present")

cur.close()
conn.close()
print("\nALL MIGRATIONS COMPLETED AND VERIFIED SUCCESSFULLY!")
