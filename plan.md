# DataCon'26: рабочий план решения ChemX

Обновлено после просмотра репозитория, baseline-кода, заметки с промптом команды и материалов
воркшопа из Downloads.

## 1. Короткий вывод

Основной фокус стоит перенести на **SelTox**.

Причины:
- у SelTox самый низкий опубликованный single-agent baseline среди содержательных доменов:
  **Macro-F1 = 0.045**;
- это наноматериалы без SMILES, значит не нужно решать сложную задачу structure extraction;
- ключевые поля часто лежат в таблицах: `np`, `bacteria`, `strain`, `method`, `MIC`, `ZOI`,
  `size`, `shape`, `zeta`, параметры synthesis;
- baseline почти полностью проваливает несколько полей, которые можно доставать регулярными
  правилами и table-first подходом: `np_synthesis`, `concentration`, `time_set_hours`,
  `temperature_for_extract_C`, `duration_preparing_extract_min`, `ph_during_synthesis`;
- материалы воркшопа прямо поддерживают стратегию: PDF нужно разбирать как набор text/table/figure
  evidence, затем делать extraction, normalization, validation и сохранять provenance.

Рабочее название архитектуры:

**SelTox-MAX: table-first multi-agent RAG extraction pipeline**

Важно: не строим тяжелый фреймворк ради фреймворка. Первая версия должна быть простым,
воспроизводимым Python-пайплайном с отдельными ролями/агентами и сохранением промежуточных
артефактов.

## 2. Что уже есть в репозитории

В репозитории сейчас есть:
- `task.md` и `README.md` с описанием задачи DataCon/ChemX;
- `baseline/` - перенесенный single-agent baseline из `ai-chem/ChemX`;
- `baseline/data/schemas/*.json` - official JSON schemas;
- `baseline/data/prompts/*.py` - prompts baseline;
- `baseline/src/constants.py` - списки колонок, numeric columns, SMILES columns, HF dataset ids,
  `MAGNETIC_ARTICLES`, `SELTOX_ARTICLES`;
- `baseline/src/metric_calc.py` - реальная логика метрики;
- `baseline/reference_metrics/*.csv` - опубликованные per-field metrics baseline.

Нового production-кода поверх baseline пока нет. В git сейчас одна ветка `main`, локальных
изменений до этой правки не было.

## 3. Как устроена оценка

Из `baseline/src/metric_calc.py`:

1. Gold берется из Hugging Face датасета, затем фильтруется по `access == 1`.
2. Для numeric columns запятые меняются на точки.
3. Пропуски заполняются строкой `NOT_DETECTED`.
4. Для small molecule domains SMILES canonicalize через RDKit.
5. Prediction должен иметь колонки `EXTRACTED_COLUMNS[domain]` плюс `pdf`.
6. Метрика считается не по row alignment, а как **multiset exact string match внутри одной статьи**
   по каждому полю.
7. Для каждой статьи считается per-field precision/recall/F1, затем усреднение по статьям.
8. Основная метрика домена - mean F1 по полям.

Ключевая ловушка: для `seltox` baseline в `prepare_result(source='single_agent')` добавляет `.pdf`
к `pdf`, а в `metric_calc.py` для `seltox` пытается читать отсутствующий файл
`src/seltox_articles.npy`. В нашем evaluator нужно использовать `SELTOX_ARTICLES` из
`baseline/src/constants.py`.

## 4. Почему SelTox лучше старого плана Nanozymes + Complexes

Старый `plan.md` предлагал Nanozymes + Complexes. Это разумная стратегия для бонуса "оба
направления", но как первый удар она хуже:

| Домен | Macro-F1 baseline | Полей | Нулевых F1-полей | Комментарий |
|---|---:|---:|---:|---|
| SelTox | 0.045 | 23 | 6 | Очень низкая планка, table-first должен дать быстрый прирост |
| Synergy | 0.080 | 29 | 4 | Близкий nano-домен после SelTox |
| Nanozymes | 0.164 | 20 | 2 | Сложная кинетика/единицы, выше планка |
| Complexes | 0.290 | 5 | 1 | Малый молекулярный домен, но SMILES F1=0 у baseline |

