# AI Company Finder v4.6

Generates a compact, structured company report for MJID.dk with:
- the 10 questions shown before each answer
- automatic logo fetch (Clearbit) below the company name
- initials + date in the header
- compact PDF layout

## Deploy (Streamlit Cloud)
1) Upload files to GitHub.
2) Set main file to `ai_company_finder_v4_6_full.py`.
3) Add a secret under Settings → Secrets:
   OPENAI_API_KEY = "sk-xxxxxxxx"
4) Deploy and test.
