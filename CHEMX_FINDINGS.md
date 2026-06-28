# ChemX: выводы из анализа материалов и репозитория

Документ — сжатый набор практически применимых наблюдений из README хакатона, документации ChemX (mkdocs), схем датасетов на HF и кода eval. План у вас свой; здесь только то, что должно повлиять на решения.

---

## 1. Как реально считается метрика — самое важное

В `docs/methods/benchmarking.md` репозитория ChemX лежит функция `calc_metrics`, и она работает так:

```python
for col in df_true.columns:
    if col == "pdf": continue
    true_values = list(df_true[col].astype(str).values)
    pred_values = list(df_pred[col].astype(str).values)
    # multiset matching по точному равенству строк
    # tp = сколько значений из true нашлось в pred (с удалением)
    # fp = сколько в pred осталось лишних
    # fn = сколько в true не нашлось в pred
```

Из этого следует несколько вещей, которые меняют стратегию:

1. **Сравнение column-wise, не row-wise.** Никакого joining по `compound_id` или `doi`. Просто два мультимножества строк на колонку. Метрика **не штрафует за перепутанные строки внутри статьи** — если в колонке `target_value` у GT есть `0.5` и у нас в любой строке выхода есть `0.5`, это TP.
2. **Exact string match через `astype(str)`.** `"0.5" ≠ "0.50"`, `"5 μg/mL" ≠ "5 ug/ml"`, `"Oc1ccccc1" ≠ "c1ccc(O)cc1"` даже если canonical RDKit-SMILES совпадает. Никакой fuzzy, никакой числовой толерантности, никакой канонизации.
3. **Macro-F1 = mean F1 по колонкам.** Все колонки весят одинаково — `page_bacteria` равно по весу `smiles`.
4. **Пропускается только `pdf`.** Все остальные метаполя (`doi`, `journal`, `year`, `access`, `origin_*`, `section_*`, `page_*`) — идут в метрику.

**Главное практическое следствие:** нормализация выхода **под формат GT** даёт огромный прирост почти бесплатно. И наоборот — слишком умная нормализация (RDKit canonical, унификация единиц) может **ухудшить** метрику, если в GT хранятся неканонические строки. Первое, что нужно сделать после клонирования — открыть CSV глазами и посмотреть **реальный формат каждого столбца** до того, как писать пайплайн.

---

## 2. Структура колонок: где «дешёвые» поля, а где нет

### Co-crystals (37 колонок, 70 строк, baseline 0.296)

Колонки делятся примерно так:
- **«Низковисящие» метаполя (~16):** `pdf`, `doi`, `title`, `journal`, `authors`, `year`, `access`, `supplementary`, `page`, `name_cocrystal_type_file`, `name_cocrystal_origin`, `name_cocrystal_page`, `ratio_cocrystal_page`, `ratio_cocrystal_origin`, `photostability_change_origin`, `photostability_change_page`. Большую часть можно вытащить из CrossRef/OpenAlex по DOI + marker.
- **Категориальное:** `photostability_change` ∈ {`increase`, `does not change`, `decrease`}.
- **Целевые химические (6):** `name_cocrystal`, `ratio_cocrystal`, `name_drug`, `SMILES_drug`, `name_coformer`, `SMILES_coformer`.

Документация явно говорит, что SMILES в Co-crystals — **canonical**. Это означает, что `Chem.MolToSmiles(Chem.MolFromSmiles(s))` должен попадать в формат GT (надо проверить версию RDKit и isomeric-флаг). OCSR через MolScribe/DECIMER → RDKit canonical здесь работает без format-mismatch.

### Benzimidazoles (25+ колонок, baseline 0.217)

Аналогичная структура с метаполями: `page_bacteria`, `origin_bacteria`, `section_bacteria`, `subsection_bacteria`, `page_target`, `origin_target`, `section_target`, `subsection_target`, `page_scaffold`, `origin_scaffold`, `page_residue`, `origin_residue` плюс библиография. Целевые: `smiles`, `compound_id`, `target_type`, `target_relation`, `target_value`, `target_units`, `bacteria`, `bacteria_unified`. Конвенция отсутствия — **строка `"NOT_DETECTED"`** (это в промпте у них зашито). Если пишете пустые ячейки вместо `"NOT_DETECTED"` — автоматический FN на пустых полях.

### SelTox (36 колонок, baseline 0.045)

Структура **другая**. Из 36 колонок провенансных мало: `doi`, `pdf`, `access`, `reference`. Все остальные — реальные химико-экспериментальные поля (`np`, `coating`, `bacteria`, `mdr`, `strain`, `np_synthesis`, `method`, `mic_np_µg_ml`, `concentration`, `zoi_np_mm`, `np_size_min_nm/max/avg`, `shape`, `time_set_hours`, `zeta_potential_mV`, `solvent_for_extract`, ..., `ph_during_synthesis`). Никаких `page_*`/`origin_*`/`section_*`.

