# Model Strategy

Updated: 2026-06-28.

## Balance / Billing Check

Yandex AI Studio is working.

Observed smoke runs:

| Model | Result | Observed usage |
|---|---|---:|
| `deepseek-v4-flash` | returned `OK` | `34` total tokens |
| `aliceai-llm-flash` | returned `OK` | `17` total tokens |
| `qwen3-235b-a22b-fp8` | returned `OK` | `14` total tokens |
| `qwen3.6-35b-a3b` | no final text, `status=incomplete` in diagnostic response | `146` total tokens in one test |
| `gpt-oss-120b` | no final text on short smoke | `103` total tokens |

If AI Studio balance does not visibly change, that is expected for these smoke tests: the total spend is tiny and billing UI can update with delay. For real budget tracking, use token usage printed by `python -m src.cli llm-smoke`.

## Recommended Yandex Setup

Default text extraction:

```text
LLM_MODEL=deepseek-v4-flash
```

Why:

- context up to `1M`;
- OpenAI-compatible API;
- smoke-tested in this repo;
- best first choice for long PDF/evidence chunks.

Cheap debug:

```text
LLM_MODEL=aliceai-llm-flash
```

Why:

- smoke-tested;
- low cost;
- use for small evidence snippets and prompt iteration.

Second text candidate:

```text
LLM_MODEL=qwen3-235b-a22b-fp8
```

Why:

- smoke-tested;
- large model;
- worth comparing on extraction quality after `deepseek-v4-flash`.

Do not use by default tonight:

```text
LLM_MODEL=qwen3.6-35b-a3b
LLM_MODEL=gpt-oss-120b
```

Reason: both currently spend output tokens but do not produce final visible text with our simple OpenAI-compatible smoke call. `qwen3.6-35b-a3b` is still interesting for image/table recovery because the Yandex docs say it supports Base64 images, but it needs a separate adapter/test before production use.

Also avoid:

```text
LLM_MODEL=deepseek-v32
```

The Yandex docs say it was switched in favor of `deepseek-v4-flash`, and the old URI is valid only until 2026-06-28.

## If Using Non-Yandex Models

Best external options for this task:

1. OpenAI latest GPT-5.x family for structured extraction and vision.
   - Good fit for strict JSON, page images, long context, and tool workflows.
2. Gemini 2.5 Pro / Flash for long-context multimodal PDF/page-image extraction.
   - Good fit for large full-document context and table-heavy visual pages.
3. Claude Sonnet / Opus tier for difficult visual/table reasoning.
   - Good fit for table reconstruction and conservative extraction.

Practical recommendation:

- Stay on Yandex for broad cheap text extraction now.
- Add one optional external VLM path only for hard pages/tables where text parser fails.
- Do not run VLM on every page until we measure cost; route only selected pages with activity tables, figures, or failed table parsing.

## What To Improve Next

Priority order:

1. Improve PDF coverage:
   - Crossref resolver is useful but misses many Elsevier/ScienceDirect articles.
   - Add publisher-specific URL heuristics and Unpaywall/OpenAlex lookup.
2. Improve parser:
   - install/use `pdfplumber` for tables;
   - install/use `PyMuPDF` for page rendering and crops.
3. Improve extraction strategy:
   - keep one blank prior row for every target PDF;
   - append extracted rows only when evidence is strong;
   - numeric blanks must be `nan`, string blanks must be `NOT_DETECTED`.
4. Improve activity extraction first:
   - `bacteria`, `strain`, `method`, `mic_np_µg_ml`, `zoi_np_mm`.
5. Add selective vision/table recovery:
   - detect likely activity table pages;
   - send page crop/image to VLM;
   - parse markdown table back into SelTox rows.

## Useful Commands

```bash
python -m src.cli llm-smoke --model deepseek-v4-flash
python -m src.cli llm-smoke --model aliceai-llm-flash
python -m src.cli llm-smoke --model qwen3-235b-a22b-fp8
python -m src.cli resolve-pdfs --domain seltox --start 0 --limit 20
python -m src.cli batch-extract --pdf-dir data/pdfs --domain SelTox --out data/predictions/selt_batch.csv
python -m src.cli prior-pred --domain seltox --rows-per-pdf 1 --out data/predictions/seltox_prior_k1.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/selt_prior_plus_batch_6.csv
```

## Sources

- Yandex AI Studio base models: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models
- Yandex AI Studio quickstart: https://aistudio.yandex.ru/docs/ru/ai-studio/quickstart/
- OpenAI models: https://platform.openai.com/docs/models
- Gemini models: https://ai.google.dev/gemini-api/docs/models
- Claude models: https://docs.anthropic.com/en/docs/about-claude/models/overview
