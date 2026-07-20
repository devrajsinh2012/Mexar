-- MEXAR Phase 1 - Architecture Fix 1.1
-- Adds domain_signature_weights and domain_entities columns to agents table.
--
-- domain_signature_weights: JSONB dict of {term: tfidf_weight} from TF-IDF lexical signature (Eq. 1)
-- domain_entities:          JSONB list of NER entity strings extracted from corpus (Section III-A)
--
-- Apply via Supabase SQL Editor (copy-paste and Run).
-- See backend/migrations/README.md for instructions.

ALTER TABLE agents ADD COLUMN IF NOT EXISTS domain_signature_weights JSONB;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS domain_entities JSONB;

COMMENT ON COLUMN agents.domain_signature_weights IS
  'TF-IDF lexical weights dict {term: weight} for domain signature (Section III-A, Eq. 1)';

COMMENT ON COLUMN agents.domain_entities IS
  'NER-extracted domain entities list for domain signature (Section III-A)';
