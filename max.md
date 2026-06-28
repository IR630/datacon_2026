# MAX.md — DataCon'26 ChemX (SelTox): состояние и план до конца

Хендофф-документ. Ветка: **`alisa`** (от `selt-mvp`). Всё запушено на `origin/alisa`.
Связанные документы: `docs/plan_alisa.md` (полный план по фазам), `docs/gt_format.md`
(измеренный формат gold), `docs/merge_plan_alisa.md` (port-level разбор), `docs/progress.md`
(лог команды), `CHEMX_FINDINGS.md` (конспект воркшопа).

---

## 0. TL;DR

- Цель: побить single-agent baseline ChemX на домене **SelTox** (Macro-F1 **0.0454**) + UI + код + презентация.
- **40 очков уже фактически заперты**: `build-submission` (без LLM) даёт Macro-F1 **0.1357** (×3 к baseline).
- Сделано: доверенный evaluator (Gate A), калибровка нормализаторов под GT (Фаза 1), сабмишен-пол (Фаза 2), покрытие PDF 6→14/65 (Фаза 4).
- Осталось главное: **Фаза 3 — реальная LLM-экстракция** (нужен ключ Yandex `api.txt`), затем итерации, VLM, UI, README, презентация, бонусы.

---

## 1. Контекст и цель (scoring)

Рубрика: **40** за победу над baseline на ≥1 домене + **20** UI + **20** код/README + **20** презентация.
Бонусы: **+5**/домен (до +40), **+10** за оба направления (small molecules + nanomaterials).

Выбран домен **SelTox** (наноматериалы, без SMILES): самая низкая планка baseline (0.0454), 6 полей у
baseline в 0.0 (легко добрать), ключевые поля в таблицах. 23 целевых поля
(`baseline/src/constants.py::EXTRACTED_COLUMNS['seltox']`).

Метрика (`baseline/src/metric_calc.py`, зеркало в `src/eval/chemx_metric_adapter.py`):
column-wise **мультимножество строк внутри статьи**, **exact string match** после `astype(str)`,
Macro-F1 = среднее F1 по 23 колонкам. Скорятся **только** EXTRACTED_COLUMNS (НЕ метаполя — это
проверено: эталоны `reference_metrics/*.csv` содержат ровно EXTRACTED_COLUMNS строк).

---

## 2. Окружение и рантайм (КАК запускать) — ВАЖНО

- Платформа: Windows, PowerShell. Репозиторий: `D:\vano\datacon_2026`.
- Создан venv `.venv` (в `.gitignore`). Установлено: `pandas pyarrow huggingface_hub datasets requests pytest pydantic`.
  Для парсинга PDF (Фаза 3) ещё нужно: `pip install pdfplumber pymupdf`. Полный набор — `requirements.txt`.
- Gold закэширован: `data/gold/seltox.parquet` (через `cache-gold`, из HF `ai-chem/SelTox`). В `.gitignore`.
- PDF: `data/pdfs/*.pdf` — 14 шт. скачано (Фаза 4). В `.gitignore`.
- **LLM = Yandex AI Studio** (OpenAI-совместимый), default модель `deepseek-v4-flash` (контекст 1M).
  Ключ задаётся файлом `api.txt` в корне (в `.gitignore`), формат — две строки:
  ```
  <YANDEX_API_KEY>
  <YANDEX_FOLDER_ID>
  ```
  Без `api.txt` любые LLM-команды не работают (см. `docs/yandex_ai_studio.md`, `docs/model_strategy.md`).
- Сетевое замечание (для агента Claude в песочнице): внешняя сеть доступна только с выключенным
  sandbox у Bash-инструмента; `curl` падает по SSL, но Python/pip/requests работают. У пользователя
  в обычном терминале сеть работает штатно.

Базовые команды (PowerShell, активированный venv или `.venv\Scripts\python.exe -m ...`):
```powershell
python -m src.cli cache-gold --domain seltox
python -m src.cli inspect-gt-format --domain seltox
python -m src.cli verify-normalizers --domain seltox        # -> 0.9995
python -m src.cli validate-evaluator --domain seltox        # Gate A (FAIL@1e-6 ожидаемо, см. §5)
python -m src.cli resolve-pdfs --domain seltox --start 0 --limit 65
python -m src.cli build-submission --domain seltox --out data/predictions/seltox_submission.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission.csv   # -> 0.1357
pytest -q                                                    # 17 passed
```

