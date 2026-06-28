# SelTox gold format (measured) — calibration spec for normalizers

Produced by `python -m src.cli inspect-gt-format --domain seltox` over the cached HF gold
(`data/gold/seltox.parquet`, access-filtered, 2512 rows). The exact-string multiset metric forces
our output to match these byte-for-byte. Normalizers in `src/postprocess/normalize.py`
(`SELTOX_FIELD_NORMALIZERS`) are calibrated to this table.

## Per-field format

| field | dtype | %nan | gold canonical | normalizer | note |
|---|---|---:|---|---|---|
| np | str | 0 | formula: `Ag`(79%), `ZnO`, `Au`, `TiO2`, `CuO`, `Fe3O4`, ... | `norm_np` | dominant default `Ag` |
| coating | int64 | 0 | `0`(85%) / `1` | `norm_binary` | default `0`; never NOT_DETECTED |
| bacteria | str | 0 | full latin: `Escherichia coli`, `Staphylococcus aureus`, ... (113 uniq) | `norm_bacteria` | |
| mdr | int64 | 0 | `0`(91%) / `1` | `norm_binary` | default `0`; baseline wrote `yes` → always wrong |
| strain | str | 49 | `NOT_DETECTED` / `ATCC 25922`, `MTCC 441`, `clinical isolate` | `norm_text` | |
| np_synthesis | str | 0 | free text: `green_synthesis using <plant>`, `green_synthesis`, `chemical_synthesis` (188 uniq) | `norm_text` | hard (exact match) |
| method | str | 0 | upper vocab: `MIC`(49%), `ZOI`, `MBC`, `MFC`, `MBEC`, ... (8 uniq) | `norm_method` | |
| mic_np_µg_ml | **str** | 36 | **int-style** `100`, `12.5`, `0` | `norm_int_num` | NOT `.0` style |
| concentration | float64 | 65 | `100.0`, `42.5`, `0.31` | `norm_float_num` | |
| zoi_np_mm | float64 | 64 | `X.0`, `0.0` | `norm_float_num` | |
| np_size_min_nm | float64 | 1 | `10.0`, `14.45`, `5.34` | `norm_float_num` | |
| np_size_max_nm | float64 | 9 | `20.0`, `15.55` | `norm_float_num` | |
| np_size_avg_nm | float64 | 5 | `13.5`, `40.0`, `26.06` | `norm_float_num` | |
| shape | str | 14 | lower: `spherical`(dom), `rod-shaped`, `cubic`, ... (22 uniq) | `norm_shape` | lowercased (23 `Spherical` folded) |
| time_set_hours | float64 | 18 | `24.0`(dom), `18.0`, `48.0` | `norm_float_num` | |
| zeta_potential_mV | float64 | 79 | `-39.95`, `-27.4` | `norm_float_num` | negatives |
| solvent_for_extract | str | 58 | `NOT_DETECTED` / `water`, `ethanol`, `water (distilled)` | `norm_text` | |
| temperature_for_extract_C | float64 | 64 | `25.0`, `60.0`, `-2.0` | `norm_float_num` | |
| duration_preparing_extract_min | float64 | 64 | `30.0`, `1440.0`, `3600.0` | `norm_float_num` | minutes |
| precursor_of_np | str | 54 | `AgNO3`(dom) / `NOT_DETECTED` / `AgNPs` / `Ag` | `norm_text` | |
| concentration_of_precursor_mM | float64 | 60 | `1.0`(dom), `5.0`, `9.4` | `norm_float_num` | |
| hydrodynamic_diameter_nm | float64 | 86 | `65.4`, `100.0` | `norm_float_num` | |
| ph_during_synthesis | float64 | 84 | `10.5`, `7.0`, `6.1` | `norm_float_num` | |

## Key calibration decisions

1. **Number format is per-field, by storage dtype.** `float64` fields → `str(float(x))` (`10` → `10.0`).
   `mic_np_µg_ml` is `str` → integer-style (`100`, no `.0`). One global number formatter is wrong.
2. **`mdr` and `coating` are binary `0/1` with 0% missing** → default `0`, never `nan`/`NOT_DETECTED`.
3. **Missing convention:** numeric fields → `"nan"`; string fields → `"NOT_DETECTED"` (this is what
   `prepare_gold` produces: numeric NaN survives `convert_comma` as the string `"nan"`).
4. **Dominant-default opportunity (for Phase 2 blank-prior, 0%-nan fields):** `np` → `Ag` (~79%),
   `coating` → `0` (~85%), `mdr` → `0` (~91%). These predict the majority class for free.

## Verification

`python -m src.cli verify-normalizers --domain seltox` → idempotency Macro-F1 **0.9995**
(normalized-gold vs gold). Sub-1.0 only on deliberate folds: `shape` 0.991 (case), `method` 0.998
(typo `MIc`), `mic` 0.9998 (one non-standard entry). Confirms normalizers match GT and do not
damage already-correct values.
