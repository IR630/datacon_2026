# Deadline Runbook

Full setup and launch instructions: `docs/run_everything.md`.

## Current Best Local Result

- Domain: SelTox.
- Published single-agent baseline: Macro-F1 `0.045`.
- Current best submission: `data/predictions/seltox_submission_llm.csv`.
- Current best score in `main`: Macro-F1 `0.1921`.
- Shape: calibrated prior rows for all `65` target PDFs plus LLM extracted rows from locally resolved PDFs.
- Yandex AI Studio final extraction model: `qwen3.6-35b-a3b/latest`.

## Reproduce

```bash
python -m src.cli resolve-pdfs --domain seltox --start 0 --limit 65 --sleep 0.05 --out-dir data/pdfs --report data/cache/pdf_resolver_report_deadline.json
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox --extracted data/predictions/extracted.csv --out data/predictions/seltox_submission_llm.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_llm.csv --out data/predictions/seltox_submission_llm_metrics.csv
python -m streamlit run app.py --server.port=8501 --server.address=localhost
```

## Demo Flow

1. Open Streamlit.
2. Show `Dataset run`: gold present, `65` target PDFs, local PDF count, current Macro-F1.
3. Click `Build` and `Evaluate` if live reproduction is needed.
4. Download `seltox_submission_llm.csv`.
5. Open `Single PDF`, upload any article PDF, run `Parse`, `Evidence`, `Extract`.

## Notes For Teammates

- Do not commit `api.txt`, `.env`, or anything under `data/`; these are ignored local artifacts.
- Keep `qwen3.6-35b-a3b/latest` as default for final `llm-extract`.
- Use `deepseek-v4-flash` only for cheap smoke/debug checks.
- The fastest next score improvement is more PDF coverage and better table/image extraction, not changing the prior.
- Optional parser dependencies matter: without `pdfplumber` and `PyMuPDF`, table extraction and page rendering are skipped.
