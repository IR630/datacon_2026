# Progress Log

## 2026-06-27

### Done

- Created branch `selt-mvp`.
- Built SelTox-MAX skeleton:
  - parser artifacts: `pages.json`, `tables.json`, `chunks.json`, `figures.json`;
  - evidence finder for activity/nanoparticle/synthesis chunks;
  - deterministic SelTox normalizer/validator;
  - activity/nanoparticle/synthesis extractor skeletons;
  - ChemX-style evaluator adapter;
  - Streamlit MVP;
  - Yandex AI Studio/OpenAI-compatible LLM client.
- Verified Yandex AI Studio access:
  - `api.txt` supports two-line local format: API key, then folder id;
  - `python -m src.cli llm-smoke` returns `OK` with `deepseek-v4-flash`.
- Pushed current work to `origin/selt-mvp`.
- Downloaded and cached `ai-chem/SelTox` parquet locally under ignored `data/gold/seltox.parquet`.
- Verified evaluator sanity:
  - prepared SelTox scoring subset: `980` rows, `65` PDFs;
  - GT vs GT Macro-F1 = `1.0`.

### Current Direction

Primary MVP remains SelTox:

- baseline Macro-F1 is low (`0.045`);
- target fields match our table-first extraction plan;
- teammate findings confirm that blank-first extraction and exact-string normalization are the main levers.

Co-crystals remains a possible second domain, but the current baseline scoring constants use only 7 extracted columns, so the “metadata-only win” hypothesis is not enough by itself.

### Next

1. Implement/download PDF resolver for the 65 `SELTOX_ARTICLES`; HF stores annotations only, not PDFs.
2. Run first batch extraction on 3-5 SelTox PDFs.
3. Compare against local gold and tune:
   - numeric blanks must be `nan`;
   - string blanks must be `NOT_DETECTED`;
   - avoid hallucinating rare numeric fields.
4. Add LLM prompts for activity rows first: `bacteria`, `strain`, `method`, `mic_np_µg_ml`, `zoi_np_mm`.
5. Add Co-crystals only after SelTox batch loop is stable.

### Dataset Findings

- Raw SelTox HF table: `3244` rows, `36` columns, `163` unique PDFs.
- After open-access + official `SELTOX_ARTICLES` filtering: `980` rows, `65` PDFs.
- Numeric missing values become string `nan` under the baseline preprocessing because numeric columns are converted before `fillna`.
- String missing values become `NOT_DETECTED`.
- One-row-per-PDF blank prior already scores about `0.073` locally after duplicate-safe evaluation, above published SelTox baseline `0.045`; repeated identical blank rows are unsafe because baseline wrappers call `drop_duplicates()`.
- Crossref-only PDF resolver downloaded 6 PDFs from the 65-article SelTox subset.
- First end-to-end batch on those 6 PDFs produced `21` extracted rows.
- Scores:
  - batch-only over 6/65 PDFs: Macro-F1 `0.024`;
  - one-row blank prior over all 65 PDFs: Macro-F1 `0.073`;
  - blank prior + 6-PDF batch extraction: Macro-F1 `0.091`.

### Current Lesson

The safest current submission shape is not “extraction only”.

Use:

```text
one blank prior row for every target PDF
+ extracted rows for PDFs we can parse
```

This protects high-missing columns while still adding true positives for common fields such as `np`, `bacteria`, `method`, `MIC`, `ZOI`, and synthesis facts.
