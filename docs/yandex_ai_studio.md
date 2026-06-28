# Yandex AI Studio Для SelTox-MAX

Updated: 2026-06-28.

## Recommended Model

For the current final SelTox pipeline use:

```text
LLM_MODEL=qwen3.6-35b-a3b/latest
LLM_MAX_OUTPUT_TOKENS=16384
```

`qwen3.6-35b-a3b/latest` is the best current default for `python -m src.cli llm-extract`.

Use `deepseek-v4-flash` for cheap smoke/debug checks:

```bash
python -m src.cli llm-smoke --model deepseek-v4-flash --max-output-tokens 32 --prompt "Return exactly OK."
```

## Local `.env`

```text
LLM_PROVIDER=yandex
YANDEX_API_KEY=<your-yandex-api-key>
YANDEX_FOLDER_ID=<your-folder-id>
LLM_MODEL=qwen3.6-35b-a3b/latest
OPENAI_BASE_URL=https://ai.api.cloud.yandex.net/v1
LLM_TEMPERATURE=0
LLM_MAX_OUTPUT_TOKENS=16384
```

`YANDEX_FOLDER_ID` is the Yandex Cloud folder/catalog id, not the API key.

`api.txt` and `.env` are ignored by git.

## Checks

Without network:

```bash
python -m src.cli llm-smoke --dry-run
```

With network:

```bash
python -m src.cli llm-smoke --max-output-tokens 1024 --prompt "Return exactly OK."
```

Expected: sanitized config plus an `OK` response. The key itself must never be printed.

## Run Extraction

```bash
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox --extracted data/predictions/extracted.csv --out data/predictions/seltox_submission_llm.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_llm.csv --out data/predictions/seltox_submission_llm_metrics.csv
```

Current best score in `main`: `Macro-F1 = 0.1921`.

## Sources

- Quickstart and OpenAI-compatible example: https://aistudio.yandex.ru/docs/ru/ai-studio/quickstart/
- Base models and model URI list: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models
