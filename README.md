# datacon_2026

Решение финальной задачи **DataCon'26** — автоматическая экстракция химических данных из
научных PDF на основе бенчмарка [ChemX](https://github.com/ai-chem/ChemX) (NeurIPS 2025).
Описание задачи: репозиторий `DataCon26`.

## SelTox-MAX MVP

Текущий рабочий трек — **SelTox-MAX**, table-first каркас для домена SelTox
(`Macro-F1` baseline: `0.045`). Пока LLM-слой отключён по умолчанию: parser, evidence finder,
normalizer, CSV adapter и metric adapter можно проверять без API-ключа.

Быстрые команды:

```bash
python -m src.cli inspect-selt
python -m src.cli parse --pdf path/to/article.pdf
python -m src.cli evidence --pdf path/to/article.pdf --domain SelTox
python -m src.cli extract --pdf path/to/article.pdf --domain SelTox --out data/predictions/article_selt.csv
python -m src.cli batch-extract --pdf-dir data/pdfs --domain SelTox --out data/predictions/selt_predictions.csv
python -m src.cli evaluate --pred data/predictions/selt_predictions.csv --domain seltox
python -m src.cli llm-smoke --dry-run
streamlit run app.py
```

Для оценки положите официальный gold cache в `data/gold/seltox.csv` или
`data/gold/seltox.parquet`. Для LLM-провайдера скопируйте `.env.example` в `.env` и заполните
OpenAI-compatible endpoint/model/key; Yandex AI Studio можно подключить через `YANDEX_API_KEY`,
`YANDEX_FOLDER_ID`, `OPENAI_BASE_URL`, `LLM_MODEL`. Короткая инструкция по выбору модели и smoke-run:
[`docs/yandex_ai_studio.md`](./docs/yandex_ai_studio.md).

Подробный рабочий план лежит в [`plan.md`](./plan.md).

## Baseline (single-agent)

В каталоге [`baseline/`](./baseline) лежит перенесённый single-agent бейзлайн из
[ai-chem/ChemX](https://github.com/ai-chem/ChemX) (`LLM/`) — отправная точка, которую
нужно превзойти. Пайплайн: `merge_suppl` → `pdf_to_images` → `pdf_extraction` /
`images_extraction` → `metric_calc`. Инструкция по запуску — в
[`baseline/README.md`](./baseline/README.md).

Опубликованные метрики single-agent (эталон сравнения; подробные Precision/Recall/F1 по
полям — в [`baseline/reference_metrics/`](./baseline/reference_metrics)):

| Домен | Направление | Macro-F1 (single-agent) |
|---|---|:---:|
| Benzimidazoles | Малые молекулы | 0.217 |
| Oxazolidinones | Малые молекулы | 0.491 |
| Co-crystals | Малые молекулы | 0.296 |
| Complexes | Малые молекулы | 0.290 |
| Eye Drops | Малые молекулы | — |
| Nanozymes | Наноматериалы | 0.164 |
| Synergy | Наноматериалы | 0.080 |
| Nanomag | Наноматериалы | 0.034 |
| Cytotox | Наноматериалы | 0.182 |
| SelTox | Наноматериалы | 0.045 |

> Цель — превзойти метрики single-agent хотя бы на одном домене.

## Ссылки

- Датасеты ChemX: https://huggingface.co/collections/ai-chem/chemx
- Код бенчмарка и бейзлайнов: https://github.com/ai-chem/ChemX
- Статья ChemX (NeurIPS 2025): https://proceedings.neurips.cc/paper_files/paper/2025/file/9e08a1db869a9646418e3371b24c6ae6-Paper-Datasets_and_Benchmarks_Track.pdf
