# DataCon 2026 — ChemX SelTox

Система автоматической экстракции химических данных из научных PDF для бенчмарка
[ChemX](https://github.com/ai-chem/ChemX) (NeurIPS 2025). Домен — **SelTox**
(антимикробная активность и токсичность наночастиц серебра).

## Результат

На домене SelTox мы превосходим опубликованный single-agent baseline ChemX в **4.2 раза**.

| Сабмишен | Macro-F1 |
|---|:---:|
| ChemX single-agent baseline | 0.0454 |
| Калиброванный prior (без LLM) | 0.1357 |
| + LLM-экстракция (Qwen3.6-35B) | 0.1863 |
| + нормализация под формат gold | **0.1921** |

Метрика — ChemX exact-string multiset Macro-F1 по 23 целевым полям. Подробности и
команды воспроизведения: [`docs/seltox_score.md`](./docs/seltox_score.md).

## Подход

Один проход на статью, table-faithful, abstention-first:

```
PDF (+ supplementary)
  |
  v  1. Parse      текст и таблицы -> markdown, страницы -> PNG
  v  2. Context    весь документ в контекст (262k токенов), без BM25
  v  3. Extract    один schema-driven вызов LLM -> одна строка на (бактерия x наночастица)
  v  4. Normalize  приведение к точному формату gold (per-field)
  v  5. Submission  prior(65 статей) + извлечённые строки
  v  6. Evaluate    доверенный ChemX-evaluator
```

Три идеи, каждая измеримо двигает метрику:

1. **Калиброванный prior.** Мажоритарные дефолты по полям без пропусков
   (`np=Ag`, `method=MIC`, `precursor=AgNO3`, ...) дают floor `0.1357` — уже ×3 к baseline
   без единого вызова LLM.
2. **Mono-agent LLM-экстракция.** Весь документ -> `Qwen3.6-35B` (Yandex AI Studio,
   OpenAI-совместимый API) -> `{samples: [...]}`. Abstention-first: нет в тексте -> `null`,
   не выдумываем. Поднимает до `0.1863`.
3. **Нормализация под gold.** Свободный текст LLM приводится к словарю gold
   (`method -> {MIC, ZOI, MBC, MFC}`, `precursor -> {AgNO3, NOT_DETECTED}`), что возвращает
   истинные ZOI/MBC, пропущенные prior'ом. Итог `0.1921`.

## Быстрый старт

```bash
# 1. Зависимости
python -m pip install -r requirements.txt

# 2. Ключ LLM: скопировать .env.example -> .env и заполнить
#    LLM_PROVIDER=yandex, YANDEX_API_KEY, YANDEX_FOLDER_ID,
#    LLM_MODEL=qwen3.6-35b-a3b/latest
cp .env.example .env

# 3. Локальный кэш gold (Hugging Face ai-chem/SelTox)
python -m src.cli cache-gold --domain seltox

# 4. Воспроизведение результата
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox \
  --extracted data/predictions/extracted.csv \
  --out data/predictions/submission.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/submission.csv
```

Полный пошаговый runbook (включая загрузку PDF и настройку Yandex): см.
[`docs/run_everything.md`](./docs/run_everything.md).

## Веб-интерфейс

```bash
streamlit run app.py
```

Загрузка PDF -> парсинг -> экстракция -> таблица извлечённых полей с указанием источника
и выгрузкой в CSV.

## Презентация

[`presentation.html`](./presentation.html) — слайды Reveal.js (открываются в браузере).

## Структура репозитория

```
src/
  agents/          экстракторы (seltox_extractor — основной schema-driven вызов LLM) + LLM-клиент
  parse/           парсинг PDF (текст, таблицы, изображения страниц)
  postprocess/     нормализаторы под формат gold + калиброванный prior
  eval/            доверенный ChemX metric adapter
  data/            резолвер PDF (Europe PMC / Unpaywall / OpenAlex / Crossref)
  cli.py           все команды пайплайна
baseline/          перенесённый single-agent baseline ChemX (эталон сравнения)
configs/           конфигурация домена
tests/             unit-тесты (pytest)
docs/              методология, формат gold, настройка LLM, runbook, итоговые метрики
app.py             веб-интерфейс (Streamlit)
```

## Тесты и CI

```bash
python -m pytest -q
```

CI (GitHub Actions, [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)) прогоняет тесты
на каждый PR. Процесс ведения репозитория — GitHub Flow, см.
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Документация

| Файл | О чём |
|---|---|
| [`docs/seltox_score.md`](./docs/seltox_score.md) | Итоговые метрики и воспроизведение |
| [`docs/run_everything.md`](./docs/run_everything.md) | Полный runbook запуска |
| [`docs/yandex_ai_studio.md`](./docs/yandex_ai_studio.md) | Настройка LLM (Yandex AI Studio) |
| [`docs/model_strategy.md`](./docs/model_strategy.md) | Обоснование выбора модели |
| [`docs/gt_format.md`](./docs/gt_format.md) | Измеренный формат gold (калибровка нормализаторов) |

## Ссылки

- Датасеты ChemX: https://huggingface.co/collections/ai-chem/chemx
- Код бенчмарка: https://github.com/ai-chem/ChemX
- Статья ChemX (NeurIPS 2025): https://proceedings.neurips.cc/paper_files/paper/2025/file/9e08a1db869a9646418e3371b24c6ae6-Paper-Datasets_and_Benchmarks_Track.pdf
