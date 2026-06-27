# Yandex AI Studio для SelTox-MAX

Обновлено: 2026-06-27.

## Выбор модели

Для первого платного smoke-run по SelTox я бы ставил:

```text
LLM_PROVIDER=yandex
LLM_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=https://ai.api.cloud.yandex.net/v1
```

Почему именно так:

- `DeepSeek V4 Flash` имеет базовый shared instance, pay-per-token, OpenAI-compatible API и контекст до `1M` токенов. Для наших PDF/table extraction задач это важнее, чем минимальная цена.
- Цена в синхронном режиме на момент проверки docs: `0.3 ₽ / 1000 input tokens` и `0.5 ₽ / 1000 output tokens`.
- `Alice AI LLM Flash` дешевле (`0.1 ₽ input`, `0.2 ₽ output` за 1000 токенов), но контекст `64k`, поэтому лучше как cheap debug mode для маленьких evidence snippets.
- `Qwen3.6-35B` выглядит полезным вторым кандидатом для vision/table recovery: дешевле DeepSeek V4 Flash (`0.2 ₽ input`, `0.3 ₽ output`) и поддерживает картинки в base64, но сначала нам нужен устойчивый text/table extraction.
- `DeepSeek-V3.2` лучше не выбирать: в docs указано, что обращения редиректятся на `DeepSeek V4 Flash`, а старый URI действует только до `2026-06-28`.

Модель указывается как:

```text
gpt://<YANDEX_FOLDER_ID>/deepseek-v4-flash
```

В коде достаточно задать `LLM_MODEL=deepseek-v4-flash`; полный URI соберется автоматически.

## Настройка ключа

`YANDEX_FOLDER_ID` — это идентификатор каталога Yandex Cloud, не API-ключ.

Где взять:

1. Откройте https://aistudio.yandex.cloud/.
2. В верхней части экрана найдите название каталога, обычно `default`.
3. Наведите курсор на название каталога.
4. Нажмите иконку копирования рядом с ним: AI Studio скопирует идентификатор каталога в буфер обмена.

Самый простой локальный вариант:

```text
api.txt
------
<your-yandex-api-key>
YANDEX_FOLDER_ID=<your-folder-id>
```

Альтернативно через `.env`:

```text
LLM_PROVIDER=yandex
YANDEX_API_KEY=<your-yandex-api-key>
YANDEX_FOLDER_ID=<your-folder-id>
LLM_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=https://ai.api.cloud.yandex.net/v1
LLM_TEMPERATURE=0
```

`api.txt` и `.env` уже игнорируются git.

## Проверка

Сначала без сетевого запроса:

```bash
python -m src.cli llm-smoke --dry-run
```

После добавления `YANDEX_FOLDER_ID` можно сделать минимальный запрос:

```bash
python -m src.cli llm-smoke
```

Если хотим дешевую быструю проверку:

```bash
python -m src.cli llm-smoke --model aliceai-llm-flash
```

Если хотим сравнить второй сильный вариант:

```bash
python -m src.cli llm-smoke --model qwen3.6-35b-a3b
```

## Что делаем дальше

1. Добавить `YANDEX_FOLDER_ID`, проверить `llm-smoke`.
2. Подключить LLM к `ActivityExtractorAgent`: именно activity rows (`bacteria`, `method`, `MIC`, `ZOI`) дадут самый быстрый прирост против baseline.
3. Запустить extraction на нескольких SelTox PDF, сохранить raw evidence и LLM responses.
4. Подкрутить normalizer под exact-string metric.
5. После локального gold cache считать ChemX-compatible Macro-F1 и итеративно чинить поля с худшим F1.

## Источники

- Quickstart и OpenAI-compatible пример: https://aistudio.yandex.ru/docs/ru/ai-studio/quickstart/
- Base models и URI моделей: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models
- Pricing: https://aistudio.yandex.ru/docs/ru/ai-studio/pricing.html