---

## 3. Целевая архитектура (один проход, table-faithful, abstention-first)

```
PDF (+ supplementary)
 1. Parse (наш ensemble): text + таблицы→markdown, page→PNG, кэш в data/parsed/<stem>/
 2. Context: ВЕСЬ документ (deepseek 1M), таблицы как markdown с тегами page/section (НЕ BM25 top-k)
 3. Extract: ОДИН schema-driven вызов complete_json(seltox.json, strict) + few-shot из gold (вне eval),
    одна строка на (bacteria×np), абстейн где не сказано  [схлопнуть 3 агента в 1]
 4. Normalize: src/postprocess/normalize.py::normalize_seltox_record (КАЛИБРОВАН под GT)
 5. Validate: убрать неподтверждённое/галлюцинации
 6. Submission: build-submission = prior(65) + extracted rows (--extracted)
 7. (опц.) VLM по страницам, где парсер таблиц упал
 8. Evaluate: src/eval/chemx_metric_adapter (доверенный)
```
Принципы: **abstention-first**, **exact-string под формат GT**, **mono-agent** (не тяжёлый MAS),
**без self-consistency/ensembling/fine-tuning**, **не обходить anti-bot** при скачивании PDF.

---

## 4. Что сделано в этой сессии

Коммиты на `alisa`:
`b1abd79` Port A · `42015f1` планы+конспект · `e9e9f36` фикс кодировки ·
`a20df73` Фаза 1 · `f54dacd` Фаза 2 · `0432c34` Фаза 4.

### Gate A — доверенный evaluator (`src/eval/chemx_metric_adapter.py`, `src/cli.py validate-evaluator`)
- Прогнан вживую. **Точного 1:1 с эталоном нет**, и это upstream-проблема: файл
  `seltox_articles.npy` (точный eval-subset) отсутствует в репо И на GitHub (404). Загрузка gold
  исключена как причина (`read_parquet` ≡ `load_dataset`, оба `float64`).
- Полоса сверки вокруг ref 0.0454: `articles-as-is` 0.0407 (mixed-case матчит 19/65),
  `lowercase` 0.0467 (65/65). **Решение:** внутренний эталон = all-65 lowercase. См. память
  проекта `gate-a-seltox-metric`.

### Фаза 1 — калибровка нормализаторов под формат GT
- `inspect-gt-format` (новая команда) → `docs/gt_format.md` (точный формат всех 23 полей).
- `src/postprocess/normalize.py`: `SELTOX_FIELD_NORMALIZERS` (per-field):
  - `float64`-поля → `"10.0"`; `mic_np_µg_ml` (str) → `"100"`; `mdr`/`coating` → бинарные 0/1;
  - расширены карты `bacteria` (полные латинские) и `np` (формулы).
- `verify-normalizers` (новая команда): идемпотентность normalized-gold vs gold = **0.9995**.

### Фаза 2 — сабмишен-пол (`build-submission`)
- `seltox_prior_record()` = калиброванные пропуски + мажоритарные дефолты:
  `np=Ag, method=MIC, shape=spherical, time_set_hours=24.0, precursor_of_np=AgNO3, np_synthesis=green_synthesis`,
  `mdr=0, coating=0`. (Каждый дефолт измеренно поднимает свой field.)
- Floor: legacy 0.0753 → +бинарные 0.0929 → **+все дефолты 0.1357** (×3 к baseline). **40 очков заперты.**
- `build-submission --extracted <csv>` уже умеет домешивать извлечённые строки.

### Фаза 4 — покрытие PDF (`src/data/pdf_resolver.py`)
- Было Crossref-only (6). Стало цепочка **Europe PMC + Unpaywall + OpenAlex + Crossref**, приоритет
  bot-friendly Europe PMC `fullTextPDF`. **Покрытие 14/65.** Остаток — платный Elsevier/ScienceDirect
  (anti-bot, не обходим) или нет OA. Непокрытые статьи всё равно скорятся prior'ом.

Тесты: **17 passed** (`tests/`).

---

## 5. Ключевые находки (must-know)

1. **Метрика скорит только EXTRACTED_COLUMNS** (не метаполя) — тезис конспекта про «дешёвые метаполя»
   неверен для ChemX. CrossRef/OpenAlex — только для скачивания PDF.
