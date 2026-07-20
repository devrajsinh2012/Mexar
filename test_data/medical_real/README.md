# MEXAR Medical Corpus — Real Data Directory

This directory is populated by running:

```bash
python backend/scripts/fetch_pubmed.py --email your_email@example.com
```

**Contents (after fetch):**
- `PMC<ID>.txt` — one plain-text file per PubMed Central OA article
- `manifest.json` — PMCID → title → subdomain → source URL mapping

**Target:** ~220 documents across 3 subdomains (cardiology, oncology, internal medicine)

See `MEXAR_Phase2_Dataset_Collection.md` for full instructions.