Низкий baseline здесь объясняется не пропущенными метаполями, а:
- **Много полей, которые часто пустые в GT** (zeta_potential, hydrodynamic_diameter, ph_during_synthesis). Baseline, видимо, галлюцинирует значения → массовые FP. Научить модель писать blank, когда поле не упомянуто, — главный рычаг.
- **Биологическая номенклатура.** В Validation Results прямо: основные ошибки — `np_synthesis`, `strain`, `bacteria`.
- **Числовой формат.** `12.5` vs `12.50` vs `12,5` → массовое расхождение.

**Вывод:** Co-crystals и Benzimidazoles бьются через корректные метаполя + минимально приличную химию. SelTox/Nanomag/Synergy — через blank-конвенцию и нормализацию числового формата под GT.

---

## 3. Baseline (single-agent) и где он ломается

Из README хакатона и `docs/methods/`:
1. `marker-pdf` → Markdown
2. `gpt-4o-2024-11-20` пишет описание каждой картинки в `<DESCRIPTION_FROM_IMAGE>` теги
3. `gpt-4.1-mini-2025-04-14` читает результат и пишет CSV в схеме домена

Системные точки атаки:
- **Один проход на весь документ.** Длинные таблицы и десятки compound IDs одновременно — внимание размывается.
- **Изображения через текст — лосс-конверсия.** Числа из графиков и структуры с подписями вида «1a, R = Me» теряются. Marker отдаёт картинки путями — baseline не извлекает структуры через OCSR.
- **Нет валидации.** Не проверяется ни `MolFromSmiles`, ни диапазоны единиц, ни заполнение `NOT_DETECTED` где надо.
- **Один общий промпт** на разные схемы. Промпт для Benzimidazoles и для SelTox должны быть разными.
- **Нет page/origin/section tracking** из marker-структуры. Между тем эти поля идут в метрику.

Подтверждено по списку метрик в README: домены с провенансными колонками (Benzimidazoles 0.217, Oxazolidinones 0.491, Co-crystals 0.296) baseline сдаёт менее провально, чем доменах без них (Nanomag 0.034, SelTox 0.045, Synergy 0.080). Это согласуется с гипотезой, что метаполя — половина истории, но не вся.

---

## 4. Что реально стоит делать

### Архитектурно

- **Marker + детерминированный экстрактор метаполей.** `page_*`, `origin_*`, `section_*`, `supplementary` — это парсинг marker-вывода, **не задача для LLM**. Marker сохраняет позицию таблиц/картинок/секций — этого достаточно.
- **Метаданные из DOI.** `journal`, `publisher`, `year`, `title`, `authors`, `access` берутся через CrossRef API (бесплатно, без ключа) или OpenAlex по DOI. Тут LLM не нужен совсем. Это копеечная победа по нескольким колонкам.
- **VLM по страницам поверх marker.** Marker отлично режет PDF на страницы и таблицы; затем VLM (Claude Sonnet 4.6 или GPT-4.1) видит саму страницу как изображение и читает таблицы с layout, нарисованные структуры и подписи к фигурам. Это даёт прирост там, где `<DESCRIPTION_FROM_IMAGE>` теряет данные.
- **OCSR — теперь да.** Документация ChemX прямо упоминает MolScribe и DECIMER в своей же extraction-методологии. SMILES в GT декларируется как canonical. Значит OCSR → RDKit canonical должен попадать в формат. Имеет смысл для Benzimidazoles, Oxazolidinones, Complexes, Co-crystals.
- **Schema-injection.** Промпт на каждый домен с реальным фрагментом схемы + 2–3 few-shot примера из самого датасета. Если делаете несколько доменов — схема должна быть параметром, не хардкодом.

### Нормализация (отдельный модуль, пишется в самом конце)

- Числовой формат: смотрите, как числа лежат в GT — целые без точки, или `5.0`? Сколько знаков после запятой? Округлять до того же числа знаков.
- Единицы: совпадают по символам (`μg/mL` vs `ug/mL` vs `µg/mL` — это **разные строки**).
- SMILES: для Co-crystals можно гнать через RDKit canonical; для других — проверить, что в GT, до того как канонизировать.
- Blank-конвенция: для Benzimidazoles `"NOT_DETECTED"`, для SelTox — посмотреть, как именно пустота кодируется в CSV (`""`, `nan`, `NaN`, `None`).
- Регистр: `Escherichia coli` vs `E. coli` vs `escherichia coli` — exact match.

### Что НЕ делать

