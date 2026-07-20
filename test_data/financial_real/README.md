# MEXAR Financial Corpus — Real Data Directory

This directory is populated by running:

```bash
export SEC_USER_AGENT="YourName your@email.com"
python backend/scripts/fetch_secedgar.py
```

**Contents (after fetch):**
- `<CIK>_<accession>.txt` — one plain-text file per 10-K section (MD&A or Risk Factors)
- `manifest.json` — CIK → accession → company → term → source URL mapping

**Target:** ~130 documents across 3 search terms (risk factors, MD&A, GAAP/IFRS standards)

See `MEXAR_Phase2_Dataset_Collection.md` for full instructions.
