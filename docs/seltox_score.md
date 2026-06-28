# SelTox — финальный скор

Метрика: ChemX exact-string multiset Macro-F1 по 23 EXTRACTED_COLUMNS,
внутренний evaluator all-65 lowercase (см. `gate-a-seltox-metric`).

| Сабмишен | Macro-F1 |
|---|---|
| ChemX single-agent baseline | 0.0454 |
| prior-only (floor, без LLM) | 0.1357 |
| **prior + LLM (Qwen3.6-35B, Yandex)** | **0.1863** |

×4 к baseline. Коммит: `0b1d7d2` (ветка `alisa`).

Воспроизведение:
```powershell
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox --extracted data/predictions/extracted.csv --out data/predictions/seltox_submission_llm.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_llm.csv
```