Решение: **SelTox как обязательный MVP**, затем **Synergy** как близкий optional second domain,
и только потом **Complexes** как stretch для бонуса "small molecules + nanomaterials".

## 5. Идеи из материалов воркшопа

### RAG lecture

Полезные выводы:
- LLM нельзя оставлять без retrieval: она уверенно галлюцинирует цифры и источники.
- В extraction-задаче RAG должен возвращать не просто ответ, а структурированную запись с evidence.
- Качество retrieval критично: если нужный фрагмент не найден, extractor не сможет извлечь поле.
- Multi-agent схема естественная: evidence finder, extractor, validator.

Для нас:
- каждый extracted field должен ссылаться на text/table/figure/caption evidence;
- retrieval для SelTox должен быть hybrid: regex + keywords + BM25, embeddings только позже;
- validator обязан удалять unsupported values, а не "улучшать" их по памяти.

### Source Discovery / PDF lecture

Полезные выводы:
- PDF сохраняет вид страницы, а не семантику таблиц и научных фактов.
- Таблица в PDF часто является набором слов, линий и координат, а не настоящей таблицей.
- Нужен ensemble parser: PyMuPDF, pdfplumber, Camelot, optional Marker/Docling.
- Для scientific PDF важны footnotes, captions, page crops, supplementary files.
- Regex полезен как candidate extraction layer, но результат нужно валидировать.

Для нас:
- сохраняем `pages.json`, `tables.json`, `chunks.json`, `figures.json`, `page_images/`;
- каждый chunk/table/evidence содержит `pdf`, `page`, `source_type`, `text`, `bbox`,
  `parser`, `confidence`;
- таблицы и captions имеют приоритет выше abstract/general discussion.

### PDF extraction exercise notebook

Практический MVP из ноутбука:
- render PDF pages for visual inspection;
- extract page text with PyMuPDF;
- extract table-like regions through pdfplumber coordinates/crops;
- find regex candidates for pH, temperature, concentration, time, size;
- extract captions with regex;
- merge candidates into raw pool;
- normalize and validate into final records.

Для нас это превращается в CLI:
- `parse` создает артефакты;
- `evidence` показывает top evidence;
- `extract` делает structured output;
- `evaluate` сравнивает с ChemX metric.

### Multi-agent chemistry notebook

Полезные выводы:
- агент = LLM + tools + loop;
- инструменты должны иметь понятные schema/docstring;
- orchestrator может делегировать specialist agents;
- важно видеть, что реально уходит в LLM, и логировать вызовы.

Для нас:
- не обязательно брать ADK/LangGraph в первой версии;
- достаточно Python orchestrator + явные модули-агенты;
- сохраняем raw LLM requests/responses для debug и презентации.

### Chemical data cleaning / standardization

Полезные выводы:
- normalization перед merge обязательна, иначе появляются ложные дубликаты и конфликты;
- нужно хранить raw value, raw unit, normalized value, normalized unit;
- missing values должны быть явными, а не пустыми;
- конфликты нельзя тихо усреднять или перезаписывать;
- validation checks: schema, types, missing values, categories, ranges, source links.

Для SelTox:
- `E. coli` -> `Escherichia coli`;
- `S. aureus` -> `Staphylococcus aureus`;
- `AgNPs`, `Ag NPs`, `silver nanoparticles` -> canonical nanoparticle label;
- `ug/ml`, `μg/mL`, `µg ml-1`, `microg/mL` -> metric-compatible representation;
- `8-41 nm` -> `np_size_min_nm=8`, `np_size_max_nm=41`;
- `not reported`, `ND`, `NR`, `n.d.`, `-` -> `NOT_DETECTED`;
- numeric sanity checks: pH 0-14, size >= 0, MIC/ZOI >= 0.

### Chemical data / databases lectures

Полезные выводы:
- химические данные малы, шумные, неоднородные, часто из разных источников;
- статьи и supplementary files являются первичными источниками;
- PubChem/ChEMBL/Materials Project и API полезны как внешние источники, но в ChemX scoring
  решает соответствие article-level gold.

