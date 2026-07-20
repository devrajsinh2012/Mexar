# MEXAR Legal Corpus — Real Data Directory

This directory is populated by running:

```bash
export COURTLISTENER_TOKEN=your_token_here
python backend/scripts/fetch_courtlistener.py
```

Get a free CourtListener API token at: https://www.courtlistener.com/sign-in/

**Contents (after fetch):**
- `case_<id>.txt` — one plain-text file per CourtListener opinion
- `manifest.json` — opinion ID → case name → subdomain → court → source URL mapping

**Target:** ~150 documents across 3 subdomains (contract law, intellectual property, corporate governance)

See `MEXAR_Phase2_Dataset_Collection.md` for full instructions.