2. **Числовой формат — per-field по dtype gold**: `float64`→`"10.0"`, `mic` (str)→`"100"`. Один общий
   формат неверен. Источник истины — `docs/gt_format.md`.
3. **`mdr`/`coating` бинарные 0/1, 0% пропусков** → дефолт `0` (а не nan/NOT_DETECTED).
4. **Мажоритарные дефолты для 0%-nan полей** (np=Ag 79%, method=MIC, precursor=AgNO3, shape, time) —
   огромный бесплатный прирост (floor 0.075→0.136).
5. **Gate A не 1:1** из-за отсутствующего `seltox_articles.npy`. Гнаться за PASS@1e-6 не нужно;
   внутренний эталон — all-65 lowercase; baseline для победы — 0.0454.
6. **Гранулярность строк** = рычаг: одна строка на (bacteria×np); `drop_duplicates()` в wrapper'е
   схлопывает одинаковые строки (нельзя дублировать пустые).
7. **PDF coverage ~22%** (павалл). Стратегия устойчива: prior закрывает непокрытые статьи.

---

## 6. Что осталось реализовать

### Фаза 3 — реальная экстракция (СЛЕДУЮЩЕЕ; нужен `api.txt`)
- `pip install pdfplumber pymupdf`; прогнать `parse` на 14 PDF, убедиться, что таблицы/текст в
  `data/parsed/<stem>/` достаются (особенно activity-таблицы MIC/ZOI).
- Новый единый экстрактор `src/agents/seltox_extractor.py` (или рефактор `extract`):
  - вход: весь parsed-текст + таблицы как markdown (full-doc, без BM25 top-k);
  - `LLMClient.complete_json(messages, schema=baseline/data/schemas/seltox.json)` (strict);
  - few-shot: 2-3 реальные строки из gold ИЗ СТАТЕЙ ВНЕ eval-subset (нет в `SELTOX_ARTICLES`),
    чтобы показать точный формат, без утечки ответов;
  - энумерация: одна запись на (bacteria×np); abstention-first (nan/NOT_DETECTED где не сказано);
  - сохранять raw LLM request/response в `data/cache/` для дебага/презентации.
- Прогнать `normalize_seltox_record` + validator на выходе; собрать
  `build-submission --extracted data/predictions/extracted.csv`.
- **Go/no-go:** `evaluate` (prior+extracted) > prior-only (0.1357) под доверенным evaluator.
- Проверка sanity на конкретной статье (например `103_alekish2018.pdf`): bacteria/method/MIC/ZOI/np
  извлеклись в формате GT.

### Фаза 5 — итерации до максимума SelTox
- Цикл по полям (headroom × частота): сперва 6 нулевых green-synthesis полей (из methods-текста),
  затем `np/bacteria/method/shape/precursor`, затем `mic/zoi/sizes` (числа+таблицы).
- Калибровать few-shot/промпт/нормализацию; следить, чтобы extracted-строки не плодили FP на
  хорошо-prior'енных статьях (возможно, для извлечённых статей не дублировать дефолтный prior, а
  ставить абстиненс-prior).

### Фаза 6 — селективный VLM (опц.)
- Адаптер base64-картинок в `LLMClient` (модель с vision, напр. `qwen3.6-35b-a3b` — нужен отдельный
  тест, см. `docs/model_strategy.md`); маршрутизировать ТОЛЬКО страницы с упавшим парсингом таблиц.

### Фаза 7 — UI + README + презентация (60 очков!)
- `app.py` (Streamlit, скелет есть): upload PDF → parse → extract → таблица + provenance (page/table)
  → download CSV + плашка ours-vs-baseline.
- README: one-command reproduce (Makefile), пиннинг, история «доверия к метрике» (Gate A),
  поправка про метаполя, баг регистра.
- Презентация: per-field таблица ours vs baseline; архитектура; владение метрикой.

### Фаза 8 — бонусы (по EV)
- **Synergy (+5)**: ближайший nano-домен (baseline 0.080), переиспользует стек (новая схема +
  few-shot + дельта нормализатора + дефолты по его gt-format).
- **Complexes (+15: +5 +10 оба направления)**: только если SelTox+Synergy заперты и есть время
  (планка 0.290, нужен RDKit-canonical SMILES; в `prepare_gold` SMILES-канонизация ещё НЕ реализована —
  добавить для mol-доменов).

---

## 7. Промпт для продолжения (вставить в новую сессию)

