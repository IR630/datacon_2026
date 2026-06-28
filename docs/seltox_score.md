# SelTox — финальный скор

Метрика: ChemX exact-string multiset Macro-F1 по 23 EXTRACTED_COLUMNS,
внутренний evaluator all-65 lowercase (см. `gate-a-seltox-metric`).

| Сабмишен | Macro-F1 |
|---|---|
| ChemX single-agent baseline | 0.0454 |
| prior-only (floor, без LLM) | 0.1357 |
| prior + LLM (Qwen3.6-35B, Yandex) | 0.1863 |
| + маппинг `method` → {MIC,ZOI,MBC,MFC} | 0.1887 |
| **+ маппинг `precursor` → {AgNO3,NOT_DETECTED}** | **0.1921** |

×4.2 к baseline. Ветка `alisa`.

Воспроизведение:
```powershell
python -m src.cli llm-extract --pdf-dir data/pdfs --out data/predictions/extracted.csv
python -m src.cli build-submission --domain seltox --extracted data/predictions/extracted.csv --out data/predictions/seltox_submission_llm.csv
python -m src.cli evaluate --domain seltox --pred data/predictions/seltox_submission_llm.csv
```
