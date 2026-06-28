# Model Strategy

Updated: 2026-06-28.

## Current Recommendation

Best current model for final SelTox extraction:

```text
LLM_MODEL=qwen3.6-35b-a3b/latest
LLM_MAX_OUTPUT_TOKENS=16384
```

Why:

- works in Yandex AI Studio with our OpenAI-compatible wrapper when the output limit is large enough;
- used by the current `llm-extract` path;
- current `main` score with Qwen3.6 + postprocessing mappings is `Macro-F1 = 0.1921`;
- better than the previous deterministic / DeepSeek path (`0.172471` locally).

Cheap smoke/debug model:

```text
LLM_MODEL=deepseek-v4-flash
```

Why:

- fast and stable for short checks;
- good for `llm-smoke`;
- not the best current final extraction default.

Other tested options:

| Model | Recommendation |
|---|---|
| `aliceai-llm-flash` | cheap debug only |
| `qwen3-235b-a22b-fp8` | manual comparison candidate |
| `gpt-oss-120b` | avoid as default for now |
| `gpt-oss-20b` | avoid as default for now |

## Minimal `.env`

```text
LLM_PROVIDER=yandex
YANDEX_API_KEY=<your-yandex-api-key>
YANDEX_FOLDER_ID=<your-folder-id>
LLM_MODEL=qwen3.6-35b-a3b/latest
OPENAI_BASE_URL=https://ai.api.cloud.yandex.net/v1
LLM_TEMPERATURE=0
LLM_MAX_OUTPUT_TOKENS=16384
```

## Smoke Tests

Config only:

```bash
python -m src.cli llm-smoke --dry-run
```

Real short request:

```bash
python -m src.cli llm-smoke --max-output-tokens 1024 --prompt "Return exactly OK."
```

## Final Extraction

```bash
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox --extracted data/predictions/extracted.csv --out data/predictions/seltox_submission_llm.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_llm.csv --out data/predictions/seltox_submission_llm_metrics.csv
```

## Notes

- Do not commit `.env`, `api.txt`, or anything under `data/`.
- Qwen3.6 looked bad with tiny `--max-output-tokens 32`, but works when the output budget is large enough.
- The current submission still needs prior rows for all 65 target PDFs; `build-submission` adds them.
- The next biggest improvement is more PDF coverage and better table/image extraction.

## Sources

- Yandex AI Studio model list: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models
- Yandex AI Studio quickstart: https://aistudio.yandex.ru/docs/ru/ai-studio/quickstart/
