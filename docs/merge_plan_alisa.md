# Merge Plan — branch `alisa`

План переноса: объединяем лучшее из `selt-mvp` (рабочий код + верный выбор домена + реальные
находки) и `main` (строгость метрики, resolver-цепочка, числовые go/no-go). Это **концептуальный
перенос**, не git-merge: в `main` кода нет, только `plan.md` + `baseline/`.

База ветки: `alisa` создана из `selt-mvp`.

---

## 1. Что оставляем из `selt-mvp` без изменений

- Домен **SelTox** как MVP (baseline Macro-F1 = 0.045 — проверено по `reference_metrics`).
- Пайплайн: ensemble parser, evidence finder (regex/keywords/BM25), agents
  (Activity/Nanoparticle/Synthesis), normalizer, validator, record linker, Streamlit UI.
- Evaluator `src/eval/chemx_metric_adapter.py`: HF→local cache, seltox-subset через
  `article_subset`, `nan` для numeric / `NOT_DETECTED` для строк. GT-vs-GT = 1.0.
- Реальный LLM-слой: **Yandex AI Studio** (OpenAI-совместимый), default `deepseek-v4-flash`.

## 2. Находки из `progress.md`, которых нет ни в одном `plan.md` (фиксируем как первоклассные)

- **Submission shape = blank-prior + extracted rows.** Одна пустая строка на каждый из 65 целевых
  PDF (правильные `NOT_DETECTED`/`nan`) + извлечённые строки для распарсенных PDF. Уже даёт
  0.073→0.091 против baseline 0.045. Это главный рычаг.
- **Узкое место — покрытие PDF**, а не промпты: 6/65 скачано (Crossref-only). Улучшать coverage
  раньше, чем prompt-tuning.
- LLM = Yandex AI Studio; интерфейс держим pluggable (идея из `main`), но документируем реального
  провайдера/модели.

---

## 3. Переносы из `main` (дельты с проверкой)

### Port A — Доверенный evaluator: валидация против опубликованных чисел  [HIGH / LOW]

- **Зачем:** сейчас доказано только GT-vs-GT=1.0. Нет доказательства, что наша метрика 1:1
  воспроизводит `baseline/reference_metrics/metrics_seltox_from_single_agent.csv`. Без этого мы не
  знаем, честно ли сравнение с baseline.
- **Источник (main):** M0 — `fetch_single_agent_pred(domain)` из
  `raw.githubusercontent.com/ai-chem/ChemX/main/LLM/result/from_single_agent/<domain>/pred.csv`;
  для `seltox/synergy/magnetic/cytotoxicity` baseline дописывает `.pdf` к колонке `pdf` в
  single-agent pred (`prepare_result`).
- **Цель (файлы):**
  - `src/baseline_bridge.py`: добавить `single_agent_pred_url(domain)` + `fetch_single_agent_pred`.
  - `src/eval/chemx_metric_adapter.py`: ветка `source='single_agent'` в `prepare_pred` с
    `.pdf`-append для нужных доменов.
  - `src/cli.py`: команда `validate-evaluator --domain seltox`.
- **Verify:** per-field `f1` совпадает с `metrics_seltox_from_single_agent.csv` (|Δ| < 1e-6);
  Macro-F1 ≈ 0.045. Пока не совпало — метрику не считаем доверенной.

### Port B — Богатая resolver-цепочка для PDF  [HIGH / MED]

- **Зачем:** 6/65 — слишком мало; покрытие напрямую ограничивает счёт.
- **Источник (main):** M1 — Unpaywall (все `oa_locations`) → OpenAlex (`locations[].pdf_url`,
  `ids.pmcid`) → Europe PMC / PMC → publisher-паттерны (MDPI/RSC/Elsevier). Имена файлов = ключ
  join к `pdf` в gold.
- **Цель (файлы):** `src/data/pdf_resolver.py` — расширить за пределы Crossref-only; та же
  сигнатура `resolve_one_pdf`, добавить шаги в `candidates`; сохранять под точными именами из
  `SELTOX_ARTICLES`.
- **Verify:** `batch-resolve` на 65 `SELTOX_ARTICLES` повышает покрытие выше 6/65; печатать
  отчёт N/65 и список незакрытого «хвоста».

### Port C — Числовые go/no-go + раздел Verification + таблица ours-vs-baseline  [MED / LOW]

- **Зачем:** для самопроверки и для жюри (презентация 20 / код-README 20).
- **Источник (main):** Verification section + явные пороги.
- **Цель (файлы):** `src/cli.py evaluate` печатает per-field таблицу ours vs baseline (baseline из
  `reference_metrics`); `README.md` — раздел с порогами и итоговой таблицей.
- **Verify:** таблица строится; порог SelTox Macro-F1 > 0.045 (stretch: per-field выше
  single-agent).

### Port D — Конфиг-driven мультидоменность  [DEFERRED / HIGH]

- **Источник (main):** один YAML на домен + переиспользование `baseline/data/schemas/*.json`;
  re-export констант.
- **Почему откладываем:** стратегия SelTox-first; узкое место — coverage, не обобщение; агенты
  специализированы под SelTox; принцип Simplicity First. Преждевременный рефактор не приносит
  очков сейчас.
- **Триггер:** только после фиксации победы на SelTox, когда добавляем Synergy (0.080) или
  Co-crystals под бонус +5.

---

## 4. Порядок реализации (следующий шаг — отдельно, по подтверждению)

1. **Port A** — доверенный evaluator (фундамент: всё меряется им).
2. **Port C** — пороги и таблица видимы.
3. Закрепить **blank-prior submission** как команду `build-submission` (если ещё не оформлено).
4. **Port B** — поднять покрытие PDF.
5. Итерации промптов Activity/таблиц (`bacteria`, `strain`, `method`, `MIC`, `ZOI`).
6. **Port D** — только при расширении на второй домен.

## 5. Матрица проверок

| Item | Команда проверки | Критерий |
|---|---|---|
| Port A | `python -m src.cli validate-evaluator --domain seltox` | per-field f1 == reference (1e-6) |
| Port B | `python -m src.cli batch-resolve --domain seltox` | покрытие > 6/65, отчёт N/65 |
| Port C | `python -m src.cli evaluate --pred ... --domain seltox` | таблица ours-vs-baseline; >0.045 |
| blank-prior | `python -m src.cli build-submission ...` | Macro-F1 ≥ 0.073 на 65 PDF |

## 6. Вне рамок (Simplicity First)

- Полный мультидоменный рефактор сейчас (см. Port D).
- Vision/Table-recovery агент — включать только если конкретное поле не закрывает планку.
- Self-consistency / ансамбль проходов — только как амплификатор при незакрытом баре.