```
Ты продолжаешь проект DataCon'26 ChemX на ветке alisa (репо D:\vano\datacon_2026, Windows/PowerShell).
Прочитай сначала: max.md, docs/plan_alisa.md, docs/gt_format.md и память проекта (gate-a-seltox-metric).

Контекст: домен SelTox, метрика exact-string multiset по 23 EXTRACTED_COLUMNS, baseline Macro-F1=0.0454.
Уже сделано (на origin/alisa): доверенный evaluator, калиброванные под gold нормализаторы
(idempotency 0.9995), build-submission без LLM даёт floor 0.1357 (×3 baseline, 40 очков заперты),
PDF resolver (14/65 скачано). venv в .venv (pandas/pyarrow/datasets/huggingface_hub/pydantic/requests/pytest).

Принципы: abstention-first; exact-string строго под формат GT (docs/gt_format.md); mono-agent (один
schema-driven вызов, не тяжёлый MAS); без self-consistency/fine-tuning; не обходить anti-bot при
скачивании; каждый шаг verify через python -m src.cli evaluate под нашим evaluator (all-65 lowercase);
коммить и пушить по фазам.

Задача сейчас — ФАЗА 3 (реальная экстракция):
1) pip install pdfplumber pymupdf; python -m src.cli parse --pdf data/pdfs/103_alekish2018.pdf — проверь
   что текст и таблицы (MIC/ZOI) достаются в data/parsed/.
2) Построй единый экстрактор: full-doc контекст + LLMClient.complete_json со схемой
   baseline/data/schemas/seltox.json (strict) + 2-3 few-shot строки из gold ИЗ СТАТЕЙ ВНЕ SELTOX_ARTICLES;
   одна запись на (bacteria×np), abstention-first; сохраняй raw LLM ответы.
3) Прогони на 14 PDF -> normalize_seltox_record -> data/predictions/extracted.csv;
   python -m src.cli build-submission --extracted ... ; evaluate.
   Go/no-go: prior+extracted > 0.1357.
Нужен ключ: api.txt в корне (две строки: YANDEX_API_KEY, YANDEX_FOLDER_ID), он в .gitignore.
Дальше по docs/plan_alisa.md: Фаза 5 (итерации по полям), 6 (VLM опц.), 7 (UI/README/презентация),
8 (Synergy +5, затем Complexes).
```

---

## 8. Runbook / карта файлов

Ключевые файлы:
- `src/eval/chemx_metric_adapter.py` — метрика, load_gold (HF→local), reproduce/validate.
- `src/baseline_bridge.py` — доступ к baseline constants/schemas/reference_metrics + single-agent URL.
- `src/data/single_agent.py` — fetch single-agent pred (кэш).
- `src/data/pdf_resolver.py` — цепочка резолва PDF.
- `src/postprocess/normalize.py` — GT-калиброванные нормализаторы + `seltox_prior_record`.
- `src/cli.py` — все команды (см. §2).
- `src/agents/*` — текущие экстракторы (скелет; в Фазе 3 схлопнуть в один schema-driven).
- `baseline/` — вендоренный baseline (схемы, constants, метрика, эталоны).

Команды разработки:
```powershell
pytest -q
python -m src.cli inspect-gt-format --domain seltox
python -m src.cli verify-normalizers --domain seltox
python -m src.cli build-submission --domain seltox --out data/predictions/sub.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/sub.csv
```

---

## 9. Риски и подводные камни

- **Метрика не 1:1 воспроизводится** (нет npy). Меряем себя all-65 lowercase; цель — уверенно >0.0454.
- **Extracted-строки могут плодить FP** на статьях, где prior уже хорош → для извлечённых статей
  пересмотреть, нужен ли мажоритарный prior (возможно абстиненс-prior).
- **PDF coverage ~22%** — это ок (prior закрывает остальные). Не уходить в anti-bot.
- **Числовой формат** — единственный частый источник «невидимых» промахов; всегда сверять с
  `docs/gt_format.md` и `verify-normalizers`.
- **Бюджет Yandex** — экстракция жжёт токены; кэшировать parsing и raw-ответы; начинать с дешёвых
  моделей для отладки (`aliceai-llm-flash`).
- **Windows-консоль** cp1251 роняет вывод с `µ`/`Δ` — в `main()` уже форсится utf-8; не печатать
  не-ASCII в новых командах без учёта этого.
