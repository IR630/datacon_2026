# Как Запустить Все

Этот файл описывает быстрый рабочий запуск SelTox-MAX: зависимости, Yandex AI Studio, датасет, submission, метрика и Streamlit UI.

## 1. Подготовить Окружение

```bash
python -m pip install -r requirements.txt
```

Если нужно быстро проверить, что зависимости на месте:

```bash
python -m pytest -q
python -m compileall src app.py
```

## 2. Настроить LLM

Скопируйте `.env.example` в `.env` и заполните только локальный `.env`.

```text
LLM_PROVIDER=yandex
YANDEX_API_KEY=<your-yandex-api-key>
YANDEX_FOLDER_ID=<your-folder-id>
LLM_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=https://ai.api.cloud.yandex.net/v1
LLM_TEMPERATURE=0
LLM_MAX_OUTPUT_TOKENS=16384
```

`api.txt`, `.env` и `data/*` уже игнорируются git. Не коммитьте ключи и скачанные данные.

### Лучшие Модели Сейчас

Основной default:

```text
LLM_MODEL=deepseek-v4-flash
```

Почему: стабильно возвращает текст в нашем OpenAI-compatible wrapper, прошел smoke-test, подходит для длинных evidence chunks.

Дешевый debug:

```text
LLM_MODEL=aliceai-llm-flash
```

Второй кандидат для ручного сравнения качества:

```text
LLM_MODEL=qwen3-235b-a22b-fp8
```

Пока не ставить default:

```text
LLM_MODEL=qwen3.6-35b-a3b/latest
LLM_MODEL=gpt-oss-120b
LLM_MODEL=gpt-oss-20b
```

Эти модели доступны, но в текущем wrapper на коротких smoke-тестах тратили output tokens и возвращали пустой финальный текст. `qwen3.6-35b-a3b` интересна для будущего image/table path, потому что AI Studio docs описывают поддержку изображений через Base64, но для нее нужен отдельный adapter.

Проверка конфига без сетевого запроса:

```bash
python -m src.cli llm-smoke --dry-run
```

Проверка реального запроса:

```bash
python -m src.cli llm-smoke --max-output-tokens 32 --prompt "Return exactly OK."
```

## 3. Скачать Gold И PDF

Если `data/gold/seltox.parquet` уже есть, этот шаг можно пропустить.

```bash
python -m src.cli cache-gold --domain seltox
```

Докачать open-access PDF для 65 target articles:

```bash
python -m src.cli resolve-pdfs --domain seltox --start 0 --limit 65 --sleep 0.05 --out-dir data/pdfs --report data/cache/pdf_resolver_report_deadline.json
```

Resolver не гарантирует 65/65 PDF: часть статей закрыта или не отдает прямой PDF. На текущем локальном прогоне было 12 PDF.

## 4. Собрать Submission

Batch extraction по доступным PDF:

```bash
python -m src.cli batch-extract --pdf-dir data/pdfs --domain SelTox --out data/predictions/selt_batch_resolved.csv --work-dir data/predictions/per_pdf --parsed-dir data/parsed --top-k 8
```

Собрать итоговый ChemX submission:

```bash
python -m src.cli build-submission --domain seltox --extracted data/predictions/selt_batch_resolved.csv --out data/predictions/seltox_submission_resolved.csv
```

Посчитать локальную метрику:

```bash
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_resolved.csv --out data/predictions/seltox_submission_resolved_metrics.csv
```

Текущий лучший локальный результат:

```text
Macro-F1 = 0.172471
```

Это выше published SelTox single-agent baseline `0.045`.

## 5. Запустить Интерфейс

```bash
python -m streamlit run app.py --server.port=8501 --server.address=localhost
```

Открыть:

```text
http://localhost:8501
```

В UI:

1. `Dataset run`: нажать `Build`, потом `Evaluate`, скачать submission/metrics.
2. `Single PDF`: загрузить PDF, нажать `Parse`, `Evidence`, `Extract`.
3. `Config`: проверить sanitized LLM config без показа ключа.

## 6. Что Сейчас Делает LLM

LLM подключена только в `ActivityExtractorAgent` для activity fields:

```text
bacteria, mdr, strain, method, mic_np_µg_ml, concentration, zoi_np_mm, time_set_hours
```

Если LLM не настроена, возвращает пустой текст или JSON не парсится, pipeline автоматически использует deterministic fallback.

На последнем сравнении `deepseek-v4-flash` и `LLM_PROVIDER=disabled` дали одинаковый CSV и одинаковый `Macro-F1 = 0.172471`. Значит текущий score фактически держится на calibrated prior + deterministic extraction. Следующий реальный прирост: улучшать LLM JSON parsing/prompting и добавлять selective image/table path.

## 7. Короткий Дедлайновый Запуск

Если данные уже лежат локально:

```bash
python -m src.cli batch-extract --pdf-dir data/pdfs --domain SelTox --out data/predictions/selt_batch_resolved.csv --work-dir data/predictions/per_pdf --parsed-dir data/parsed --top-k 8
python -m src.cli build-submission --domain seltox --extracted data/predictions/selt_batch_resolved.csv --out data/predictions/seltox_submission_resolved.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_resolved.csv --out data/predictions/seltox_submission_resolved_metrics.csv
python -m streamlit run app.py --server.port=8501 --server.address=localhost
```

## Sources

- Yandex AI Studio model list: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models
- Yandex AI Studio quickstart: https://aistudio.yandex.ru/docs/ru/ai-studio/quickstart/