- **Self-consistency и ensembling по голосованию строк.** При exact-match метрике усреднение двух чуть разных строк = ни одной правильной.
- **Тяжёлая мультиагентная архитектура в духе ChemCrow.** В самой статье ChemX MAS-подход (NanoMINER, YOLO+GPT-4o) дал прирост только на multimodal-задачах. На остальном моно-агент с правильной инфраструктурой конкурентоспособен.
- **Fine-tuning Qwen/Llama под extraction.** Подготовка пар, обучение, итерации — за выходные не успеть стабильно. Имеет смысл только если решение готово к субботе.
- **RAG.** Статьи помещаются в современный контекст целиком. RAG нужен для grounding/цитат, не для retrieval — а grounding делается проще, через page_id в выходе модели.

---

## 5. Выбор домена

| Опция | Цель | Главный рычаг | Риск |
|---|---|---|---|
| Co-crystals only | побить 0.296 | метаполя + canonical SMILES + 3 категории `photostability_change` | малый домен (70 строк), высокая дисперсия |
| Co-crystals + SelTox | +5 за домен, +10 за оба направления | A + нормализатор blank/чисел для SelTox | SelTox сложнее, чем выглядит |
| Co-crystals + Nanomag (0.034) | то же | то же | схему Nanomag нужно открывать отдельно |

Реалистичный план — **Co-crystals как основной** (стабильно бьётся, есть демонстрационное OCSR для презентации), **SelTox/Nanomag как stretch** (если останется время после стабилизации первого).

Эффект масштабирования: если архитектура построена как domain-agnostic с schema-injection, добавление второго домена ≈ написание промпта + few-shot + правил нормализации. Это часы, а не дни.

---

## 6. Что проверить ДО написания кода

Эти вещи нужно подтвердить руками, иначе план висит в воздухе:

1. **Загрузить Co-crystals и SelTox с HuggingFace, прочитать глазами:**
   - `df.dtypes`, `df.isna().sum()`, `df.head(20)` по каждой колонке
   - Как именно записаны числа (precision, разделитель)
   - Как записаны пустоты в каждой колонке (`""`, `NaN`, `"NOT_DETECTED"`, ...)
   - Какой реально формат SMILES (isomeric? canonical через какую версию RDKit?)
   - Сколько уникальных значений в категориальных полях
2. **Воспроизвести `calc_metrics` локально и прогнать на самих GT-данных (sanity check, должен дать F1=1.0).**
3. **Зайти в `LLM/` репо ChemX через `git clone`** (web_fetch у меня не пускает в подпапки):
   - Посмотреть, как single-agent baseline извлекает `page_*`/`origin_*` поля. Если у них есть детерминированный парсер — гипотеза о «лёгкой победе на метаполях» нужно скорректировать.
   - Посмотреть точную обёртку eval — может, перед `calc_metrics` есть скрытая нормализация.
4. **Посчитать F1 baseline отдельно по химическим vs метаполям колонкам** для одного домена. Если метрика бьёт по метаполям — рычаг подтверждён; если нет — другая стратегия.
5. **Бюджет по VLM.** Прикинуть стоимость прогона одной статьи через Claude/GPT-4.1 как изображения по страницам. Если статей в test-сплите много и страницы большие — план может не упереться в качество, но упереться в деньги.

---

## 7. Чего я не успел проверить (риски)

- **Схему Nanomag, Synergy, Cytotox, Nanozymes** не открывал. Гипотеза «у наноматериалов нет метаполей» подтверждена только на SelTox.
- **Точную нормализацию в eval-wrapper'е** репо ChemX. Только публичную функцию `calc_metrics` со страницы доков. Возможно, в `LLM/` есть обёртка с дополнительной обработкой.
- **Реальный SMILES-формат в GT** ни одного датасета руками не смотрел — только декларация «canonical» из доков.
- **ChemX-RAG** упомянут в README ChemX, но публично репо недоступен. Полагаться на него нельзя.
- **Сколько train/test split дают на хакатоне.** В метриках написано «на open access статьях», но как режут sample — неясно.

---

## 8. Краткий чек-лист на старте

```
[ ] git clone https://github.com/ai-chem/ChemX
[ ] cd ChemX && ls LLM/  # посмотреть код baseline
[ ] huggingface-cli download ai-chem/Co-crystals --repo-type dataset
[ ] open Co-crystals в pandas, dtype/isna/head по каждой колонке
[ ] то же для SelTox
[ ] локально прогнать calc_metrics(df_true, df_true) → должно быть 1.0
[ ] локально прогнать calc_metrics(df_true, df_baseline_predictions) → воспроизвести табличные цифры из README
[ ] разбить F1 на метаполя vs химические поля → проверить гипотезу
[ ] только после этого — архитектурные решения и код
```

Самое опасное — начать строить пайплайн до того, как поняли формат GT. Любое расхождение в формате чисел/единиц/SMILES обнулит работу, и diff будет невидимым в исходниках, только в метрике.