Для нас:
- главный источник истины - конкретная PDF/article evidence;
- внешние базы можно использовать только для normalization/synonyms, не для выдумывания полей;
- source metadata нужно хранить в каждом artifact.

## 6. SelTox official target fields

Из `baseline/src/constants.py` и `baseline/data/schemas/seltox.json`:

```text
np
coating
bacteria
mdr
strain
np_synthesis
method
mic_np_µg_ml
concentration
zoi_np_mm
np_size_min_nm
np_size_max_nm
np_size_avg_nm
shape
time_set_hours
zeta_potential_mV
solvent_for_extract
temperature_for_extract_C
duration_preparing_extract_min
precursor_of_np
concentration_of_precursor_mM
hydrodynamic_diameter_nm
ph_during_synthesis
```

Группировка для агентов:

- **Activity fields:** `np`, `bacteria`, `mdr`, `strain`, `method`, `mic_np_µg_ml`,
  `concentration`, `zoi_np_mm`, `time_set_hours`.
- **Nanoparticle fields:** `np`, `coating`, `np_size_min_nm`, `np_size_max_nm`,
  `np_size_avg_nm`, `shape`, `zeta_potential_mV`, `hydrodynamic_diameter_nm`.
- **Synthesis fields:** `np_synthesis`, `solvent_for_extract`, `temperature_for_extract_C`,
  `duration_preparing_extract_min`, `precursor_of_np`, `concentration_of_precursor_mM`,
  `ph_during_synthesis`.
- **Linking fields:** `np`, article/pdf, nearest evidence section/table, method/context.

## 7. Архитектура SelTox-MAX

```text
PDF / supplementary
  -> Document Ensemble Parser
  -> Document Index
  -> Evidence Finder
  -> Activity Extractor Agent
  -> Nanoparticle Characterization Extractor Agent
  -> Synthesis Extractor Agent
  -> Optional Vision/Table Recovery Agent
  -> Record Linker
  -> Deterministic Normalizer
  -> Validator Agent
  -> ChemX CSV adapter
  -> Evaluation adapter
  -> Streamlit UI
```

### Document Ensemble Parser

Первая версия:
- PyMuPDF: page text, page rendering, metadata, embedded images if useful;
- pdfplumber: words with coordinates, table extraction/crops;
- Camelot: optional lattice/stream tables, graceful fallback;
- Marker/Docling: optional markdown/json converters, не блокируют запуск.

Артефакты:

```text
data/parsed/<pdf_stem>/pages.json
data/parsed/<pdf_stem>/tables.json
data/parsed/<pdf_stem>/chunks.json
data/parsed/<pdf_stem>/figures.json
data/parsed/<pdf_stem>/page_images/
```

### Evidence Finder

Для SelTox first pass лучше keyword/regex/BM25, а не embeddings-first.

Activity keywords:
`MIC`, `MBC`, `ZOI`, `zone of inhibition`, `inhibition zone`, `antibacterial`,
`antimicrobial`, `bacteria`, `strain`, `MDR`, `ATCC`, `E. coli`, `S. aureus`,
`P. aeruginosa`, `K. pneumoniae`, `B. subtilis`, `E. faecalis`.

Nanoparticle keywords:
`AgNP`, `Ag NPs`, `silver nanoparticle`, `ZnO`, `AuNP`, `CuO`, `TiO2`,
`particle size`, `TEM`, `SEM`, `DLS`, `zeta`, `hydrodynamic`, `shape`.

Synthesis keywords:
`green synthesis`, `biological synthesis`, `plant extract`, `AgNO3`, `silver nitrate`,
`precursor`, `pH`, `temperature`, `stirring`, `duration`, `extract`, `solvent`.

### Extraction agents

**ActivityExtractorAgent**
- приоритет: tables with MIC/MBC/ZOI -> footnotes/captions -> results/discussion -> abstract;
- извлекает rows activity table;
- возвращает structured JSON with evidence ids.

