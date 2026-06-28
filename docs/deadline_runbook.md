# Deadline Runbook

## Current Best Local Result

- Domain: SelTox.
- Published single-agent baseline: Macro-F1 `0.045`.
- Current local submission: `data/predictions/seltox_submission_resolved.csv`.
- Current local score: Macro-F1 `0.172471`.
- Shape: calibrated prior rows for all `65` target PDFs plus `60` deterministic extracted rows from `12` locally resolved PDFs.
- Yandex AI Studio smoke test works with `deepseek-v4-flash`; token usage is visible in `llm-smoke`.

## Reproduce

```bash
python -m src.cli resolve-pdfs --domain seltox --start 0 --limit 65 --sleep 0.05 --out-dir data/pdfs --report data/cache/pdf_resolver_report_deadline.json
python -m src.cli batch-extract --pdf-dir data/pdfs --domain SelTox --out data/predictions/selt_batch_resolved.csv --work-dir data/predictions/per_pdf --parsed-dir data/parsed --top-k 8
python -m src.cli build-submission --domain seltox --extracted data/predictions/selt_batch_resolved.csv --out data/predictions/seltox_submission_resolved.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_resolved.csv --out data/predictions/seltox_submission_resolved_metrics.csv
python -m streamlit run app.py --server.port=8501 --server.address=localhost
```

## Demo Flow

1. Open Streamlit.
2. Show `Dataset run`: gold present, `65` target PDFs, local PDF count, current Macro-F1.
3. Click `Build` and `Evaluate` if live reproduction is needed.
4. Download `seltox_submission_resolved.csv`.
5. Open `Single PDF`, upload any article PDF, run `Parse`, `Evidence`, `Extract`.

## Notes For Teammates

- Do not commit `api.txt`, `.env`, or anything under `data/`; these are ignored local artifacts.
- Keep `deepseek-v4-flash` as default for quick paid checks.
- Avoid looping over `qwen3.6-35b-a3b` and `gpt-oss-120b` until response parsing is fixed.
- The fastest next score improvement is better PDF parsing and extraction, not changing the prior.
- Optional parser dependencies matter: without `pdfplumber` and `PyMuPDF`, table extraction and page rendering are skipped.
