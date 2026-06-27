# datacon_2026

Решение финальной задачи **DataCon'26** — автоматическая экстракция химических данных из
научных PDF на основе бенчмарка [ChemX](https://github.com/ai-chem/ChemX) (NeurIPS 2025).
Описание задачи: репозиторий `DataCon26`.

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