**NanoparticleExtractorAgent**
- извлекает size/shape/zeta/hydrodynamic/coating;
- приоритет characterization tables, TEM/SEM/DLS text, figure captions.

**SynthesisExtractorAgent**
- извлекает synthesis method, precursor, precursor concentration, pH, temperature, time,
  extract/solvent.

**VisionTableRecoveryAgent**
- включается только если table parser failed или важная таблица плохо распарсилась;
- принимает crop/page image и возвращает markdown/JSON table.

**RecordLinker**
- склеивает activity rows с article-level NP/synthesis/characterization facts;
- не создает значения без evidence.

**Normalizer**
- обычный Python, не LLM;
- приводит units/synonyms/ranges/missing values;
- удаляет явные дубликаты.

**ValidatorAgent**
- проверяет каждую запись против evidence;
- удаляет unsupported/hallucinated values;
- выставляет warnings/confidence.

## 8. Предлагаемая структура проекта

```text
app.py
requirements.txt
.env.example
configs/
  selt.yaml
data/
  pdfs/
  parsed/
  predictions/
  gold/
  cache/
docs/
  workshop_summary.md
src/
  __init__.py
  cli.py
  config.py
  schemas/
    __init__.py
    selt.py
  parse/
    __init__.py
    pymupdf_parser.py
    pdfplumber_parser.py
    camelot_parser.py
    ensemble.py
  retrieve/
    __init__.py
    patterns.py
    bm25.py
    evidence_finder.py
  agents/
    __init__.py
    base.py
    activity_extractor.py
    nanoparticle_extractor.py
    synthesis_extractor.py
    vision_table_recovery.py
    validator.py
  postprocess/
    __init__.py
    normalize.py
    link_records.py
    deduplicate.py
  eval/
    __init__.py
    chemx_metric_adapter.py
  utils/
    __init__.py
    io.py
    logging.py
tests/
  test_normalize.py
  test_schema.py
  test_parse_smoke.py
```

Не нужно сразу делать всю структуру, если времени мало. Минимальная версия: `src/cli.py`,
`parse/ensemble.py`, `retrieve/evidence_finder.py`, `agents/*`, `postprocess/normalize.py`,
`eval/chemx_metric_adapter.py`, `app.py`.

## 9. CLI первой версии

```bash
python -m src.cli inspect-selt
python -m src.cli parse --pdf data/pdfs/ag_nps_sensor_article.pdf
python -m src.cli evidence --pdf data/pdfs/ag_nps_sensor_article.pdf --domain SelTox
python -m src.cli extract --pdf data/pdfs/<article>.pdf --domain SelTox --out data/predictions/<article>_selt.csv
python -m src.cli batch-extract --pdf-dir data/pdfs --domain SelTox --out data/predictions/selt_predictions.csv
python -m src.cli evaluate --pred data/predictions/selt_predictions.csv --domain seltox
streamlit run app.py
```

Если Hugging Face недоступен, `inspect-selt` и `evaluate` должны уметь читать local cache:
`data/gold/seltox.csv` или `data/gold/seltox.parquet`.

## 10. Этапы работы

### M0. Trusted evaluator

Сначала реализовать `chemx_metric_adapter.py`.

Проверка:
- на single-agent predictions метрики должны совпадать с
  `baseline/reference_metrics/metrics_seltox_from_single_agent.csv`;
- если нет gold cache, сделать synthetic smoke test и явно написать в README, куда положить gold.

Без M0 мы не понимаем, побили baseline или нет.

### M1. Inspect SelTox schema/gold

Команда `inspect-selt`:
- показывает split names;
- rows/columns;
- sample rows;
- target chemical fields;
- source fields;
- missing values format;
- article subset from `SELTOX_ARTICLES`.

### M2. Parse one PDF

Реализовать parser для одного PDF.

Проверка:
- создаются `pages.json`, `tables.json`, `chunks.json`, `figures.json`, `page_images/`;
- parser не падает, если Camelot/Marker/Docling не установлены;
- на `ag_nps_sensor_article.pdf` находятся pH 10, 70 C, 2 h, AgNO3, 8-41 nm как evidence.

