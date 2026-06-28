# Как Запустить Все

Быстрый рабочий запуск SelTox-MAX: зависимости, Yandex AI Studio, PDF, LLM extraction, submission, метрика и Streamlit UI.

## 1. Зависимости

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m compileall src app.py
```

## 2. `.env`

Скопируйте `.env.example` в `.env` и заполните локальный файл. `.env`, `api.txt` и `data/*` уже ignored, их нельзя коммитить.

```text
LLM_PROVIDER=yandex
YANDEX_API_KEY=<your-yandex-api-key>
YANDEX_FOLDER_ID=<your-folder-id>
LLM_MODEL=qwen3.6-35b-a3b/latest
OPENAI_BASE_URL=https://ai.api.cloud.yandex.net/v1
LLM_TEMPERATURE=0
LLM_MAX_OUTPUT_TOKENS=16384
```

Текущий лучший default для финального `llm-extract`: `qwen3.6-35b-a3b/latest`.

Для дешевого smoke/debug можно временно использовать `deepseek-v4-flash`. `gpt-oss-120b` и `gpt-oss-20b` пока не ставим default: на коротких проверках они тратили tokens и не возвращали полезный финальный текст.

Проверить конфиг без сетевого запроса:

```bash
python -m src.cli llm-smoke --dry-run
```

Проверить реальный LLM-запрос:

```bash
python -m src.cli llm-smoke --max-output-tokens 1024 --prompt "Return exactly OK."
```

## 3. Gold И PDF

Если `data/gold/seltox.parquet` уже есть, gold скачивать не нужно.

```bash
python -m src.cli cache-gold --domain seltox
```

Пройти resolver по 65 target articles:

```bash
python -m src.cli resolve-pdfs --domain seltox --start 0 --limit 65 --sleep 0.05 --out-dir data/pdfs --report data/cache/pdf_resolver_report_deadline.json
```

Нормально, если скачались не все 65 PDF. На текущем локальном прогоне было 12 PDF; submission все равно покрывает 65 статей через prior rows.

## 4. Лучший Submission

Основной финальный путь сейчас:

```bash
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox --extracted data/predictions/extracted.csv --out data/predictions/seltox_submission_llm.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_llm.csv --out data/predictions/seltox_submission_llm_metrics.csv
```

Смысл:

```text
65 calibrated prior rows for all target PDFs
+ LLM extracted rows for locally available PDFs
= final ChemX submission
```

Текущий лучший зафиксированный результат в `main`: `Macro-F1 = 0.1921`, см. `docs/seltox_score.md`.

## 5. Интерфейс

```bash
python -m streamlit run app.py --server.port=8501 --server.address=localhost
```

Открыть:

```text
http://localhost:8501
```

Вкладки:

- `Dataset run`: собрать/evaluate/download submission.
- `Single PDF`: загрузить один PDF, сделать `Parse`, `Evidence`, `Extract`.
- `Config`: посмотреть sanitized LLM config без ключа.

Если хотите в UI показать лучший LLM submission, в `Dataset run` укажите:

```text
Extracted CSV: data/predictions/extracted.csv
Submission CSV: data/predictions/seltox_submission_llm.csv
Metrics CSV: data/predictions/seltox_submission_llm_metrics.csv
```

## 6. Быстрый Дедлайновый Запуск

Если зависимости, `.env`, gold и PDF уже на месте:

```bash
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox --extracted data/predictions/extracted.csv --out data/predictions/seltox_submission_llm.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_llm.csv --out data/predictions/seltox_submission_llm_metrics.csv
python -m streamlit run app.py --server.port=8501 --server.address=localhost
```

## Sources

- Yandex AI Studio model list: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models
- Yandex AI Studio quickstart: https://aistudio.yandex.ru/docs/ru/ai-studio/quickstart/