### M3. Evidence Finder

Реализовать hybrid retrieval.

Проверка:
- `evidence` command показывает top activity/NP/synthesis snippets;
- для SelTox PDF top chunks должны включать MIC/ZOI/bacteria tables, если они есть.

### M4. Extraction agents

Сначала без vision:
- ActivityExtractorAgent;
- NanoparticleExtractorAgent;
- SynthesisExtractorAgent;
- structured JSON only;
- Pydantic validation;
- retry on parse errors;
- raw LLM responses saved.

Проверка:
- один PDF -> JSON artifacts + CSV with official SelTox columns.

### M5. Normalization, linking, validation

Реализовать:
- bacteria synonyms;
- NP synonyms;
- units;
- ranges;
- `NOT_DETECTED`;
- numeric sanity checks;
- record linking;
- deduplication.

Проверка:
- tests for normalization;
- no unsupported values after ValidatorAgent.

### M6. Batch run and metric iteration

Запустить на доступном наборе SelTox PDF.

Цель:
- Macro-F1 > **0.045**.

Итерация:
1. activity extraction: `bacteria`, `strain`, `method`, `MIC`, `ZOI`, `np`;
2. table recovery;
3. synthesis fields;
4. normalization;
5. record linking;
6. validator.

### M7. Streamlit UI

Минимальный UI:
- upload PDF;
- select domain SelTox;
- buttons Parse / Extract;
- result table;
- evidence snippets per record;
- validation warnings/confidence;
- download CSV/JSONL.

### M8. Optional domains

После SelTox:
1. **Synergy** - ближайший по тематике nano-домен, baseline 0.080.
2. **Complexes** - stretch для бонуса "small molecules + nanomaterials", baseline 0.290.

## 11. Риски

| Риск | Что делать |
|---|---|
| Нет доступа к Hugging Face | local gold cache + synthetic smoke tests |
| Не все PDF скачиваются автоматически | resolver chain + ручной tail; сначала работаем на доступных PDF |
| Table parser ломается | ensemble parser + crop/page image fallback |
| LLM выдумывает значения | evidence-grounded prompts + ValidatorAgent + `NOT_DETECTED` |
| Row linking сложный | сначала article-level NP/synthesis facts, потом улучшать linking |
| Exact string metric суровая | normalizer калибровать по gold и single-agent predictions |
| Слишком много архитектуры | сначала CLI MVP, потом optional agents/vision/UI polish |

## 12. Ветка или main

Для анализа и правки плана отдельная ветка не обязательна.

Для реализации кода лучше создать отдельную ветку:

```bash
git switch -c feature/selt-mvp
```

Причина: дальше появятся dependencies, структура проекта, CLI, Streamlit и тесты. Это уже
достаточно большой change set, который лучше держать отдельно от `main`.

## 13. Критерий успеха первой рабочей версии

Первая версия считается готовой, если:
- `python -m src.cli inspect-selt` работает или честно просит local gold cache;
- `python -m src.cli parse --pdf ...` создает parsed artifacts;
- `python -m src.cli evidence --pdf ... --domain SelTox` показывает релевантные evidence chunks;
- `python -m src.cli extract --pdf ... --domain SelTox` создает CSV с official SelTox columns;
- `python -m src.cli evaluate --pred ... --domain seltox` считает ChemX-compatible metrics;
- `streamlit run app.py` открывает UI и показывает таблицу;
- README объясняет запуск;
- pipeline не падает без optional parsers;
- все intermediate artifacts сохраняются.

## 14. Следующее действие

Начинать нужно не с frontend и не с LangGraph, а с:

1. `requirements.txt`, `.env.example`, `configs/selt.yaml`;
2. `src/eval/chemx_metric_adapter.py`;
3. `src/cli.py inspect-selt`;
4. parser/evidence MVP на одном PDF;
5. SelTox extraction на одном PDF;
6. batch + metric iteration.

Это самый короткий путь к системе, которая реально может побить baseline.
